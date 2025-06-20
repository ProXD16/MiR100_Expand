import rospy
from geometry_msgs.msg import Pose, Twist, PoseWithCovarianceStamped, PoseStamped
import numpy as np
import json
import actionlib
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import tf.transformations
from scipy.signal import butter, lfilter
from PIL import Image
from sensor_msgs.msg import LaserScan  # Added for LiDAR data
from threading import Lock  # Added for thread safety

class MPCController:
    def __init__(self, dt, v_max, v_min, omega_max, omega_min, lookahead_distance=0.5, filter_order=3, cutoff_frequency=2.0):
        self.dt = dt
        self.v_max = v_max
        self.v_min = v_min
        self.omega_max = omega_max
        self.omega_min = omega_min
        self.current_pose = None
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.trajectory_x = []
        self.trajectory_y = []
        self.start_point = None
        self.end_point = None
        self.total_length = 0.0
        self.distance_threshold = 0.5
        self.lookahead_distance = lookahead_distance
        self.reached_goal = False
        self.last_v = 0.0
        self.last_omega = 0.0
        self.velocity_data = []
        self.angular_velocity_data = []
        self.acceleration_data = []
        self.angular_acceleration_data = []
        self.time_data = []
        self.start_time = None
        self.filter_order = filter_order
        self.cutoff_frequency = cutoff_frequency
        self.map_image = None
        self.map_width = 0
        self.map_height = 0
        # New variables for LiDAR-based collision avoidance
        self.min_distance = float('inf')  # Initialize to infinity
        self.lidar_lock = Lock()  # Lock for thread-safe access
        self.fov_angle = np.deg2rad(60)  # 60-degree field of view
        self.safe_distance = 0.5  # Minimum safe distance in meters
        # Subscribe to /f_scan topic
        self.lidar_sub = rospy.Subscriber('/f_scan', LaserScan, self.lidar_callback, queue_size=1)

        if self.dt <= 0:
            rospy.logerr("dt must be positive for filter design. Disabling filter.")
            self.b, self.a = ([1], [1])
        else:
            nyquist_freq = 0.5 / self.dt
            normalized_cutoff = self.cutoff_frequency / nyquist_freq
            if normalized_cutoff >= 1.0:
                rospy.logwarn(f"Cutoff frequency ({self.cutoff_frequency} Hz) is at or above Nyquist frequency ({nyquist_freq} Hz). Clamping.")
                normalized_cutoff = 0.99
            elif normalized_cutoff <= 0:
                rospy.logwarn(f"Cutoff frequency ({self.cutoff_frequency} Hz) must be positive. Disabling filter.")
                self.b, self.a = ([1], [1])
            else:
                self.b, self.a = butter(self.filter_order, normalized_cutoff, btype='low', analog=False)

        self.ramp_up_duration = 2.0
        self.ramp_down_distance = 0.5
        self.velocity_smoothing_alpha = 0.3

    def lidar_callback(self, msg):
        """Process LiDAR data to find minimum distance within 60-degree FOV."""
        # Calculate the indices for the 60-degree FOV (±30 degrees)
        angle_min = msg.angle_min
        angle_max = msg.angle_max
        angle_increment = msg.angle_increment
        ranges = np.array(msg.ranges)

        # Replace invalid ranges (inf, nan) with a large value
        ranges = np.where(np.isinf(ranges) | np.isnan(ranges), 1000.0, ranges)

        # Find the index corresponding to the forward direction (0 degrees)
        center_index = len(ranges) // 2  # Assuming forward is at the middle
        half_fov = self.fov_angle / 2  # ±30 degrees

        # Calculate the index range for ±30 degrees
        indices_per_radian = 1 / angle_increment
        half_fov_indices = int(half_fov * indices_per_radian)
        start_index = max(0, center_index - half_fov_indices)
        end_index = min(len(ranges), center_index + half_fov_indices + 1)

        # Extract ranges within the FOV
        fov_ranges = ranges[start_index:end_index]

        # Find the minimum distance within the FOV
        min_distance = np.min(fov_ranges) if len(fov_ranges) > 0 else float('inf')

        # Update min_distance with thread-safe access
        with self.lidar_lock:
            self.min_distance = min_distance

    def load_map(self, map_path):
        try:
            self.map_image = Image.open(map_path)
            self.map_width, self.map_height = self.map_image.size
            rospy.loginfo(f"Loaded map image: {map_path}, size: {self.map_width}x{self.map_height}")
        except Exception as e:
            rospy.logwarn(f"Failed to load map image {map_path}: {e}")
            self.map_image = None

    def check_map_bounds(self, x, y):
        if self.map_image is None:
            return
        pixel_x = int(x / 0.05)
        pixel_y = int(self.map_height - y / 0.05)
        if 0 <= pixel_x < self.map_width and 0 <= pixel_y < self.map_height:
            rospy.logdebug(f"Robot position ({x:.2f}, {y:.2f}) within map bounds")
        else:
            rospy.logwarn(f"Robot position ({x:.2f}, {y:.2f}) outside map bounds")

    def lowpass_filter(self, data):
        if len(self.b) == 1 and self.b[0] == 1 and len(self.a) == 1 and self.a[0] == 1:
            return data
        padlen = 3 * max(len(self.a), len(self.b), self.filter_order)
        if len(data) <= padlen:
            return data
        try:
            y = lfilter(self.b, self.a, data)
            return y
        except ValueError as e:
            rospy.logwarn(f"Error during filtering: {e}. Returning unfiltered data. Data length: {len(data)}, padlen: {padlen}")
            return data

    def smooth_velocity(self, new_v, new_omega):
        smoothed_v = (1 - self.velocity_smoothing_alpha) * self.last_v + self.velocity_smoothing_alpha * new_v
        smoothed_omega = (1 - self.velocity_smoothing_alpha) * self.last_omega + self.velocity_smoothing_alpha * new_omega
        return smoothed_v, smoothed_omega
    
    def smooth_ramp_factor(self, factor):
        return np.sin(factor * np.pi / 2)

    def pose_callback(self, msg):
        pose_msg = msg.pose.pose
        quat = pose_msg.orientation
        norm_sq = quat.x**2 + quat.y**2 + quat.z**2 + quat.w**2
        if norm_sq < 1e-9:
            rospy.logwarn_throttle(5.0, "Invalid (zero) quaternion received, skipping pose update.")
            return

        try:
            euler = tf.transformations.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
            _, _, yaw = euler
        except Exception as e:
            rospy.logerr(f"Error converting quaternion to Euler: {e}")
            return

        self.x = pose_msg.position.x
        self.y = pose_msg.position.y
        self.theta = yaw
        self.current_pose = np.array([self.x, self.y, self.theta])
        self.trajectory_x.append(self.x)
        self.trajectory_y.append(self.y)
        self.check_map_bounds(self.x, self.y)

    def set_line_path(self, start_point, end_point):
        self.start_point = np.array([start_point[0], start_point[1]])
        self.end_point = np.array([end_point[0], end_point[1]])
        self.total_length = np.linalg.norm(self.end_point - self.start_point)
        if self.total_length < 1e-6:
            rospy.logwarn("Start and end points are too close. Invalid line path.")
            return False
        rospy.loginfo(f"Set line path from {self.start_point} to {self.end_point}, length {self.total_length:.2f}m")
        return True

    def get_point_on_path(self, s):
        if self.total_length < 1e-6:
            return np.array([self.x, self.y])
        s = np.clip(s, 0, self.total_length)
        t = s / self.total_length
        point = self.start_point + t * (self.end_point - self.start_point)
        return point

    def get_derivative_on_path(self, s):
        if self.total_length < 1e-6:
            return np.array([1.0, 0.0])
        direction = (self.end_point - self.start_point) / self.total_length
        return direction

    def find_closest_point_on_path(self, x, y):
        if self.total_length < 1e-6:
            return 0.0
        robot_pos = np.array([x, y])
        vec_to_robot = robot_pos - self.start_point
        direction = (self.end_point - self.start_point) / self.total_length
        s = np.dot(vec_to_robot, direction)
        s = np.clip(s, 0, self.total_length)
        return s

    def mpc_control(self, x, y, theta):
        if self.total_length < 1e-9:
            rospy.logwarn_throttle(1.0, "Line path is not defined or too short. Cannot perform MPC control.")
            return 0.0, 0.0

        closest_s = self.find_closest_point_on_path(x, y)
        lookahead_s = closest_s + self.lookahead_distance
        lookahead_s = np.clip(lookahead_s, 0, self.total_length)
        lookahead_pt = self.get_point_on_path(lookahead_s)
        lookahead_x, lookahead_y = lookahead_pt[0], lookahead_pt[1]

        final_goal_pt = self.get_point_on_path(self.total_length)
        final_goal_x, final_goal_y = final_goal_pt[0], final_goal_pt[1]
        distance_to_final_goal = np.sqrt((x - final_goal_x)**2 + (y - final_goal_y)**2)
        
        is_near_end_point = distance_to_final_goal < self.distance_threshold
        is_near_end_of_s = abs(self.total_length - closest_s) < self.distance_threshold * 1.5
        
        if is_near_end_point and is_near_end_of_s:
            rospy.loginfo("Reached the final goal!")
            self.reached_goal = True
            return 0.0, 0.0

        path_derivative = self.get_derivative_on_path(lookahead_s)
        dx_ds, dy_ds = path_derivative[0], path_derivative[1]
        angle_to_goal = np.arctan2(dy_ds, dx_ds)
        heading_error = angle_to_goal - theta
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))

        x_error_lookahead = lookahead_x - x
        y_error_lookahead = lookahead_y - y
        distance_error = np.sqrt(x_error_lookahead**2 + y_error_lookahead**2)

        heading_threshold = 0.1
        linear_speed_kp = 1.8
        angular_speed_kp = 1.8

        if abs(heading_error) > heading_threshold:
            v = self.v_max * 0.2
            if distance_error < self.lookahead_distance * 0.3 and abs(heading_error) > np.pi/4:
                v = 0.0
            omega = angular_speed_kp * heading_error
        else:
            v = linear_speed_kp * distance_error
            omega = angular_speed_kp * heading_error

        v, omega = self.smooth_velocity(v, omega)

        if self.start_time is not None:
            current_time = rospy.Time.now().to_sec()
            elapsed_time = current_time - self.start_time
            if elapsed_time < self.ramp_up_duration:
                ramp_factor = self.smooth_ramp_factor(elapsed_time / self.ramp_up_duration)
                v *= ramp_factor
                omega *= ramp_factor

        if distance_to_final_goal < self.ramp_down_distance:
            ramp_down_factor = self.smooth_ramp_factor(distance_to_final_goal / self.ramp_down_distance)
            v *= ramp_down_factor
            omega *= ramp_down_factor

        # Collision avoidance: Stop linear motion if obstacle is within 0.5m
        with self.lidar_lock:
            if self.min_distance < self.safe_distance:
                v = 0.0  # Stop moving forward
                rospy.logwarn(f"Obstacle detected within {self.min_distance:.2f}m, stopping linear motion.")

        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

        if self.start_time is not None:
            current_time_log = rospy.Time.now().to_sec()
            time_elapsed_log = current_time_log - self.start_time
            dt_accel = time_elapsed_log - self.time_data[-1] if self.time_data else time_elapsed_log
            if dt_accel > 1e-6:
                linear_acceleration = (v - self.last_v) / dt_accel
                angular_acceleration = (omega - self.last_omega) / dt_accel
            else:
                linear_acceleration = self.acceleration_data[-1] if self.acceleration_data else 0.0
                angular_acceleration = self.angular_acceleration_data[-1] if self.angular_acceleration_data else 0.0
            
            self.acceleration_data.append(linear_acceleration)
            self.angular_acceleration_data.append(angular_acceleration)
            self.velocity_data.append(v)
            self.angular_velocity_data.append(omega)
            self.time_data.append(time_elapsed_log)

        self.last_v = v
        self.last_omega = omega
        return v, omega

