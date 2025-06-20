#!/usr/bin/env python
import rospy
import json
from geometry_msgs.msg import PoseStamped
from actionlib_msgs.msg import GoalStatusArray, GoalStatus

class BatteryMonitor:
    def __init__(self, ip='192.168.0.172', auth_token='YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='):
        self.host = f'http://{ip}/api/v2.0.0/'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {auth_token}'
        }
        self.timeout = 2
        self.battery_level = 50  # Giả định pin luôn là 50% (> 20%)

    def update_battery_status(self):
        # Giả lập mức pin > 20% vì chưa chạy trên robot thật
        self.battery_level = 50
        return f"{self.battery_level}%"

    def start_charging(self):
        # Giả lập lệnh sạc (không gọi API thật)
        rospy.loginfo("Charging command sent (simulated)")
        return True

class MoveToMarker:
    def __init__(self, json_path="/home/duc/Downloads/MIR100_WebApp/database_json/position_marker.json"):
        self.json_path = json_path
        self.json_data = self._load_json_data()
        self.goal_status = None
        rospy.init_node('move_to_marker', anonymous=True)
        self.pub = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=10)
        self.sub = rospy.Subscriber('/move_base/status', GoalStatusArray, self.status_callback)
        rospy.sleep(1.0)
    
    def _load_json_data(self):
        try:
            with open(self.json_path, 'r') as file:
                data = json.load(file)
            return data
        except Exception as e:
            rospy.logerr(f"Error reading JSON file: {e}")
            return None
    
    def get_marker_pose(self, marker_id):
        if self.json_data is None:
            rospy.logerr("No JSON data available")
            return None
        for marker in self.json_data:
            if marker.get('id') == marker_id:
                return marker.get('x'), marker.get('y'), marker.get('w'), marker.get('z')
        rospy.logwarn(f"Marker ID {marker_id} not found in JSON data")
        return None
    
    def status_callback(self, msg):
        if not msg.status_list:
            return
        self.goal_status = msg.status_list[-1].status
        status_text = msg.status_list[-1].text
        if self.goal_status == GoalStatus.SUCCEEDED:
            pass
        elif self.goal_status == GoalStatus.ACTIVE:
            pass
        elif self.goal_status in [GoalStatus.PREEMPTED, GoalStatus.ABORTED, GoalStatus.REJECTED]:
            pass
    
    def send_goal(self, marker_id):
        pose = self.get_marker_pose(marker_id)
        if pose is None:
            return False
        x, y, w, z = pose
        goal = PoseStamped()
        goal.header.frame_id = "map"
        goal.header.stamp = rospy.Time.now()
        goal.pose.position.x = x
        goal.pose.position.y = y
        goal.pose.orientation.w = w
        goal.pose.orientation.z = z
        self.goal_status = None
        self.pub.publish(goal)
        rospy.loginfo(f"Sent goal to marker {marker_id}: x={x}, y={y}, w={w}, z={z}")
        return True
    
    def wait_for_goal_completion(self, timeout=60.0):
        start_time = rospy.get_time()
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            if self.goal_status is not None:
                if self.goal_status == GoalStatus.SUCCEEDED:
                    return True
                if self.goal_status in [GoalStatus.PREEMPTED, GoalStatus.ABORTED, GoalStatus.REJECTED]:
                    return False
            if rospy.get_time() - start_time > timeout:
                rospy.logwarn("Timeout waiting for goal completion")
                return False
            rate.sleep()
        return False

class ProgramExecutor:
    def __init__(self, json_path="/home/duc/Downloads/MIR100_WebApp/database_json/queue_programming.json"):
        self.json_path = json_path
        self.json_data = self._load_json_data()
        self.battery_monitor = BatteryMonitor()
        self.move_to_marker = MoveToMarker()

    def _load_json_data(self):
        try:
            with open(self.json_path, 'r') as file:
                data = json.load(file)
            return data
        except Exception as e:
            rospy.logerr(f"Error reading JSON file: {e}")
            return None

    def execute_command(self, command):
        command_type = command.get("type")
        subtype = command.get("subtype")

        if command_type == "move":
            marker_id = command.get("marker_id")
            if self.move_to_marker.send_goal(marker_id):
                if self.move_to_marker.wait_for_goal_completion():
                    rospy.loginfo(f"Successfully reached marker {marker_id}")
                else:
                    rospy.logwarn(f"Failed to reach marker {marker_id}")
            else:
                rospy.logerr(f"Failed to send goal for marker {marker_id}")

        elif command_type == "logic" and subtype == "if":
            conditions = command.get("conditions", [])
            for condition in conditions:
                if condition.get("type") == "math" and condition.get("subtype") == "less_than_or_equal_to":
                    value_a_commands = condition.get("config", {}).get("value_a_commands", [])
                    value_b = condition.get("config", {}).get("value_b")
                    for cmd in value_a_commands:
                        if cmd.get("type") == "battery" and cmd.get("subtype") == "status":
                            battery_status = self.battery_monitor.update_battery_status()
                            if battery_status != "--%":
                                battery_level = int(battery_status.strip("%"))
                                if battery_level <= value_b:
                                    for then_cmd in command.get("then_commands", []):
                                        self.execute_command(then_cmd)
                                    return

        elif command_type == "battery" and subtype == "charging":
            self.battery_monitor.start_charging()

    def execute_program(self):
        if self.json_data is None:
            rospy.logerr("No JSON data available")
            return

        for program in self.json_data:
            program_name = program.get("name")
            rospy.loginfo(f"Executing program: {program_name}")
            for command in program.get("commands", []):
                if command.get("type") == "logic" and command.get("subtype") == "loop":
                    iterations = command.get("config", {}).get("iterations", 1)
                    for _ in range(iterations):
                        for body_cmd in command.get("body_commands", []):
                            self.execute_command(body_cmd)

    def run(self):
        if not rospy.is_shutdown():
            self.execute_program()
            rospy.loginfo("Program execution completed")

if __name__ == '__main__':
    try:
        executor = ProgramExecutor()
        executor.run()
    except rospy.ROSInterruptException:
        rospy.logerr("ROS node interrupted")