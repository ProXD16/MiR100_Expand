import rospy
import numpy as np
import json
import actionlib
import tf.transformations
from geometry_msgs.msg import Pose, Twist, PoseWithCovarianceStamped
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from sensor_msgs.msg import LaserScan
from scipy.signal import butter, filtfilt, lfilter
from PIL import Image
from threading import Lock

# Helper functions for Catmull-Rom to Bezier conversion
def get_catmull_rom_intermediate_point(points_list, index):
    """
    Helper to get points for Catmull-Rom, duplicating ends.
    points_list is a list of np.array([x, y]).
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
    """Calculates a point on a cubic Bezier curve (p0, p1, p2, p3 are start, cp1, cp2, end)."""
    t = float(t)
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3

def cubic_bezier_derivative(p0, p1, p2, p3, t):
    """Calculates the derivative (dp/dt) of a cubic Bezier curve."""
    t = float(t)
    return 3 * (1 - t) ** 2 * (p1 - p0) + 6 * (1 - t) * t * (p2 - p1) + 3 * t ** 2 * (p3 - p2)

# MPC Controller Classes
class LineMPCController:
    def __init__(self, dt, v_max, v_min, omega_max, omega_min, lookahead_distance=0.5, filter_order=3, cutoff_frequency=2.0):
        """Initialize the Line MPC controller with given parameters."""
        # Control parameters
        self.dt = dt
        self.v_max = v_max
        self.v_min = v_min
        self.omega_max = omega_max
        self.omega_min = omega_min
        self.lookahead_distance = lookahead_distance
        self.distance_threshold = 0.5
        self.ramp_up_duration = 2.0
        self.ramp_down_distance = 0.5
        self.velocity_smoothing_alpha = 0.3

        # Pose and trajectory tracking
        self.current_pose = None
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.trajectory_x = []
        self.trajectory_y = []

        # Path planning
        self.start_point = None
        self.end_point = None
        self.total_length = 0.0

        # Control state
        self.reached_goal = False
        self.last_v = 0.0
        self.last_omega = 0.0
        self.start_time = None

        # Data logging
        self.velocity_data = []
        self.angular_velocity_data = []
        self.acceleration_data = []
        self.angular_acceleration_data = []
        self.time_data = []

        # Low-pass filter
        self.filter_order = filter_order
        self.cutoff_frequency = cutoff_frequency
        if self.dt <= 0:
            rospy.logerr("dt must be positive for filter design. Disabling filter.")
            self.b, self.a = ([1], [1])
        else:
            nyquist_freq = 0.5 / self.dt
            normalized_cutoff = self.cutoff_frequency / nyquist_freq
            if normalized_cutoff >= 1.0:
                rospy.logwarn(f"Cutoff frequency ({self.cutoff_frequency} Hz) >= Nyquist frequency ({nyquist_freq} Hz). Clamping.")
                normalized_cutoff = 0.99
            elif normalized_cutoff <= 0:
                rospy.logwarn(f"Cutoff frequency ({self.cutoff_frequency} Hz) must be positive. Disabling filter.")
                self.b, self.a = ([1], [1])
            else:
                self.b, self.a = butter(self.filter_order, normalized_cutoff, btype='low', analog=False)

        # Map-based navigation
        self.map_image = None
        self.map_width = 0
        self.map_height = 0

        # LiDAR-based collision avoidance
        self.min_distance = float('inf')
        self.lidar_lock = Lock()
        self.fov_angle = np.deg2rad(60)  # 60-degree field of view
        self.safe_distance = 0.5  # Minimum safe distance in meters
        self.lidar_sub = rospy.Subscriber('/f_scan', LaserScan, self.lidar_callback, queue_size=1)

    def lidar_callback(self, msg):
        """Process LiDAR data to find minimum distance within 60-degree FOV."""
        angle_min = msg.angle_min
        angle_increment = msg.angle_increment
        ranges = np.array(msg.ranges)

        # Replace invalid ranges with a large value
        ranges = np.where(np.isinf(ranges) | np.isnan(ranges), 1000.0, ranges)

        # Calculate indices for ±30 degrees FOV
        center_index = len(ranges) // 2
        half_fov = self.fov_angle / 2
        indices_per_radian = 1 / angle_increment
        half_fov_indices = int(half_fov * indices_per_radian)
        start_index = max(0, center_index - half_fov_indices)
        end_index = min(len(ranges), center_index + half_fov_indices + 1)

        # Extract and find minimum distance in FOV
        fov_ranges = ranges[start_index:end_index]
        min_distance = np.min(fov_ranges) if len(fov_ranges) > 0 else float('inf')

        # Thread-safe update
        with self.lidar_lock:
            self.min_distance = min_distance

    def load_map(self, map_path):
        """Load map image for navigation."""
        try:
            self.map_image = Image.open(map_path)
            self.map_width, self.map_height = self.map_image.size
            rospy.loginfo(f"Loaded map image: {map_path}, size: {self.map_width}x{self.map_height}")
        except Exception as e:
            rospy.logwarn(f"Failed to load map image {map_path}: {e}")
            self.map_image = None

    def check_map_bounds(self, x, y):
        """Check if robot position is within map bounds."""
        if self.map_image is None:
            return
        pixel_x = int(x / 0.05)
        pixel_y = int(self.map_height - y / 0.05)
        if 0 <= pixel_x < self.map_width and 0 <= pixel_y < self.map_height:
            rospy.logdebug(f"Robot position ({x:.2f}, {y:.2f}) within map bounds")
        else:
            rospy.logwarn(f"Robot position ({x:.2f}, {y:.2f}) outside map bounds")

    def lowpass_filter(self, data):
        """Apply low-pass filter to data."""
        if len(self.b) == 1 and self.b[0] == 1 and len(self.a) == 1 and self.a[0] == 1:
            return data
        padlen = 3 * max(len(self.a), len(self.b), self.filter_order)
        if len(data) <= padlen:
            return data
        try:
            return lfilter(self.b, self.a, data)
        except ValueError as e:
            rospy.logwarn(f"Error during filtering: {e}. Returning unfiltered data.")
            return data

    def smooth_velocity(self, new_v, new_omega):
        """Smooth velocity commands using exponential moving average."""
        smoothed_v = (1 - self.velocity_smoothing_alpha) * self.last_v + self.velocity_smoothing_alpha * new_v
        smoothed_omega = (1 - self.velocity_smoothing_alpha) * self.last_omega + self.velocity_smoothing_alpha * new_omega
        return smoothed_v, smoothed_omega

    def smooth_ramp_factor(self, factor):
        """Compute smooth ramp factor using sine function."""
        return np.sin(factor * np.pi / 2)

    def pose_callback(self, msg):
        """Update robot pose from AMCL pose message."""
        pose_msg = msg.pose.pose
        quat = pose_msg.orientation
        norm_sq = quat.x ** 2 + quat.y ** 2 + quat.z ** 2 + quat.w ** 2
        if norm_sq < 1e-9:
            rospy.logwarn_throttle(5.0, "Invalid (zero) quaternion received, skipping pose update.")
            return
        try:
            _, _, yaw = tf.transformations.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
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
        """Set linear path from start to end point."""
        self.start_point = np.array([start_point[0], start_point[1]])
        self.end_point = np.array([end_point[0], end_point[1]])
        self.total_length = np.linalg.norm(self.end_point - self.start_point)
        if self.total_length < 1e-6:
            rospy.logwarn("Start and end points are too close. Invalid line path.")
            return False
        rospy.loginfo(f"Set line path from {self.start_point} to {self.end_point}, length {self.total_length:.2f}m")
        return True

    def get_point_on_path(self, s):
        """Get point on the linear path at distance s."""
        if self.total_length < 1e-6:
            return np.array([self.x, self.y])
        s = np.clip(s, 0, self.total_length)
        t = s / self.total_length
        point = self.start_point + t * (self.end_point - self.start_point)
        return point

    def get_derivative_on_path(self, s):
        """Get derivative (direction) of the linear path."""
        if self.total_length < 1e-6:
            return np.array([1.0, 0.0])
        direction = (self.end_point - self.start_point) / self.total_length
        return direction

    def find_closest_point_on_path(self, x, y):
        """Find distance s of the closest point on the path to (x, y)."""
        if self.total_length < 1e-6:
            return 0.0
        robot_pos = np.array([x, y])
        vec_to_robot = robot_pos - self.start_point
        direction = (self.end_point - self.start_point) / self.total_length
        s = np.dot(vec_to_robot, direction)
        s = np.clip(s, 0, self.total_length)
        return s

    def mpc_control(self, x, y, theta):
        """Compute MPC control commands (linear and angular velocity)."""
        if self.total_length < 1e-9:
            rospy.logwarn_throttle(1.0, "Line path is not defined or too short. Cannot perform MPC control.")
            return 0.0, 0.0

        # Find lookahead point
        closest_s = self.find_closest_point_on_path(x, y)
        lookahead_s = closest_s + self.lookahead_distance
        lookahead_s = np.clip(lookahead_s, 0, self.total_length)
        lookahead_pt = self.get_point_on_path(lookahead_s)
        lookahead_x, lookahead_y = lookahead_pt[0], lookahead_pt[1]

        # Check if goal is reached
        final_goal_pt = self.get_point_on_path(self.total_length)
        final_goal_x, final_goal_y = final_goal_pt[0], final_goal_pt[1]
        distance_to_final_goal = np.sqrt((x - final_goal_x) ** 2 + (y - final_goal_y) ** 2)
        is_near_end_point = distance_to_final_goal < self.distance_threshold
        is_near_end_of_s = abs(self.total_length - closest_s) < self.distance_threshold * 1.5

        if is_near_end_point and is_near_end_of_s:
            rospy.loginfo("Reached the final goal!")
            self.reached_goal = True
            return 0.0, 0.0

        # Compute heading error
        path_derivative = self.get_derivative_on_path(lookahead_s)
        dx_ds, dy_ds = path_derivative[0], path_derivative[1]
        angle_to_goal = np.arctan2(dy_ds, dx_ds)
        heading_error = angle_to_goal - theta
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))

        # Compute distance error
        x_error_lookahead = lookahead_x - x
        y_error_lookahead = lookahead_y - y
        distance_error = np.sqrt(x_error_lookahead ** 2 + y_error_lookahead ** 2)

        # Control law
        heading_threshold = 0.1
        linear_speed_kp = 1.8
        angular_speed_kp = 1.8

        if abs(heading_error) > heading_threshold:
            v = self.v_max * 0.2
            if distance_error < self.lookahead_distance * 0.3 and abs(heading_error) > np.pi / 4:
                v = 0.0
            omega = angular_speed_kp * heading_error
        else:
            v = linear_speed_kp * distance_error
            omega = angular_speed_kp * heading_error

        # Smooth velocities
        v, omega = self.smooth_velocity(v, omega)

        # Apply ramp-up
        if self.start_time is not None:
            current_time = rospy.Time.now().to_sec()
            elapsed_time = current_time - self.start_time
            if elapsed_time < self.ramp_up_duration:
                ramp_factor = self.smooth_ramp_factor(elapsed_time / self.ramp_up_duration)
                v *= ramp_factor
                omega *= ramp_factor

        # Apply ramp-down near goal
        if distance_to_final_goal < self.ramp_down_distance:
            ramp_down_factor = self.smooth_ramp_factor(distance_to_final_goal / self.ramp_down_distance)
            v *= ramp_down_factor
            omega *= ramp_down_factor

        # Collision avoidance
        with self.lidar_lock:
            if self.min_distance < self.safe_distance:
                v = 0.0
                rospy.logwarn(f"Obstacle detected within {self.min_distance:.2f}m, stopping linear motion.")

        # Clip velocities
        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

        # Log data
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

class SplineMPCController:
    def __init__(self, dt, v_max, v_min, omega_max, omega_min, lookahead_distance=0.2, filter_order=3, cutoff_frequency=1.5):
        """Initialize the Spline MPC controller with given parameters."""
        # Control parameters
        self.dt = dt
        self.v_max = v_max
        self.v_min = v_min
        self.omega_max = omega_max
        self.omega_min = omega_min
        self.lookahead_distance = lookahead_distance
        self.distance_threshold = 0.2
        self.ramp_up_duration = 2.0
        self.ramp_down_distance = 0.5
        self.velocity_smoothing_alpha = 0.3

        # Pose and trajectory tracking
        self.current_pose = None
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.trajectory_x = []
        self.trajectory_y = []

        # Path planning
        self.waypoints = []
        self.bezier_segments = []
        self.segment_arclengths_approx = []
        self.cumulative_arclengths_approx = []
        self.total_arclength_approx = 0.0
        self.num_arclength_samples_per_segment = 30

        # Control state
        self.reached_goal = False
        self.last_v = 0.0
        self.last_omega = 0.0
        self.start_time = None

        # Data logging
        self.velocity_data = []
        self.angular_velocity_data = []
        self.acceleration_data = []
        self.angular_acceleration_data = []
        self.time_data = []

        # Low-pass filter
        self.filter_order = filter_order
        self.cutoff_frequency = cutoff_frequency
        if self.dt <= 0:
            rospy.logerr("dt must be positive for filter design. Disabling filter.")
            self.b, self.a = ([1], [1])
        else:
            nyquist_freq = 0.5 / self.dt
            normalized_cutoff = self.cutoff_frequency / nyquist_freq
            if normalized_cutoff >= 1.0:
                rospy.logwarn(f"Cutoff frequency ({self.cutoff_frequency} Hz) >= Nyquist frequency ({nyquist_freq} Hz). Clamping.")
                normalized_cutoff = 0.99
            elif normalized_cutoff <= 0:
                rospy.logwarn(f"Cutoff frequency ({self.cutoff_frequency} Hz) must be positive. Disabling filter.")
                self.b, self.a = ([1], [1])
            else:
                self.b, self.a = butter(self.filter_order, normalized_cutoff, btype='low', analog=False)

        # LiDAR-based collision avoidance
        self.min_distance = float('inf')
        self.lidar_lock = Lock()
        self.fov_angle = np.deg2rad(60)  # 60-degree field of view
        self.safe_distance = 0.5  # Minimum safe distance in meters
        self.lidar_sub = rospy.Subscriber('/f_scan', LaserScan, self.lidar_callback, queue_size=1)

    def lidar_callback(self, msg):
        """Process LiDAR data to find minimum distance within 60-degree FOV."""
        angle_min = msg.angle_min
        angle_increment = msg.angle_increment
        ranges = np.array(msg.ranges)

        # Replace invalid ranges with a large value
        ranges = np.where(np.isinf(ranges) | np.isnan(ranges), 1000.0, ranges)

        # Calculate indices for ±30 degrees FOV
        center_index = len(ranges) // 2
        half_fov = self.fov_angle / 2
        indices_per_radian = 1 / angle_increment
        half_fov_indices = int(half_fov * indices_per_radian)
        start_index = max(0, center_index - half_fov_indices)
        end_index = min(len(ranges), center_index + half_fov_indices + 1)

        # Extract and find minimum distance in FOV
        fov_ranges = ranges[start_index:end_index]
        min_distance = np.min(fov_ranges) if len(fov_ranges) > 0 else float('inf')

        # Thread-safe update
        with self.lidar_lock:
            self.min_distance = min_distance

    def lowpass_filter(self, data):
        """Apply low-pass filter to data."""
        if len(self.b) == 1 and self.b[0] == 1 and len(self.a) == 1 and self.a[0] == 1:
            return data
        padlen = 3 * max(len(self.a), len(self.b), self.filter_order)
        if len(data) <= padlen:
            return data
        try:
            return filtfilt(self.b, self.a, data, padlen=padlen)
        except ValueError as e:
            rospy.logwarn(f"Error during filtering: {e}. Data length: {len(data)}, padlen: {padlen}")
            return data

    def smooth_velocity(self, new_v, new_omega):
        """Smooth velocity commands using exponential moving average."""
        smoothed_v = (1 - self.velocity_smoothing_alpha) * self.last_v + self.velocity_smoothing_alpha * new_v
        smoothed_omega = (1 - self.velocity_smoothing_alpha) * self.last_omega + self.velocity_smoothing_alpha * new_omega
        return smoothed_v, smoothed_omega

    def smooth_ramp_factor(self, factor):
        """Compute smooth ramp factor using sine function."""
        return np.sin(factor * np.pi / 2)

    def pose_callback(self, msg):
        """Update robot pose from AMCL pose message."""
        pose_msg = msg.pose.pose
        quat = pose_msg.orientation
        norm_sq = quat.x ** 2 + quat.y ** 2 + quat.z ** 2 + quat.w ** 2
        if norm_sq < 1e-9:
            rospy.logwarn_throttle(5.0, "Invalid (zero) quaternion received, skipping pose update.")
            return
        try:
            _, _, yaw = tf.transformations.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
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
        """Calculate Catmull-Rom spline path as Bezier segments."""
        self.bezier_segments = []
        self.segment_arclengths_approx = []
        self.cumulative_arclengths_approx = []
        self.total_arclength_approx = 0.0

        if len(self.waypoints) < 2:
            rospy.logwarn("Need at least two waypoints to create a path.")
            return False

        # Filter duplicate waypoints
        unique_wps = [self.waypoints[0]]
        for i in range(1, len(self.waypoints)):
            if np.linalg.norm(self.waypoints[i] - self.waypoints[i-1]) > 1e-6:
                unique_wps.append(self.waypoints[i])

        if len(unique_wps) < 2:
            rospy.logwarn("Less than two unique waypoints after filtering. Cannot create path.")
            self.waypoints = []
            return False

        effective_waypoints = unique_wps

        # Create Bezier segments
        for i in range(len(effective_waypoints) - 1):
            p0_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i - 1)
            p1_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i)
            p2_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i + 1)
            p3_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i + 2)

            cp1 = p1_catmull + (p2_catmull - p0_catmull) / 6.0
            cp2 = p2_catmull - (p3_catmull - p1_catmull) / 6.0

            segment_points = [p1_catmull, cp1, cp2, p2_catmull]
            self.bezier_segments.append(segment_points)

            # Approximate segment arclength
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
            rospy.logwarn("Total path arclength is very small. Waypoints might be too close.")

        rospy.loginfo(f"Created Catmull-Rom path with {len(self.bezier_segments)} Bezier segments. "
                      f"Total arclength: {self.total_arclength_approx:.2f}m from {len(effective_waypoints)} waypoints.")
        return True

    def _get_segment_and_t(self, global_s):
        """Get Bezier segment index and local t for a given arc length."""
        if not self.bezier_segments or self.total_arclength_approx < 1e-9:
            return 0, 0.0

        target_s = np.clip(global_s, 0, self.total_arclength_approx)
        segment_idx = np.searchsorted(self.cumulative_arclengths_approx, target_s, side='right') - 1
        segment_idx = np.clip(segment_idx, 0, len(self.bezier_segments) - 1)

        s_at_segment_start = self.cumulative_arclengths_approx[segment_idx]
        s_into_segment = target_s - s_at_segment_start
        current_segment_length = self.segment_arclengths_approx[segment_idx]

        t_local = 0.0 if current_segment_length < 1e-6 else s_into_segment / current_segment_length
        t_local = np.clip(t_local, 0.0, 1.0)
        return segment_idx, t_local

    def get_point_on_path(self, global_s):
        """Get point on the path at arc length s."""
        if not self.bezier_segments:
            return np.array([self.x, self.y])
        segment_idx, t_local = self._get_segment_and_t(global_s)
        segment_points = self.bezier_segments[segment_idx]
        return cubic_bezier_point(*segment_points, t_local)

    def get_derivative_on_path(self, global_s):
        """Get derivative (tangent) of the path at arc length s."""
        if not self.bezier_segments:
            return np.array([1.0, 0.0])
        segment_idx, t_local = self._get_segment_and_t(global_s)
        segment_points = self.bezier_segments[segment_idx]
        deriv_wrt_t_local = cubic_bezier_derivative(*segment_points, t_local)
        ds_dt_local = np.linalg.norm(deriv_wrt_t_local)

        if ds_dt_local < 1e-6:
            if t_local < 0.5:
                deriv_wrt_t_local_eps = cubic_bezier_derivative(*segment_points, min(1.0, t_local + 0.01))
                ds_dt_local_eps = np.linalg.norm(deriv_wrt_t_local_eps)
                if ds_dt_local_eps > 1e-6:
                    return deriv_wrt_t_local_eps / ds_dt_local_eps
            else:
                deriv_wrt_t_local_eps = cubic_bezier_derivative(*segment_points, max(0.0, t_local - 0.01))
                ds_dt_local_eps = np.linalg.norm(deriv_wrt_t_local_eps)
                if ds_dt_local_eps > 1e-6:
                    return deriv_wrt_t_local_eps / ds_dt_local_eps
            rospy.logwarn_throttle(1.0, f"ds/dt_local near zero at s={global_s:.2f}, t={t_local:.2f}, segment {segment_idx}.")
            if segment_idx + 1 < len(self.bezier_segments):
                next_pt_dir = self.bezier_segments[segment_idx + 1][0] - cubic_bezier_point(*segment_points, t_local)
                norm_next_pt_dir = np.linalg.norm(next_pt_dir)
                if norm_next_pt_dir > 1e-6:
                    return next_pt_dir / norm_next_pt_dir
            return np.array([1.0, 0.0])

        return deriv_wrt_t_local / ds_dt_local

    def find_closest_point_on_path(self, x, y):
        """Find arc length s of the closest point on the path to (x, y)."""
        if not self.bezier_segments or self.total_arclength_approx < 1e-9:
            return 0.0

        robot_pos = np.array([x, y])
        min_dist_sq_overall = float('inf')
        closest_s_overall = 0.0
        num_search_samples_per_segment = 50

        for i, segment_def_points in enumerate(self.bezier_segments):
            current_min_dist_sq_segment = float('inf')
            best_t_on_segment = 0.0

            for k_sample in range(num_search_samples_per_segment + 1):
                t = float(k_sample) / num_search_samples_per_segment
                pt_on_curve = cubic_bezier_point(*segment_def_points, t)
                dist_sq = np.sum((pt_on_curve - robot_pos) ** 2)

                if dist_sq < current_min_dist_sq_segment:
                    current_min_dist_sq_segment = dist_sq
                    best_t_on_segment = t

            if current_min_dist_sq_segment < min_dist_sq_overall:
                min_dist_sq_overall = current_min_dist_sq_segment
                s_on_segment = best_t_on_segment * self.segment_arclengths_approx[i]
                closest_s_overall = self.cumulative_arclengths_approx[i] + s_on_segment

        return closest_s_overall

    def mpc_control(self, x, y, theta):
        """Compute MPC control commands (linear and angular velocity)."""
        if not self.bezier_segments or self.total_arclength_approx < 1e-9:
            rospy.logwarn_throttle(1.0, "Path is not defined or too short. Cannot perform MPC control.")
            return 0.0, 0.0

        # Find lookahead point
        closest_s = self.find_closest_point_on_path(x, y)
        lookahead_s = closest_s + self.lookahead_distance
        lookahead_s = np.clip(lookahead_s, 0, self.total_arclength_approx)
        lookahead_pt = self.get_point_on_path(lookahead_s)
        lookahead_x, lookahead_y = lookahead_pt[0], lookahead_pt[1]

        # Check if goal is reached
        final_goal_pt = self.get_point_on_path(self.total_arclength_approx)
        final_goal_x, final_goal_y = final_goal_pt[0], final_goal_pt[1]
        distance_to_final_goal = np.sqrt((x - final_goal_x) ** 2 + (y - final_goal_y) ** 2)
        is_near_end_point = distance_to_final_goal < self.distance_threshold
        is_near_end_of_s = abs(self.total_arclength_approx - closest_s) < self.distance_threshold * 1.5

        if is_near_end_point and is_near_end_of_s:
            rospy.loginfo("Reached the final goal!")
            self.reached_goal = True
            return 0.0, 0.0

        # Compute heading error
        path_derivative_at_lookahead = self.get_derivative_on_path(lookahead_s)
        dx_ds, dy_ds = path_derivative_at_lookahead[0], path_derivative_at_lookahead[1]
        angle_to_goal = np.arctan2(dy_ds, dx_ds)
        heading_error = angle_to_goal - theta
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))

        # Compute distance error
        x_error_lookahead = lookahead_x - x
        y_error_lookahead = lookahead_y - y
        distance_error = np.sqrt(x_error_lookahead ** 2 + y_error_lookahead ** 2)

        # Control law
        heading_threshold = 0.1
        linear_speed_kp = 1.8
        angular_speed_kp = 1.8

        if abs(heading_error) > heading_threshold:
            v = self.v_max * 0.2
            if distance_error < self.lookahead_distance * 0.3 and abs(heading_error) > np.pi / 4:
                v = 0.0
            omega = angular_speed_kp * heading_error
        else:
            v = linear_speed_kp * distance_error
            omega = angular_speed_kp * heading_error

        # Smooth velocities
        v, omega = self.smooth_velocity(v, omega)

        # Apply ramp-up
        if self.start_time is not None:
            current_time = rospy.Time.now().to_sec()
            elapsed_time = current_time - self.start_time
            if elapsed_time < self.ramp_up_duration:
                ramp_factor = self.smooth_ramp_factor(elapsed_time / self.ramp_up_duration)
                v *= ramp_factor
                omega *= ramp_factor

        # Apply ramp-down near goal
        if distance_to_final_goal < self.ramp_down_distance:
            ramp_down_factor = self.smooth_ramp_factor(distance_to_final_goal / self.ramp_down_distance)
            v *= ramp_down_factor
            omega *= ramp_down_factor

        # Collision avoidance
        with self.lidar_lock:
            if self.min_distance < self.safe_distance:
                v = 0.0
                rospy.logwarn(f"Obstacle detected within {self.min_distance:.2f}m, stopping linear motion.")

        # Clip velocities
        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

        # Log data
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

def track_path(controller, move_base_client, cmd_vel_pub, initial_goal, rate, path_type):
    """Track a path using the specified controller."""
    # Send initial goal to move_base
    goal = MoveBaseGoal()
    goal.target_pose.header.frame_id = "map"
    goal.target_pose.header.stamp = rospy.Time.now()
    goal.target_pose.pose.position.x = initial_goal[0]
    goal.target_pose.pose.position.y = initial_goal[1]
    goal.target_pose.pose.orientation.w = 1.0
    move_base_client.send_goal(goal)
    rospy.loginfo(f"Sent initial goal for {path_type} to move_base: ({initial_goal[0]:.2f}, {initial_goal[1]:.2f})")

    wait_result = move_base_client.wait_for_result(rospy.Duration(60.0))
    if not wait_result:
        rospy.logwarn(f"Timeout waiting for initial goal for {path_type}.")
        return False
    if move_base_client.get_state() != actionlib.GoalStatus.SUCCEEDED:
        rospy.logwarn(f"Failed to reach initial goal for {path_type}.")
        return False
    rospy.loginfo(f"Reached initial goal for {path_type}!")

    # Start tracking loop
    controller.start_time = rospy.Time.now().to_sec()
    while not rospy.is_shutdown() and not controller.reached_goal:
        if controller.current_pose is None:
            rospy.logwarn_throttle(1.0, f"No pose data available for {path_type}. Skipping control iteration.")
            rate.sleep()
            continue
        x, y, theta = controller.x, controller.y, controller.theta
        v, omega = controller.mpc_control(x, y, theta)
        twist_msg = Twist()
        twist_msg.linear.x = v
        twist_msg.angular.z = omega
        cmd_vel_pub.publish(twist_msg)
        rate.sleep()

    cmd_vel_pub.publish(Twist())
    rospy.loginfo(f"Tracking completed for {path_type}. Sent zero velocity command.")
    return True

def main():
    """Main function to process paths sequentially."""
    rospy.init_node('sequential_mpc_controller')

    # Parameters
    dt = 0.05
    v_max = 0.3
    v_min = -0.3
    omega_max = 0.5
    omega_min = -0.5
    line_lookahead_distance = 0.5
    spline_lookahead_distance = 0.1
    line_filter_order = 3
    line_cutoff_freq = 2.0
    spline_filter_order = 3
    spline_cutoff_freq = 1.5
    map_path = "static/map_image.png"
    json_path = "database_json/path_drawn.json"

    # Initialize publishers and clients
    cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    move_base_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    move_base_client.wait_for_server(rospy.Duration(5.0))

    # Load JSON data
    try:
        with open(json_path, 'r') as f:
            json_data = json.load(f)
    except Exception as e:
        rospy.logerror(f"Failed to load JSON file {json_path}: {e}")
        return

    # Subscribe to pose updates
    line_controller = LineMPCController(dt, v_max, v_min, omega_max, omega_min, line_lookahead_distance, line_filter_order, line_cutoff_freq)
    spline_controller = SplineMPCController(dt, v_max, v_min, omega_max, omega_min, spline_lookahead_distance, spline_filter_order, spline_cutoff_freq)
    line_controller.load_map(map_path)

    def pose_callback(msg):
        line_controller.pose_callback(msg)
        spline_controller.pose_callback(msg)

    rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, pose_callback, queue_size=1)

    # Wait for initial pose
    rospy.loginfo("Waiting for initial pose from /amcl_pose...")
    while not rospy.is_shutdown() and line_controller.current_pose is None:
        rospy.sleep(0.1)

    rate = rospy.Rate(1.0 / dt)

    # Process paths sequentially
    for item in json_data:
        path_type = item.get("type")
        if path_type == "line":
            if len(item["x"]) >= 2 and len(item["y"]) >= 2:
                start_point = np.array([item["x"][0], item["y"][0]])
                end_point = np.array([item["x"][1], item["y"][1]])
                if not line_controller.set_line_path(start_point, end_point):
                    rospy.logerror("Failed to set line path.")
                    continue
                line_controller.reached_goal = False
                line_controller.start_time = None
                line_controller.trajectory_x = []
                line_controller.trajectory_y = []
                line_controller.velocity_data = []
                line_controller.angular_velocity_data = []
                line_controller.acceleration_data = []
                line_controller.angular_acceleration_data = []
                line_controller.time_data = []
                if not track_path(line_controller, move_base_client, cmd_vel_pub, start_point, rate, "line"):
                    rospy.logwarn("Skipping to next path due to failure in line tracking.")
                    continue
        elif path_type in ["spline3", "spline5"]:
            spline_controller.waypoints = [np.array(point) for point in item["points"]]
            initial_goal = np.array(item["points"][0]) if item["points"] else np.array([0.0, 0.0])
            if len(spline_controller.waypoints) < 2:
                rospy.logerror(f"Need at least two waypoints for {path_type}. Skipping.")
                continue
            if not spline_controller.calculate_path():
                rospy.logerror(f"Failed to create {path_type} path. Skipping.")
                continue
            spline_controller.reached_goal = False
            spline_controller.start_time = None
            spline_controller.trajectory_x = []
            spline_controller.trajectory_y = []
            spline_controller.velocity_data = []
            spline_controller.angular_velocity_data = []
            spline_controller.acceleration_data = []
            spline_controller.angular_acceleration_data = []
            spline_controller.time_data = []
            if not track_path(spline_controller, move_base_client, cmd_vel_pub, initial_goal, rate, path_type):
                rospy.logwarn(f"Skipping to next path due to failure in {path_type} tracking.")
                continue

    # Final cleanup
    cmd_vel_pub.publish(Twist())
    rospy.sleep(0.5)
    rospy.loginfo("All paths processed. Final zero velocity command sent.")
    rospy.signal_shutdown("Application exit")

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