def main():
    rospy.init_node('line_mpc_node')
    
    dt = 0.05
    v_max = 0.3
    v_min = -0.3
    omega_max = 0.5
    omega_min = -0.5
    lookahead_distance = 0.5
    filter_order = 3
    cutoff_freq = 2.0

    controller = MPCController(dt, v_max, v_min, omega_max, omega_min,
                              lookahead_distance, filter_order, cutoff_freq)
    
    cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    move_base_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    
    # Load map image
    map_path = "static/map_image.png"
    controller.load_map(map_path)

    # Load line paths from JSON
    json_path = "database_json/path_drawn.json"
    try:
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        lines = [
            {
                'start_point': np.array([item["x"][0], item["y"][0]]),
                'end_point': np.array([item["x"][1], item["y"][1]])
            }
            for item in json_data
            if item.get("type") == "line" and len(item["x"]) >= 2 and len(item["y"]) >= 2
        ]
        if not lines:
            rospy.logerror("No valid 'line' objects with at least two points found in JSON file.")
            return
        rospy.loginfo(f"Loaded {len(lines)} line(s) from {json_path}")
    except Exception as e:
        rospy.logerror(f"Failed to load JSON file {json_path}: {e}")
        return

    # Subscribe to pose updates
    rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, controller.pose_callback, queue_size=1)

    # Wait for initial pose
    rospy.loginfo("Waiting for initial pose from /amcl_pose...")
    while not rospy.is_shutdown() and controller.current_pose is None:
        rospy.sleep(0.1)

    # Process each line sequentially
    for line_idx, line in enumerate(lines):
        rospy.loginfo(f"Processing line {line_idx + 1}/{len(lines)}")
        
        # Set line path
        start_point = line['start_point']
        end_point = line['end_point']
        if not controller.set_line_path(start_point, end_point):
            rospy.logwarn(f"Failed to set line path for line {line_idx + 1}. Skipping.")
            continue

        # Send initial goal to move_base
        move_base_client.wait_for_server(rospy.Duration(5.0))
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = start_point[0]
        goal.target_pose.pose.position.y = start_point[1]
        goal.target_pose.pose.orientation.w = 1.0  # Neutral orientation
        move_base_client.send_goal(goal)
        rospy.loginfo(f"Sent initial goal for line {line_idx + 1} to move_base: ({start_point[0]:.2f}, {start_point[1]:.2f})")

        wait_result = move_base_client.wait_for_result(rospy.Duration(60.0))
        if not wait_result:
            rospy.logwarn(f"Timeout waiting for initial goal of line {line_idx + 1}.")
            continue
        if move_base_client.get_state() != actionlib.GoalStatus.SUCCEEDED:
            rospy.logwarn(f"Failed to reach initial goal of line {line_idx + 1}.")
            continue
        rospy.loginfo(f"Reached initial goal for line {line_idx + 1}!")

        # Start tracking loop for the current line
        controller.start_time = rospy.Time.now().to_sec()
        controller.reached_goal = False  # Reset reached_goal for the new line
        rate = rospy.Rate(1.0 / dt)
        while not rospy.is_shutdown() and not controller.reached_goal:
            if controller.current_pose is None:
                rospy.logwarn_throttle(1.0, "No pose data available. Skipping control iteration.")
                rate.sleep()
                continue

            x, y, theta = controller.x, controller.y, controller.theta
            v, omega = controller.mpc_control(x, y, theta)
            
            twist_msg = Twist()
            twist_msg.linear.x = v
            twist_msg.angular.z = omega
            cmd_vel_pub.publish(twist_msg)

            rate.sleep()

        # Send zero velocity command after completing the line
        cmd_vel_pub.publish(Twist())
        rospy.loginfo(f"Completed line {line_idx + 1}. Sent zero velocity command.")

    # Final cleanup
    cmd_vel_pub.publish(Twist())
    rospy.loginfo("All lines completed. Sent final zero velocity command.")

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        rospy.loginfo("ROS node interrupted.")
    except Exception as e:
        rospy.logerror(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if not rospy.is_shutdown():
            final_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
            rospy.sleep(0.5)
            final_pub.publish(Twist())
            rospy.sleep(0.2)
            rospy.loginfo("Final zero velocity command sent.")
            rospy.signal_shutdown("Application exit")
        rospy.loginfo("Exiting application.")