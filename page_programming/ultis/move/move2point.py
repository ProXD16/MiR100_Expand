#!/usr/bin/env python
import rospy
import json
import time 
from geometry_msgs.msg import PoseStamped, Twist
from actionlib_msgs.msg import GoalStatusArray, GoalStatus, GoalID

try:
    from page_programming.ultis.measure.measure_distance import DistanceMeasurer 
except ImportError:
    rospy.logerr("Failed to import DistanceMeasurer from distance_measurer.py. Obstacle checking during move will be disabled.")
    DistanceMeasurer = None 

GOAL_COMPLETION_OBSTACLE = 99 
GOAL_COMPLETION_TIMEOUT = 98
GOAL_COMPLETION_INTERRUPTED = 97
GOAL_COMPLETION_ERROR = 96

class MoveToMarker:
    def __init__(self, json_path, distance_measurer_instance=None):
        self.json_path = json_path
        self.json_data = self._load_json_data()
        self.goal_status_code = None
        self.current_goal_id_str = None
        
        if not rospy.core.is_initialized():
            rospy.logfatal("MoveToMarker: ROS Master not found or rospy.init_node() has not been called.")
            raise RuntimeError("ROS not initialized for MoveToMarker")

        self.pub_goal = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=1)
        self.pub_cancel = rospy.Publisher('/move_base/cancel', GoalID, queue_size=1)
        self.sub_status = rospy.Subscriber('/move_base/status', GoalStatusArray, self.status_callback)
        
        self.distance_measurer = None
        if DistanceMeasurer is not None:
            self.distance_measurer = distance_measurer_instance
        
        if self.distance_measurer is None:
            rospy.logwarn("MoveToMarker: DistanceMeasurer instance not provided or import failed. Obstacle check disabled.")

        rospy.loginfo("MoveToMarker: Initializing...")
        rospy.sleep(1.0) 
        rospy.loginfo("MoveToMarker: Initialized.")

    def _load_json_data(self):
        try:
            with open(self.json_path, 'r') as file: data = json.load(file)
            rospy.loginfo(f"MoveToMarker: Loaded marker data from {self.json_path}"); return data
        except FileNotFoundError: rospy.logerr(f"MoveToMarker: Marker JSON file not found: {self.json_path}"); return None
        except json.JSONDecodeError as e: rospy.logerr(f"MoveToMarker: Error decoding JSON: {e}"); return None
        except Exception as e: rospy.logerr(f"MoveToMarker: Error reading marker JSON file: {e}"); return None

    def get_marker_pose(self, marker_id):
        if not self.json_data: rospy.logerr("MoveToMarker: No marker JSON data."); return None
        for marker in self.json_data:
            if marker.get('id') == marker_id:
                x, y, oz, ow = marker.get('x'), marker.get('y'), marker.get('z'), marker.get('w')
                if None in [x, y, oz, ow]: rospy.logwarn(f"MoveToMarker: Marker ID {marker_id} incomplete pose."); return None
                return x, y, oz, ow
        rospy.logwarn(f"MoveToMarker: Marker ID {marker_id} not found."); return None

    def status_callback(self, msg):
        if msg.status_list:
            latest = msg.status_list[-1]
            if self.current_goal_id_str is None or (latest.goal_id and latest.goal_id.id == self.current_goal_id_str):
                if self.goal_status_code != latest.status:
                    rospy.logdebug(f"MoveToMarker: Goal '{latest.goal_id.id}' status: {latest.text} ({latest.status})")
                self.goal_status_code = latest.status
                if latest.goal_id and latest.goal_id.id: self.current_goal_id_str = latest.goal_id.id

    def send_goal(self, marker_id):
        pose = self.get_marker_pose(marker_id)
        if not pose: return False
        x,y,oz,ow = pose
        goal = PoseStamped(); goal.header.frame_id="map"; goal.header.stamp=rospy.Time.now()
        goal.pose.position.x=x; goal.pose.position.y=y; goal.pose.position.z=0.0
        goal.pose.orientation.x=0.0; goal.pose.orientation.y=0.0; goal.pose.orientation.z=oz; goal.pose.orientation.w=ow
        self.goal_status_code=None; self.current_goal_id_str=None
        if self.pub_goal.get_num_connections()==0: rospy.logwarn("MoveToMarker: No subscribers for /move_base_simple/goal.")
        self.pub_goal.publish(goal)
        rospy.loginfo(f"MoveToMarker: Sent goal to marker {marker_id}."); return True

    def cancel_current_goal(self):
        if self.current_goal_id_str:
            rospy.loginfo(f"MoveToMarker: Cancelling goal ID: {self.current_goal_id_str}")
            self.pub_cancel.publish(GoalID(id=self.current_goal_id_str, stamp=rospy.Time(0)))
        else: rospy.logwarn("MoveToMarker: No current_goal_id_str to cancel.")

    def wait_for_goal_completion(self, timeout_secs=60.0, 
                                 obstacle_check_interval_secs=0.25, 
                                 # Sửa tên tham số ở đây để khớp với cách gọi:
                                 obstacle_distance_threshold=0.1, 
                                 obstacle_measure_angle_deg=15.0):
        start_time = rospy.get_time()
        rate = rospy.Rate(10) 
        last_obstacle_check_time = rospy.get_time()

        # Chờ ID mục tiêu (nếu cần)
        wait_for_id_timeout = rospy.get_time() + 2.0
        while self.current_goal_id_str is None and rospy.get_time() < wait_for_id_timeout and not rospy.is_shutdown():
            rate.sleep()
        if self.current_goal_id_str is None and not rospy.is_shutdown():
             rospy.logwarn("MoveToMarker: Failed to get current_goal_id_str from status. Obstacle check might be less reliable.")

        rospy.loginfo(f"MoveToMarker: Waiting for goal '{self.current_goal_id_str}' (timeout: {timeout_secs:.1f}s).")
        if self.distance_measurer:
            rospy.loginfo(f"MoveToMarker: Obstacle check: interval={obstacle_check_interval_secs:.2f}s, "
                          f"threshold={obstacle_distance_threshold:.2f}m, angle={obstacle_measure_angle_deg:.1f}deg.")
        
        while not rospy.is_shutdown():
            current_time = rospy.get_time()
            if (current_time - start_time) > timeout_secs:
                rospy.logwarn(f"MoveToMarker: Timeout for goal '{self.current_goal_id_str}'."); self.cancel_current_goal(); return GOAL_COMPLETION_TIMEOUT 

            if self.goal_status_code is not None:
                if self.goal_status_code == GoalStatus.SUCCEEDED:
                    rospy.loginfo(f"MoveToMarker: Goal '{self.current_goal_id_str}' SUCCEEDED."); return True
                terminal_states = [GoalStatus.PREEMPTED, GoalStatus.ABORTED, GoalStatus.REJECTED, GoalStatus.RECALLED, GoalStatus.LOST]
                if self.goal_status_code in terminal_states:
                    rospy.logerr(f"MoveToMarker: Goal '{self.current_goal_id_str}' FAILED (status: {self.goal_status_code})"); return False
            
            if self.distance_measurer and (current_time - last_obstacle_check_time) >= obstacle_check_interval_secs:
                dist = self.distance_measurer.get_overall_minimum_distance(
                    measurement_angle_deg_total=obstacle_measure_angle_deg # Sử dụng tên đã sửa
                )
                if dist < obstacle_distance_threshold: # Sử dụng tên đã sửa
                    rospy.logerr(f"MoveToMarker: OBSTACLE at {dist:.2f}m (thresh: {obstacle_distance_threshold:.2f}m) for goal '{self.current_goal_id_str}'. Cancelling.")
                    self.cancel_current_goal(); rospy.sleep(0.2); return GOAL_COMPLETION_OBSTACLE 
                last_obstacle_check_time = current_time
            
            rate.sleep()
        
        rospy.logwarn(f"MoveToMarker: Goal '{self.current_goal_id_str}' waiting interrupted by ROS shutdown."); return GOAL_COMPLETION_INTERRUPTED