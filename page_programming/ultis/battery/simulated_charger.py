#!/usr/bin/env python
"""
Simulated battery charging for MIR100 robot in simulation mode.
Navigates to a docking position by publishing to /move_base_simple/goal and simulates battery charging.
"""

import rospy
import json
import os
import numpy as np
from geometry_msgs.msg import Twist, PoseStamped, PoseWithCovarianceStamped
from std_msgs.msg import Header
from battery.battery_status import BatteryChecker

class SimulatedCharger:
    """
    Handles simulated battery charging by navigating to a docker position and incrementing battery level.
    """
    def __init__(self, 
                 docker_json_path="/database_json/docker.json",
                 simulation_state_path="/simulation_state.json",
                 battery_file_path="database_json/battery_percent.json",
                 move_obstacle_threshold=0.1,
                 move_obstacle_check_angle=20.0,
                 charge_rate_percent_per_30s=1.0,
                 front_lidar_topic="/f_scan",
                 back_lidar_topic="/b_scan",
                 measure_distance_angle_deg_total=10.0,
                 pose_topic="/amcl_pose",
                 goal_tolerance=0.2):
        """
        Initialize the SimulatedCharger.

        Args:
            docker_json_path (str): Path to docker JSON file with docking position.
            simulation_state_path (str): Path to simulation state JSON file.
            battery_file_path (str): Path to battery percentage JSON file.
            move_obstacle_threshold (float): Distance threshold for obstacle detection (meters).
            move_obstacle_check_angle (float): Angle for obstacle checking (degrees).
            charge_rate_percent_per_30s (float): Battery percentage increase per 30 seconds.
            front_lidar_topic (str): ROS topic for front LiDAR.
            back_lidar_topic (str): ROS topic for back LiDAR.
            measure_distance_angle_deg_total (float): Default angle for distance measurement.
            pose_topic (str): ROS topic for robot pose (default: /amcl_pose for simulation).
            goal_tolerance (float): Distance tolerance to consider goal reached (meters).
        """
        self.docker_json_path = docker_json_path
        self.simulation_state_path = simulation_state_path
        self.battery_file_path = battery_file_path
        self.move_obstacle_threshold = move_obstacle_threshold
        self.move_obstacle_check_angle = move_obstacle_check_angle
        self.charge_rate_percent_per_30s = charge_rate_percent_per_30s
        self.pose_topic = pose_topic
        self.goal_tolerance = goal_tolerance
        self.current_pose = None
        
        # Initialize battery checker
        self.battery_checker = BatteryChecker(
            simulation_state_path=simulation_state_path,
            battery_file_path=battery_file_path
        )
        
        # Initialize distance measurer for obstacle detection (if available)
        self.distance_measurer = None
        try:
            from measure.measure_distance import DistanceMeasurer
            self.distance_measurer = DistanceMeasurer(
                front_scan_topic=front_lidar_topic,
                back_scan_topic=back_lidar_topic,
                default_measurement_angle_deg_total=measure_distance_angle_deg_total
            )
        except ImportError:
            rospy.logwarn("Failed to import DistanceMeasurer. Obstacle checking disabled.")
        
        # ROS publishers and subscribers
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.goal_pub = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=10)
        rospy.Subscriber(self.pose_topic, PoseWithCovarianceStamped, self._pose_callback, queue_size=1)
        
        # Load simulation state
        self.simulation_mode = self._load_simulation_state()
        rospy.loginfo(f"SimulatedCharger initialized in {'simulation' if self.simulation_mode else 'real'} mode.")

    def _load_simulation_state(self):
        """
        Load simulation state from JSON file to determine if running in simulation mode.
        Returns True for simulation, False for real mode.
        """
        try:
            with open(self.simulation_state_path, 'r') as f:
                state = json.load(f)
            simulation_running = state.get("simulation_running", False)
            rospy.loginfo(f"Loaded simulation state: {'simulation' if simulation_running else 'real'}")
            return simulation_running
        except Exception as e:
            rospy.logwarn(f"Failed to load simulation state from {self.simulation_state_path}: {e}. Defaulting to simulation mode.")
            return True  # Default to simulation mode

    def _pose_callback(self, msg):
        """
        Callback for robot pose updates.
        Updates self.current_pose with [x, y].
        """
        pose_msg = msg.pose.pose
        self.current_pose = np.array([pose_msg.position.x, pose_msg.position.y])
        rospy.logdebug(f"Updated pose: x={self.current_pose[0]:.2f}, y={self.current_pose[1]:.2f}")

    def _load_docker_position(self):
        """
        Load docker position from JSON file.
        Returns tuple (marker_id, pose_dict) or (None, None) if not found.
        """
        if not os.path.exists(self.docker_json_path):
            rospy.logwarn(f"Docker JSON file not found: {self.docker_json_path}. Creating dummy.")
            dummy_docker = {
                "marker_id": "docker_station",
                "name": "Docker",
                "x": 0.0,
                "y": 0.0,
                "w": 1.0,
                "z": 0.0
            }
            try:
                docker_dir = os.path.dirname(self.docker_json_path)
                if not os.path.exists(docker_dir) and docker_dir:
                    os.makedirs(docker_dir)
                with open(self.docker_json_path, 'w') as f:
                    json.dump(dummy_docker, f, indent=4)
                rospy.loginfo(f"Created dummy docker file: {self.docker_json_path}")
                return dummy_docker["marker_id"], dummy_docker
            except Exception as e:
                rospy.logerr(f"Could not create dummy docker file: {e}")
                return None, None
        
        try:
            with open(self.docker_json_path, 'r') as f:
                docker_data = json.load(f)
            if isinstance(docker_data, list) and len(docker_data) > 0:
                # Handle list case
                docker = docker_data[0]
                marker_id = docker.get("id")
                if not marker_id or not all(k in docker for k in ["x", "y", "z", "w"]):
                    rospy.logerr(f"Invalid docker JSON structure in list: {docker_data}")
                    return None, None
                return marker_id, docker
            elif isinstance(docker_data, dict) and "marker_id" in docker_data:
                # Handle single dictionary case
                if not all(k in docker_data for k in ["x", "y", "z", "w"]):
                    rospy.logerr(f"Invalid docker JSON structure in dict: {docker_data}")
                    return None, None
                return docker_data["marker_id"], docker_data
            else:
                rospy.logerr(f"Invalid docker JSON structure: {docker_data}")
                return None, None
        except Exception as e:
            rospy.logerr(f"Error loading docker JSON {self.docker_json_path}: {e}")
            return None, None

    def _wait_for_goal_completion(self, target_pose, timeout=60.0):
        """
        Wait for the robot to reach the target pose using move_base_simple.
        Returns True if successful, False if timeout or obstacle detected.
        """
        start_time = rospy.Time.now().to_sec()
        rate = rospy.Rate(10)  # 10 Hz
        target_position = np.array([target_pose["x"], target_pose["y"]])
        
        while not rospy.is_shutdown() and (rospy.Time.now().to_sec() - start_time) < timeout:
            if self.distance_measurer is not None:
                dist = self.distance_measurer.get_overall_minimum_distance(
                    measurement_angle_deg_total=self.move_obstacle_check_angle
                )
                if dist < self.move_obstacle_threshold:
                    rospy.logerr(f"SimulatedCharger: Move to docker STOPPED due to OBSTACLE (distance {dist:.2f}m).")
                    self.cmd_vel_pub.publish(Twist())
                    return False
            
            if self.current_pose is None:
                rospy.logwarn(f"SimulatedCharger: Waiting for pose data from {self.pose_topic}")
                rate.sleep()
                continue
            
            distance_to_goal = np.linalg.norm(self.current_pose - target_position)
            if distance_to_goal < self.goal_tolerance:
                rospy.loginfo(f"SimulatedCharger: Reached goal: Distance to goal {distance_to_goal:.2f}m < tolerance {self.goal_tolerance}m")
                self.cmd_vel_pub.publish(Twist())
                return True
            
            rate.sleep()
        
        rospy.logwarn("SimulatedCharger: Move to docker timed out.")
        self.cmd_vel_pub.publish(Twist())
        return False

    def charge_battery(self, target_battery_level=100.0):
        """
        Navigate to docker position and simulate battery charging in simulation mode.
        In real mode, returns False without action.
        
        Args:
            target_battery_level (float): Desired battery level to reach (default: 100.0%)
        
        Returns:
            bool: True if charging completed successfully, False otherwise.
        """
        if not self.simulation_mode:
            rospy.logwarn("SimulatedCharger: Cannot charge in real mode. Use RealCharger instead.")
            return False

        # Load docker position
        marker_id, docker_pose = self._load_docker_position()
        if not marker_id or not docker_pose:
            rospy.logerr("SimulatedCharger: Failed to load docker position marker_id.")
            return False

        # Create and publish move_base_simple goal
        goal_msg = PoseStamped()
        goal_msg.header = Header(stamp=rospy.Time.now(), frame_id="map")
        goal_msg.pose.position.x = docker_pose["x"]
        goal_msg.pose.position.y = docker_pose["y"]
        goal_msg.pose.orientation.z = docker_pose["z"]
        goal_msg.pose.orientation.w = docker_pose["w"]

        rospy.loginfo(f"SimulatedCharger: Publishing goal to /move_base_simple/goal for marker_id: {marker_id} at x={docker_pose['x']}, y={docker_pose['y']}")
        self.goal_pub.publish(goal_msg)

        # Wait for goal completion
        if not self._wait_for_goal_completion(docker_pose):
            rospy.logerr(f"SimulatedCharger: Failed to reach docker marker {marker_id}.")
            return False

        # Simulate charging
        rospy.loginfo(f"SimulatedCharger: Reached docker. Starting simulated charging to {target_battery_level}%")
        current_level = self.battery_checker.check_battery()
        if current_level is None:
            rospy.logerr("SimulatedCharger: Failed to get current battery level.")
            return False

        rate = rospy.Rate(1.0 / 30.0)  # Check every 30 seconds
        while current_level < target_battery_level and not rospy.is_shutdown():
            current_level += self.charge_rate_percent_per_30s
            current_level = min(current_level, 100.0)  # Cap at 100%
            self.battery_checker.update_battery_level(current_level)  # Update simulated battery
            rospy.loginfo(f"SimulatedCharger: Battery level increased to {current_level:.1f}%")
            rate.sleep()

        self.cmd_vel_pub.publish(Twist())  # Ensure robot stops
        rospy.loginfo(f"SimulatedCharger: Charging completed at {current_level:.1f}%")
        return True