#!/usr/bin/env python
import rospy
import json
import os
import numpy as np
from geometry_msgs.msg import PoseWithCovarianceStamped, Pose, Twist
from logic_and_math.logic_gate_executor import LogicGateExecutor, SIGNAL_BREAK, SIGNAL_CONTINUE, SIGNAL_FATAL_ERROR
from battery.battery_status import BatteryMonitor
from move.move2point import MoveToMarker, GOAL_COMPLETION_OBSTACLE
try:
    from measure.measure_distance import DistanceMeasurer
except ImportError:
    rospy.logwarn("Failed to import DistanceMeasurer from measure_distance.py. Obstacle checking disabled.")
    DistanceMeasurer = None
from trajectory.follow_line import MPCController

class RobotProgramExecutor(LogicGateExecutor):
    def __init__(self, marker_json_path, 
                 sub_programs_json_path,
                 initial_battery_level=15,
                 front_lidar_topic="/f_scan", 
                 back_lidar_topic="/b_scan",   
                 measure_distance_angle_deg_total=10.0,
                 move_obstacle_threshold=0.4, 
                 move_obstacle_check_angle=20.0,
                 simulation_state_path="/home/duc/Downloads/MIR100_WebApp/simulation_state.json"):
        super().__init__()
        self.battery_monitor = BatteryMonitor(initial_battery_level=initial_battery_level)
        
        self.distance_measurer = None
        if DistanceMeasurer is not None:
            self.distance_measurer = DistanceMeasurer(
                front_scan_topic=front_lidar_topic,
                back_scan_topic=back_lidar_topic, 
                default_measurement_angle_deg_total=measure_distance_angle_deg_total
            )
        
        self.move_to_marker = MoveToMarker(
            json_path=marker_json_path,
            distance_measurer_instance=self.distance_measurer 
        )
        
        self.default_measure_angle = measure_distance_angle_deg_total
        self.move_obstacle_threshold = move_obstacle_threshold
        self.move_obstacle_check_angle = move_obstacle_check_angle
        self.sub_programs_json_path = sub_programs_json_path
        self.simulation_state_path = simulation_state_path
        self.loaded_sub_programs = self._load_sub_programs()
        
        self.mpc_controller = MPCController(
            dt=0.05,
            v_max=0.3,
            v_min=-0.3,
            omega_max=0.5,
            omega_min=-0.5,
            lookahead_distance=0.5,
            filter_order=3,
            cutoff_frequency=2.0
        )
        
        self.simulation_mode = self._load_simulation_state()
        self.pose_topic = "/amcl_pose" if self.simulation_mode else "/robot_pose"
        self.current_pose = None
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        rospy.Subscriber(self.pose_topic, PoseWithCovarianceStamped if self.simulation_mode else Pose, 
                        self._pose_callback, queue_size=1)
        
        rospy.loginfo(f"RobotProgramExecutor initialized (with SubProgram, Obstacle Avoidance, and MPC for trajectory). Pose topic: {self.pose_topic}")

    def _load_simulation_state(self):
        try:
            with open(self.simulation_state_path, 'r') as f:
                state = json.load(f)
            simulation_running = state.get("simulation_running", False)
            rospy.loginfo(f"Loaded simulation state: {'simulation' if simulation_running else 'real'}")
            return simulation_running
        except Exception as e:
            rospy.logwarn(f"Failed to load simulation state from {self.simulation_state_path}: {e}. Defaulting to simulation mode for Gazebo.")
            return True  # Default to simulation mode since Gazebo is detected

    def _pose_callback(self, msg):
        if self.simulation_mode:
            pose_msg = msg.pose.pose
        else:
            pose_msg = msg
        quat = pose_msg.orientation
        norm_sq = quat.x**2 + quat.y**2 + quat.z**2 + quat.w**2
        if norm_sq < 1e-9:
            rospy.logwarn_throttle(5.0, "Invalid (zero) quaternion received, skipping pose update.")
            return
        try:
            import tf.transformations as tf_trans
            euler = tf_trans.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
            _, _, yaw = euler
        except Exception as e:
            rospy.logerr(f"Error converting quaternion to Euler: {e}")
            return
        self.current_pose = np.array([pose_msg.position.x, pose_msg.position.y, yaw])
        rospy.logdebug(f"Updated pose: x={self.current_pose[0]:.2f}, y={self.current_pose[1]:.2f}, theta={self.current_pose[2]:.2f}")

    def _load_sub_programs(self):
        if not self.sub_programs_json_path or not os.path.exists(self.sub_programs_json_path):
            rospy.logwarn(f"Subprogram JSON file not found or path not set: {self.sub_programs_json_path}. Call_program will fail.")
            return {}
        programs_dict = {}
        try:
            with open(self.sub_programs_json_path, 'r') as f:
                sub_programs_list = json.load(f)
            if not isinstance(sub_programs_list, list):
                rospy.logerr(f"Subprogram JSON file '{self.sub_programs_json_path}' is not a list.")
                return {}
            for program_data in sub_programs_list:
                if isinstance(program_data, dict) and "name" in program_data and "commands" in program_data:
                    programs_dict[program_data["name"]] = program_data["commands"]
                else:
                    rospy.logwarn(f"Invalid program structure in subprogram file: {program_data}")
            rospy.loginfo(f"Loaded {len(programs_dict)} subprograms from {self.sub_programs_json_path}.")
        except Exception as e:
            rospy.logerr(f"Error loading subprograms from {self.sub_programs_json_path}: {e}")
            return {}
        return programs_dict

    def _get_value_from_command_source(self, value_command):
        cmd_type = value_command.get("type")
        cmd_subtype = value_command.get("subtype")
        cmd_config = value_command.get("config", {})
        cmd_id = value_command.get("id", "N/A_val_src")
        rospy.logdebug(f"RobotExecutor (CmdID {cmd_id}): Getting value from source: type='{cmd_type}', subtype='{cmd_subtype}'")
        if cmd_type == "battery" and cmd_subtype == "status":
            val = self.battery_monitor.get_battery_level_numeric()
            return float(val) if val is not None else None
        elif cmd_type == "measure" and cmd_subtype == "distance":
            if self.distance_measurer is None:
                rospy.logwarn(f"RobotExecutor (CmdID {cmd_id}): DistanceMeasurer not available.")
                return float('inf')
            angle = cmd_config.get("angle_deg_total", self.default_measure_angle)
            dist = self.distance_measurer.get_overall_minimum_distance(measurement_angle_deg_total=angle)
            rospy.loginfo(f"RobotExecutor (CmdID {cmd_id}): Overall measured distance (angle {angle}deg): {dist if dist != float('inf') else 'inf'}")
            return dist
        else:
            rospy.logwarn(f"RobotExecutor (CmdID {cmd_id}): Unsupported value source: type='{cmd_type}', subtype='{cmd_subtype}'")
            return None

    def evaluate_conditions(self, conditions_block):
        if not conditions_block:
            return True 
        for item in conditions_block:
            cond_id = item.get("id", "N/A_cond")
            type = item.get("type")
            subtype = item.get("subtype")
            config = item.get("config", {})
            rospy.logdebug(f"RobotExecutor (CondID {cond_id}): Evaluating item: type='{type}', subtype='{subtype}'")
            if type == "logic":
                if subtype == "true":
                    rospy.loginfo(f"RobotExecutor (CondID {cond_id} - logic.true): TRUE.")
                    continue
                elif subtype == "false":
                    rospy.loginfo(f"RobotExecutor (CondID {cond_id} - logic.false): FALSE.")
                    return False
                else:
                    rospy.logwarn(f"RobotExecutor (CondID {cond_id}): Unknown logic subtype '{subtype}'. FALSE.")
                    return False
            elif type == "math":
                val_a_src = config.get("value_a_source") or config.get("value_a_commands")
                val_a = self._get_value_from_command_source(val_a_src[0]) if val_a_src and isinstance(val_a_src, list) and len(val_a_src) > 0 else config.get("value_a")
                if val_a is not None and not isinstance(val_a, (int, float)):
                    try:
                        val_a = float(val_a)
                    except (ValueError, TypeError):
                        rospy.logerr(f"RobotExecutor (CondID {cond_id}): Direct value_a '{val_a}' not num.")
                        return False
                if val_a is None:
                    rospy.logerr(f"RobotExecutor (CondID {cond_id}): Could not determine value_a.")
                    return False
                op = subtype
                val_b = config.get("value_b")
                if val_b is None:
                    rospy.logerr(f"RobotExecutor (CondID {cond_id}): value_b is missing.")
                    return False
                try:
                    val_b_num = float(val_b)
                except (ValueError, TypeError):
                    rospy.logerr(f"RobotExecutor (CondID {cond_id}): value_b '{val_b}' not num.")
                    return False
                res = self.compare(val_a, op, val_b_num)
                rospy.loginfo(f"RobotExecutor (CondID {cond_id} - math: ({val_a} {op} {val_b_num})): Result: {res}")
                if not res:
                    return False
            else:
                rospy.logwarn(f"RobotExecutor (CondID {cond_id}): Unknown condition type '{type}'. FALSE.")
                return False
        rospy.loginfo("RobotExecutor.evaluate_conditions: All conditions in block evaluated to TRUE.")
        return True

    def execute_command(self, command):
        command_id = command.get("id", "N/A")
        command_type = command.get("type")
        subtype = command.get("subtype")
        config = command.get("config", {})
        
        rospy.logdebug(f"RobotExecutor: Attempting cmd ID: {command_id}, Type: {command_type}, Subtype: {subtype}")

        base_result = super().execute_command(command) 

        if base_result in [SIGNAL_BREAK, SIGNAL_CONTINUE, SIGNAL_FATAL_ERROR]:
            rospy.logdebug(f"RobotExecutor (CmdID {command_id}): Propagating signal from base: {base_result}")
            return base_result
        if base_result is None: 
            rospy.logdebug(f"RobotExecutor (CmdID {command_id}): Handled by base, completed normally.")
            return None 
        
        if base_result is False: 
            rospy.logdebug(f"RobotExecutor (CmdID {command_id}): Not handled by base. Robot-specific execution.")
            
            if command_type == "move": 
                marker_id = command.get("marker_id") 
                if marker_id is not None:
                    rospy.loginfo(f"RobotExecutor (CmdID {command_id}): Executing move to marker_id: {marker_id}")
                    if self.move_to_marker.send_goal(marker_id):
                        move_result = self.move_to_marker.wait_for_goal_completion(
                            obstacle_distance_threshold=self.move_obstacle_threshold,
                            obstacle_measure_angle_deg=self.move_obstacle_check_angle
                        )
                        if move_result is GOAL_COMPLETION_OBSTACLE:
                            rospy.logerr(f"RobotExecutor (CmdID {command_id}): Move to marker {marker_id} STOPPED due to OBSTACLE.")
                            return SIGNAL_FATAL_ERROR 
                        elif not move_result: 
                            rospy.logwarn(f"RobotExecutor (CmdID {command_id}): Move to marker {marker_id} did not complete successfully (timeout/error).")
                    else:
                        rospy.logerr(f"RobotExecutor (CmdID {command_id}): Failed to send goal for marker_id: {marker_id}.")
                else:
                    rospy.logwarn(f"RobotExecutor (CmdID {command_id}): Move command missing 'marker_id'. Skipping.")
                return None 
            
            elif command_type == "trajectory" and subtype == "line": 
                marker_id = config.get("destination_marker_id")
                if marker_id is not None:
                    rospy.loginfo(f"RobotExecutor (CmdID {command_id}): Executing trajectory:line to marker_id: {marker_id}")
                    with open(self.move_to_marker.json_path, 'r') as f:
                        markers = json.load(f)
                    marker = next((m for m in markers if m["id"] == marker_id), None)
                    if not marker:
                        rospy.logerr(f"RobotExecutor (CmdID {command_id}): Marker {marker_id} not found.")
                        return SIGNAL_FATAL_ERROR
                    
                    end_point = np.array([marker["x"], marker["y"]])
                    
                    rospy.loginfo(f"Waiting for current pose from {self.pose_topic}...")
                    start_time = rospy.Time.now().to_sec()
                    timeout = 5.0
                    while self.current_pose is None and (rospy.Time.now().to_sec() - start_time) < timeout:
                        rospy.sleep(0.1)
                    if self.current_pose is None:
                        rospy.logerr(f"RobotExecutor (CmdID {command_id}): Failed to get current pose from {self.pose_topic}.")
                        return SIGNAL_FATAL_ERROR
                    
                    start_point = self.current_pose[:2]
                    rospy.loginfo(f"Setting line path from {start_point} to {end_point}")
                    
                    if not self.mpc_controller.set_line_path(start_point, end_point):
                        rospy.logerr(f"RobotExecutor (CmdID {command_id}): Failed to set line path.")
                        return SIGNAL_FATAL_ERROR
                    
                    self.mpc_controller.start_time = rospy.Time.now().to_sec()
                    self.mpc_controller.reached_goal = False
                    rate = rospy.Rate(1.0 / self.mpc_controller.dt)
                    while not rospy.is_shutdown() and not self.mpc_controller.reached_goal:
                        if self.current_pose is None:
                            rospy.logwarn_throttle(1.0, "No pose data available. Skipping control iteration.")
                            rate.sleep()
                            continue
                        
                        if self.distance_measurer is not None:
                            dist = self.distance_measurer.get_overall_minimum_distance(
                                measurement_angle_deg_total=self.move_obstacle_check_angle
                            )
                            if dist < self.move_obstacle_threshold:
                                rospy.logerr(f"RobotExecutor (CmdID {command_id}): Trajectory to marker {marker_id} STOPPED by OBSTACLE (distance {dist:.2f}m).")
                                self.cmd_vel_pub.publish(Twist())
                                return SIGNAL_FATAL_ERROR
                        
                        x, y, theta = self.current_pose
                        v, omega = self.mpc_controller.mpc_control(x, y, theta)
                        
                        twist_msg = Twist()
                        twist_msg.linear.x = v
                        twist_msg.angular.z = omega
                        self.cmd_vel_pub.publish(twist_msg)
                        
                        rate.sleep()
                    
                    self.cmd_vel_pub.publish(Twist())
                    rospy.loginfo(f"RobotExecutor (CmdID {command_id}): Trajectory to marker {marker_id} completed.")
                    return None
                else:
                    rospy.logwarn(f"RobotExecutor (CmdID {command_id}): Trajectory:line missing 'destination_marker_id'.")
                    return None

            elif command_type == "battery":
                if subtype == "charging":
                    rospy.loginfo(f"RobotExecutor (CmdID {command_id}): Charging.")
                    self.battery_monitor.start_charging()
                elif subtype == "status":
                    rospy.loginfo(f"RobotExecutor (CmdID {command_id}): Battery status: {self.battery_monitor.update_battery_status()}")
                else:
                    rospy.logwarn(f"RobotExecutor (CmdID {command_id}): Unknown battery subtype: '{subtype}'")
                return None

            elif command_type == "log":
                message = config.get("message", f"Log CmdID: {command_id}")
                log_level = config.get("level", "info").lower()
                if log_level == "warn":
                    rospy.logwarn(f"PROGRAM LOG: {message}")
                elif log_level == "error":
                    rospy.logerr(f"PROGRAM LOG: {message}")
                else:
                    rospy.loginfo(f"PROGRAM LOG: {message}")
                return None

            elif command_type == "programming" and subtype == "call_program":
                called_program_name = config.get("called_program_name")
                if not called_program_name:
                    rospy.logerr(f"RobotExecutor (CmdID {command_id}): 'called_program_name' missing for call_program.")
                    return SIGNAL_FATAL_ERROR 
                rospy.loginfo(f"RobotExecutor (CmdID {command_id}): Calling subprogram '{called_program_name}'...")
                sub_program_commands = self.loaded_sub_programs.get(called_program_name)
                if sub_program_commands is None:
                    rospy.logerr(f"RobotExecutor (CmdID {command_id}): Subprogram '{called_program_name}' not found.")
                    return SIGNAL_FATAL_ERROR 
                if not isinstance(sub_program_commands, list):
                    rospy.logerr(f"RobotExecutor (CmdID {command_id}): Commands for subprogram '{called_program_name}' not a list.")
                    return SIGNAL_FATAL_ERROR
                rospy.loginfo(f"--- Starting subprogram: {called_program_name} ({len(sub_program_commands)} commands) ---")
                final_sub_result = None
                for sub_cmd_idx, sub_cmd in enumerate(sub_program_commands):
                    if rospy.is_shutdown():
                        rospy.logwarn(f"Subprogram '{called_program_name}' interrupted by ROS shutdown (cmd {sub_cmd_idx+1}).")
                        final_sub_result = SIGNAL_FATAL_ERROR
                        break
                    sub_cmd_result = self.execute_command(sub_cmd)
                    if sub_cmd_result is SIGNAL_FATAL_ERROR:
                        rospy.logerr(f"FATAL ERROR in subprogram '{called_program_name}'. Propagating.")
                        final_sub_result = SIGNAL_FATAL_ERROR
                        break
                rospy.loginfo(f"--- Finished subprogram: {called_program_name} ---")
                return final_sub_result if final_sub_result is SIGNAL_FATAL_ERROR else None
            else:
                rospy.logwarn(f"RobotExecutor (CmdID {command_id}): Unsupported command: type='{command_type}', subtype='{subtype}'")
                return None 
        
        rospy.logerr(f"RobotExecutor (CmdID {command_id}): Unexpected result from base_result.execute_command(): {base_result}")
        return None

    def execute_program(self, json_data_list):
        if not isinstance(json_data_list, list): 
            rospy.logerr(f"execute_program expects list, got {type(json_data_list)}")
            if isinstance(json_data_list, dict) and "name" in json_data_list:
                json_data_list = [json_data_list]
            else:
                return
        if not json_data_list:
            rospy.logerr("No JSON program data (empty list).")
            return

        for program_idx, program_data in enumerate(json_data_list):
            if not isinstance(program_data, dict):
                rospy.logerr(f"Program item {program_idx} not dict: {program_data}")
                continue
            program_name = program_data.get("name", f"Unnamed_Program_{program_idx}")
            commands = program_data.get("commands", [])
            if not isinstance(commands, list):
                rospy.logerr(f"Commands for '{program_name}' not list: {commands}")
                continue
            rospy.loginfo(f"Executing program: '{program_name}' ({len(commands)} commands)")
            if rospy.is_shutdown():
                rospy.logwarn(f"ROS shutdown before '{program_name}'")
                break 
            for cmd_idx, command_item in enumerate(commands):
                if rospy.is_shutdown():
                    rospy.logwarn(f"Program '{program_name}' interrupted (cmd {cmd_idx+1}).")
                    return 
                cmd_result = self.execute_command(command_item) 
                if cmd_result is SIGNAL_FATAL_ERROR:
                    rospy.logerr(f"FATAL ERROR in program '{program_name}'. Halting.")
                    return 
            if rospy.is_shutdown():
                rospy.logwarn(f"Program '{program_name}' incomplete due to ROS shutdown.")
                return
            else:
                rospy.loginfo(f"Finished program: '{program_name}'")

