import rospy
from geometry_msgs.msg import Pose, Twist, PoseWithCovarianceStamped, PoseStamped
import numpy as np
import json
import actionlib
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import tf.transformations
from scipy.signal import butter, filtfilt
from sensor_msgs.msg import LaserScan  # Added for LiDAR data
from threading import Lock  # Added for thread safety

# --- Helper functions for Catmull-Rom to Bezier conversion ---
def get_catmull_rom_intermediate_point(points_list, index):
    """
    Helper to get points for Catmull-Rom, duplicating ends.
    points_list is a list of np.array([x,y]).
    """
    if not points_list:
        rospy.logwarn_throttle(5.0, "get_catmull_rom_intermediate_point called with empty points_list.")
        return np.array([0.0, 0.0])
    if index < 0:
        return points_list[0]
    if index >= len(points_list):
        return points_list[-1]
    return points_list[index]

def cubic_bezier_point(p0, p1, p2, p3, t):
    """Calculates a point on a cubic Bezier curve (p0,p1,p2,p3 are start, cp1, cp2, end)."""
    t = float(t)
    return (1-t)**3 * p0 + 3*(1-t)**2 * t * p1 + 3*(1-t) * t**2 * p2 + t**3 * p3

def cubic_bezier_derivative(p0, p1, p2, p3, t):
    """Calculates the derivative (dp/dt) of a cubic Bezier curve."""
    t = float(t)
    return 3*(1-t)**2 * (p1-p0) + 6*(1-t)*t * (p2-p1) + 3*t**2 * (p3-p2)
# --- End Helper functions ---

class MPCController:
    def __init__(self, dt, v_max, v_min, omega_max, omega_min, lookahead_distance=0.1, filter_order=4, cutoff_frequency=4.0):
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
        self.waypoints = []
        self.bezier_segments = []
        self.segment_arclengths_approx = []
        self.cumulative_arclengths_approx = []
        self.total_arclength_approx = 0.0
        self.num_arclength_samples_per_segment = 30
        self.distance_threshold = 0.2
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

    def lowpass_filter(self, data):
        if len(self.b) == 1 and self.b[0] == 1 and len(self.a) == 1 and self.a[0] == 1:
            return data
        padlen = 3 * max(len(self.a), len(self.b), self.filter_order)
        if len(data) <= padlen:
            return data
        try:
            y = filtfilt(self.b, self.a, data, padlen=padlen)
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

    def calculate_path(self):
        self.bezier_segments = []
        self.segment_arclengths_approx = []
        self.cumulative_arclengths_approx = []
        self.total_arclength_approx = 0.0

        if len(self.waypoints) < 2:
            rospy.logwarn("Need at least two waypoints to create a path.")
            return False

        unique_wps = []
        if self.waypoints:
            unique_wps.append(self.waypoints[0])
            for i in range(1, len(self.waypoints)):
                if np.linalg.norm(self.waypoints[i] - self.waypoints[i-1]) > 1e-6:
                    unique_wps.append(self.waypoints[i])
        
        if len(unique_wps) < 2:
            rospy.logwarn("After filtering duplicates, less than two unique waypoints remain. Cannot create path.")
            self.waypoints = []
            return False
        
        effective_waypoints = unique_wps

        for i in range(len(effective_waypoints) - 1):
            p0_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i - 1)
            p1_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i)
            p2_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i + 1)
            p3_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i + 2)
            
            cp1 = p1_catmull + (p2_catmull - p0_catmull) / 6.0
            cp2 = p2_catmull - (p3_catmull - p1_catmull) / 6.0
            
            segment_points = [p1_catmull, cp1, cp2, p2_catmull]
            self.bezier_segments.append(segment_points)

            length = 0.0
            prev_p = cubic_bezier_point(*segment_points, 0.0)
            for k_sample in range(1, self.num_arclength_samples_per_segment + 1):
                t_sample = float(k_sample) / self.num_arclength_samples_per_segment
                curr_p = cubic_bezier_point(*segment_points, t_sample)
                length += np.linalg.norm(curr_p - prev_p)
                prev_p = curr_p
            self.segment_arclengths_approx.append(length)

        if self.segment_arclengths_approx:
            self.cumulative_arclengths_approx = np.concatenate(([0.0], np.cumsum(self.segment_arclengths_approx)))
            self.total_arclength_approx = self.cumulative_arclengths_approx[-1]
        else:
            self.cumulative_arclengths_approx = [0.0]
            self.total_arclength_approx = 0.0

        if self.total_arclength_approx < 1e-6 and len(effective_waypoints) >= 2:
            rospy.logwarn("Total path arclength is very small. Waypoints might be too close or identical.")
        
        rospy.loginfo(f"Successfully created Catmull-Rom path with {len(self.bezier_segments)} Bezier segments. "
                      f"Total approx arclength: {self.total_arclength_approx:.2f}m from {len(effective_waypoints)} unique waypoints.")
        return True

    def _get_segment_and_t(self, global_s):
        if not self.bezier_segments or self.total_arclength_approx < 1e-9:
            return 0, 0.0

        target_s = np.clip(global_s, 0, self.total_arclength_approx)
        
        segment_idx = np.searchsorted(self.cumulative_arclengths_approx, target_s, side='right') - 1
        segment_idx = np.clip(segment_idx, 0, len(self.bezier_segments) - 1)

        s_at_segment_start = self.cumulative_arclengths_approx[segment_idx]
        s_into_segment = target_s - s_at_segment_start
        current_segment_length = self.segment_arclengths_approx[segment_idx]

        if current_segment_length < 1e-6:
            t_local = 0.0
        else:
            t_local = s_into_segment / current_segment_length
        
        t_local = np.clip(t_local, 0.0, 1.0)
        return segment_idx, t_local

    def get_point_on_path(self, global_s):
        if not self.bezier_segments: return np.array([self.x, self.y])
        segment_idx, t_local = self._get_segment_and_t(global_s)
        segment_points = self.bezier_segments[segment_idx]
        return cubic_bezier_point(*segment_points, t_local)

    def get_derivative_on_path(self, global_s):
        if not self.bezier_segments: return np.array([1.0, 0.0])
        segment_idx, t_local = self._get_segment_and_t(global_s)
        segment_points = self.bezier_segments[segment_idx]
        deriv_wrt_t_local = cubic_bezier_derivative(*segment_points, t_local)
        ds_dt_local = np.linalg.norm(deriv_wrt_t_local)
        
        if ds_dt_local < 1e-6:
            if t_local < 0.5:
                deriv_wrt_t_local_eps = cubic_bezier_derivative(*segment_points, min(1.0, t_local + 0.01))
                ds_dt_local_eps = np.linalg.norm(deriv_wrt_t_local_eps)
                if ds_dt_local_eps > 1e-6: return deriv_wrt_t_local_eps / ds_dt_local_eps
            else:
                deriv_wrt_t_local_eps = cubic_bezier_derivative(*segment_points, max(0.0, t_local - 0.01))
                ds_dt_local_eps = np.linalg.norm(deriv_wrt_t_local_eps)
                if ds_dt_local_eps > 1e-6: return deriv_wrt_t_local_eps / ds_dt_local_eps
            rospy.logwarn_throttle(1.0, f"ds/dt_local is near zero at s={global_s:.2f}, t={t_local:.2f} on segment {segment_idx}. Using default derivative.")
            if segment_idx + 1 < len(self.bezier_segments):
                next_pt_dir = self.bezier_segments[segment_idx+1][0] - cubic_bezier_point(*segment_points, t_local)
                norm_next_pt_dir = np.linalg.norm(next_pt_dir)
                if norm_next_pt_dir > 1e-6: return next_pt_dir / norm_next_pt_dir
            return np.array([1.0, 0.0])
            
        return deriv_wrt_t_local / ds_dt_local

    def find_closest_point_on_path(self, x, y):
        if not self.bezier_segments or self.total_arclength_approx < 1e-9:
            return 0.0

        robot_pos = np.array([x,y])
        min_dist_sq_overall = float('inf')
        closest_s_overall = 0.0
        num_search_samples_per_segment = 50

        for i, segment_def_points in enumerate(self.bezier_segments):
            current_min_dist_sq_segment = float('inf')
            best_t_on_segment = 0.0

            for k_sample in range(num_search_samples_per_segment + 1):
                t = float(k_sample) / num_search_samples_per_segment
                pt_on_curve = cubic_bezier_point(*segment_def_points, t)
                dist_sq = np.sum((pt_on_curve - robot_pos)**2)
                
                if dist_sq < current_min_dist_sq_segment:
                    current_min_dist_sq_segment = dist_sq
                    best_t_on_segment = t
            
            if current_min_dist_sq_segment < min_dist_sq_overall:
                min_dist_sq_overall = current_min_dist_sq_segment
                s_on_segment = best_t_on_segment * self.segment_arclengths_approx[i]
                closest_s_overall = self.cumulative_arclengths_approx[i] + s_on_segment
        
        return closest_s_overall

    def mpc_control(self, x, y, theta):
        if not self.bezier_segments or self.total_arclength_approx < 1e-9:
            rospy.logwarn_throttle(1.0, "Path is not defined or too short. Cannot perform MPC control.")
            return 0.0, 0.0

        closest_s = self.find_closest_point_on_path(x, y)
        lookahead_s = closest_s + self.lookahead_distance
        lookahead_s = np.clip(lookahead_s, 0, self.total_arclength_approx)
        lookahead_pt = self.get_point_on_path(lookahead_s)
        lookahead_x, lookahead_y = lookahead_pt[0], lookahead_pt[1]

        final_goal_pt = self.get_point_on_path(self.total_arclength_approx)
        final_goal_x, final_goal_y = final_goal_pt[0], final_goal_pt[1]
        distance_to_final_goal = np.sqrt((x - final_goal_x)**2 + (y - final_goal_y)**2)
        
        is_near_end_point = distance_to_final_goal < self.distance_threshold
        is_near_end_of_s = abs(self.total_arclength_approx - closest_s) < self.distance_threshold * 1.5
        
        if is_near_end_point and is_near_end_of_s:
            rospy.loginfo("Reached the final goal!")
            self.reached_goal = True
            return 0.0, 0.0

        path_derivative_at_lookahead = self.get_derivative_on_path(lookahead_s)
        dx_ds, dy_ds = path_derivative_at_lookahead[0], path_derivative_at_lookahead[1]
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
    rospy.init_node('spline_tracking_node_catmull_rom')
    
    dt = 0.05
    v_max = 0.3
    v_min = -0.3
    omega_max = 0.5
    omega_min = -0.5
    lookahead_distance = 0.2
    filter_order = 3
    cutoff_freq = 1.5

    controller = MPCController(dt, v_max, v_min, omega_max, omega_min,
                              lookahead_distance, filter_order, cutoff_freq)
    
    cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    move_base_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    
    # Load waypoints from JSON
    json_path = "database_json/path_drawn.json"
    try:
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        splines = [item for item in json_data if item.get("type") == "spline3"]
        if not splines:
            rospy.logerror("No 'spline3' objects found in JSON file.")
            return
        rospy.loginfo(f"Loaded {len(splines)} spline(s) from {json_path}")
    except Exception as e:
        rospy.logerror(f"Failed to load JSON file {json_path}: {e}")
        return

    # Subscribe to pose updates
    rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, controller.pose_callback, queue_size=1)

    # Wait for initial pose
    rospy.loginfo("Waiting for initial pose from /amcl_pose...")
    while not rospy.is_shutdown() and controller.current_pose is None:
        rospy.sleep(0.1)

    # Process each spline sequentially
    for spline_idx, spline in enumerate(splines):
        rospy.loginfo(f"Processing spline {spline_idx + 1}/{len(splines)}")
        
        # Set waypoints for the current spline
        controller.waypoints = [np.array(point) for point in spline["points"]]
        initial_goal = np.array(spline["points"][0]) if spline["points"] else np.array([0.0, 0.0])
        
        if len(controller.waypoints) < 2:
            rospy.logwarn(f"Spline {spline_idx + 1} has fewer than two waypoints. Skipping.")
            continue

        # Send initial goal to move_base
        move_base_client.wait_for_server(rospy.Duration(5.0))
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = initial_goal[0]
        goal.target_pose.pose.position.y = initial_goal[1]
        goal.target_pose.pose.orientation.w = 1.0  # Neutral orientation
        move_base_client.send_goal(goal)
        rospy.loginfo(f"Sent initial goal for spline {spline_idx + 1} to move_base: ({initial_goal[0]:.2f}, {initial_goal[1]:.2f})")

        wait_result = move_base_client.wait_for_result(rospy.Duration(60.0))
        if not wait_result:
            rospy.logwarn(f"Timeout waiting for initial goal of spline {spline_idx + 1}.")
            continue
        if move_base_client.get_state() != actionlib.GoalStatus.SUCCEEDED:
            rospy.logwarn(f"Failed to reach initial goal of spline {spline_idx + 1}.")
            continue
        rospy.loginfo(f"Reached initial goal for spline {spline_idx + 1}!")

        # Calculate path for the current spline
        if not controller.calculate_path():
            rospy.logerror(f"Failed to create path from waypoints for spline {spline_idx + 1}.")
            continue

        # Start tracking loop for the current spline
        controller.start_time = rospy.Time.now().to_sec()
        controller.reached_goal = False  # Reset reached_goal for the new spline
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

        # Send zero velocity command after completing the spline
        cmd_vel_pub.publish(Twist())
        rospy.loginfo(f"Completed spline {spline_idx + 1}. Sent zero velocity command.")

    # Final cleanup
    cmd_vel_pub.publish(Twist())
    rospy.loginfo("All splines completed. Sent final zero velocity command.")

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        rospy.loginfo("ROS node interrupted.")
    except Exception as e:
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