def main():
    node_name = 'mir100_program_runner_final'
    try:
        rospy.init_node(node_name, anonymous=False) 
        rospy.loginfo(f"ROS Node '{node_name}' initialized.")

        base_path = "/home/duc/Downloads/MIR100_WebApp/database_json/"
        queue_json_path = os.path.join(base_path, "queue_programming.json")
        marker_json_path = os.path.join(base_path, "position_marker.json")
        subprograms_definition_path = os.path.join(base_path, "programming_json.json")
        simulation_state_path = os.path.join(base_path, "simulation_state.json")

        front_lidar_param = rospy.get_param("~front_lidar_topic", "/f_scan") 
        back_lidar_param = rospy.get_param("~back_lidar_topic", "/b_scan")   
        measure_angle_total_param = rospy.get_param("~measure_angle_deg", 10.0)
        move_obstacle_thresh_param = rospy.get_param("~move_obstacle_threshold", 0.45)
        move_obstacle_angle_param = rospy.get_param("~move_obstacle_angle_deg", 30.0)

        rospy.loginfo(f"Queue file: {queue_json_path}")
        rospy.loginfo(f"Subprograms file: {subprograms_definition_path}")
        rospy.loginfo(f"Marker file: {marker_json_path}")
        rospy.loginfo(f"Simulation state file: {simulation_state_path}")
        rospy.loginfo(f"Front LiDAR: {front_lidar_param}, Back LiDAR: {back_lidar_param if back_lidar_param else 'None'}")
        rospy.loginfo(f"Measure angle: {measure_angle_total_param} deg, Move obstacle check: thresh={move_obstacle_thresh_param}m, angle={move_obstacle_angle_param}deg")

        if not os.path.exists(marker_json_path):
            rospy.logwarn(f"Marker file {marker_json_path} not found. Creating dummy.")
            dummy_markers = [
                {"id": 1, "name":"Marker1", "x": 1.0, "y": 0.0, "w": 1.0, "z": 0.0},
                {"id": 3, "name":"Marker3", "x": -1.0, "y": 0.5, "w": 0.707, "z": 0.707},
                {"id": "Move_Loop_Marker_1", "name":"ML_M1", "x": 0.5, "y": 0.5, "w": 1.0, "z": 0.0},
                {"id": "Move_Loop_Marker_3", "name":"ML_M3", "x": -0.5, "y": -0.5, "w": 0.0, "z": 1.0}
            ]
            try:
                marker_dir = os.path.dirname(marker_json_path)
                if not os.path.exists(marker_dir) and marker_dir:
                    os.makedirs(marker_dir)
                with open(marker_json_path, 'w') as f:
                    json.dump(dummy_markers, f, indent=4)
                rospy.loginfo(f"Created dummy marker file: {marker_json_path}")
            except Exception as e:
                rospy.logerr(f"Could not create dummy marker file: {e}")
                return

        initial_sim_battery = 100 
        executor = RobotProgramExecutor(
            marker_json_path=marker_json_path,
            sub_programs_json_path=subprograms_definition_path,
            initial_battery_level=initial_sim_battery,
            front_lidar_topic=front_lidar_param if front_lidar_param else None,
            back_lidar_topic=back_lidar_param if back_lidar_param else None,
            measure_distance_angle_deg_total=measure_angle_total_param,
            move_obstacle_threshold=move_obstacle_thresh_param,
            move_obstacle_check_angle=move_obstacle_angle_param,
            simulation_state_path=simulation_state_path
        )
        
        if not os.path.exists(queue_json_path):
            rospy.logerr(f"Main program queue JSON file not found: {queue_json_path}")
            return
        try:
            with open(queue_json_path, 'r') as f:
                main_program_data = json.load(f)
            rospy.loginfo(f"Loaded main program queue data from {queue_json_path}")
        except Exception as e:
            rospy.logerr(f"Error reading/parsing main program queue JSON {queue_json_path}: {e}")
            return
        
        if main_program_data:
            executor.execute_program(main_program_data) 
        else:
            rospy.logwarn("Main program queue data empty.")
        
        rospy.loginfo("All programs from the main queue file have been processed.")

    except rospy.ROSInterruptException:
        rospy.loginfo(f"Execution of '{node_name}' interrupted.")
    except Exception as e:
        rospy.logfatal(f"An unexpected error in main of '{node_name}': {e}", exc_info=True)
    finally:
        rospy.loginfo(f"Shutting down node '{node_name}'.")

if __name__ == '__main__':
    main()