

import rospy
from geometry_msgs.msg import Pose, Twist # PoseWithCovarianceStamped might be needed if pose_callback handles it
import numpy as np
import tf.transformations
# scipy.interpolate.splrep and splev are no longer needed for the primary path generation
from scipy.signal import butter, filtfilt

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
    """Calculates a point on a cubic Bezier curve."""
    t = float(t)
    return (1-t)**3 * p0 + 3*(1-t)**2 * t * p1 + 3*(1-t) * t**2 * p2 + t**3 * p3

def cubic_bezier_derivative(p0, p1, p2, p3, t):
    """Calculates the derivative (dp/dt) of a cubic Bezier curve."""
    t = float(t)
    return 3*(1-t)**2 * (p1-p0) + 6*(1-t)*t * (p2-p1) + 3*t**2 * (p3-p2)
# --- End Helper functions ---


class Spline5_MPCController: # Name implies quintic, but we're doing Catmull-Rom (like HTML)
    def __init__(self, dt, v_max, v_min, omega_max, omega_min, lookahead_distance=0.1, filter_order=4, cutoff_frequency=2.0):
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

        # Waypoints will be a list of np.array([x,y])
        self.waypoints = []  # CHANGED from waypoints_x, waypoints_y

        # Path representation based on Catmull-Rom to Bezier
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
        
        # Robust filter initialization
        if self.dt <= 0:
            rospy.logerr("dt must be positive for filter design. Disabling filter.")
            self.b, self.a = ([1], [1]) # Pass-through filter
        else:
            nyquist_freq = 0.5 / self.dt
            normalized_cutoff = self.cutoff_frequency / nyquist_freq
            if normalized_cutoff >= 1.0:
                rospy.logwarn(f"Cutoff frequency ({self.cutoff_frequency} Hz) is at or above Nyquist ({nyquist_freq} Hz). Clamping.")
                normalized_cutoff = 0.99
            elif normalized_cutoff <= 0:
                rospy.logwarn(f"Cutoff frequency ({self.cutoff_frequency} Hz) must be positive. Disabling filter.")
                self.b, self.a = ([1], [1])
            else:
                self.b, self.a = butter(self.filter_order, normalized_cutoff, btype='low', analog=False)

    def lowpass_filter(self, data):
        if len(self.b) == 1 and self.b[0] == 1 and len(self.a) == 1 and self.a[0] == 1:
            return data # Filter disabled
        padlen = 3 * max(len(self.a), len(self.b), self.filter_order)
        if len(data) <= padlen:
            return data
        try:
            y = filtfilt(self.b, self.a, data, padlen=padlen)
            return y
        except ValueError as e:
            rospy.logwarn(f"Error during filtering: {e}. Returning unfiltered. Data len: {len(data)}, padlen: {padlen}")
            return data
            
    def pose_callback(self, msg): # Assuming msg is Pose from /robot_pose or PoseWithCovarianceStamped.pose.pose
        # If msg is PoseWithCovarianceStamped, you need msg.pose.pose
        # For now, let's assume it's directly a Pose message as per the import
        # If it's from amcl_pose, it's PoseWithCovarianceStamped, so msg = msg.pose.pose
        
        # Check if the message is PoseWithCovarianceStamped and adjust
        if hasattr(msg, 'pose') and hasattr(msg.pose, 'pose'): # Heuristic for PoseWithCovarianceStamped
            actual_pose_msg = msg.pose.pose
        elif hasattr(msg, 'position') and hasattr(msg, 'orientation'): # Looks like a Pose message
            actual_pose_msg = msg
        else:
            rospy.logwarn_throttle(5.0, "Received message in pose_callback is not a recognized Pose type.")
            return

        quat = actual_pose_msg.orientation
        norm_sq = quat.x**2 + quat.y**2 + quat.z**2 + quat.w**2
        if norm_sq < 1e-9: # Check for zero quaternion
            rospy.logwarn_throttle(5.0, "Invalid (zero) quaternion received, skipping pose update.")
            return

        try:
            euler = tf.transformations.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
            _, _, yaw = euler # roll, pitch, yaw
        except Exception as e:
            rospy.logerr(f"Error converting quaternion to Euler: {e}")
            return

        self.x = actual_pose_msg.position.x
        self.y = actual_pose_msg.position.y
        self.theta = yaw
        self.current_pose = np.array([self.x, self.y, self.theta])
        self.trajectory_x.append(self.x)
        self.trajectory_y.append(self.y)

        if not self.waypoints: # If no waypoints exist, set the first one to current pose
            self.waypoints.append(np.array([self.x, self.y]))
        else:
            # Update the first waypoint to be the robot's current start position
            # This is often desired if the path starts from where the robot is.
            self.waypoints[0] = np.array([self.x, self.y])


    def calculate_path(self): # RENAMED from calculate_spline
        self.bezier_segments = []
        self.segment_arclengths_approx = []
        self.cumulative_arclengths_approx = []
        self.total_arclength_approx = 0.0

        if len(self.waypoints) < 2: # Catmull-Rom needs at least 2 points for one segment
            rospy.logwarn("Need at least two waypoints to create a Catmull-Rom path.")
            return False

        # Filter out consecutive duplicate waypoints
        unique_wps = []
        if self.waypoints:
            unique_wps.append(self.waypoints[0])
            for i in range(1, len(self.waypoints)):
                if np.linalg.norm(self.waypoints[i] - self.waypoints[i-1]) > 1e-6:
                    unique_wps.append(self.waypoints[i])
        
        if len(unique_wps) < 2:
            rospy.logwarn("After filtering, less than two unique waypoints remain. Cannot create path.")
            self.waypoints = [] # Or just return False and let caller handle waypoints
            return False
        
        effective_waypoints = unique_wps

        for i in range(len(effective_waypoints) - 1): # Create a Bezier segment for each pair of waypoints
            p0_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i - 1)
            p1_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i)     # Start of Bezier segment
            p2_catmull = get_catmull_rom_intermediate_point(effective_waypoints, i + 1) # End of Bezier segment
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
            self.total_arclength_approx = 0.0
            self.cumulative_arclengths_approx = [0.0]

        if self.total_arclength_approx < 1e-6 and len(effective_waypoints) >=2:
             rospy.logwarn_throttle(5.0, "Total path arclength is very small.")

        rospy.loginfo(f"Created Catmull-Rom path: {len(self.bezier_segments)} segments, ~{self.total_arclength_approx:.2f}m length from {len(effective_waypoints)} wps.")
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

        t_local = s_into_segment / current_segment_length if current_segment_length > 1e-6 else 0.0
        return segment_idx, np.clip(t_local, 0.0, 1.0)

    def get_point_on_path(self, global_s):
        if not self.bezier_segments: return np.array([self.x, self.y])
        segment_idx, t_local = self._get_segment_and_t(global_s)
        return cubic_bezier_point(*self.bezier_segments[segment_idx], t_local)

    def get_derivative_on_path(self, global_s):
        if not self.bezier_segments: return np.array([1.0, 0.0])
        segment_idx, t_local = self._get_segment_and_t(global_s)
        segment_points = self.bezier_segments[segment_idx]
        deriv_wrt_t = cubic_bezier_derivative(*segment_points, t_local)
        ds_dt = np.linalg.norm(deriv_wrt_t)
        if ds_dt < 1e-6:
            # Fallback for zero derivative (e.g. cusp or end of tiny segment)
            rospy.logwarn_throttle(1.0, f"ds/dt near zero at s={global_s:.2f}, t={t_local:.2f} on segment {segment_idx}.")
            if segment_idx + 1 < len(self.bezier_segments):
                next_pt_dir = self.bezier_segments[segment_idx+1][0] - cubic_bezier_point(*segment_points, t_local)
                norm_next_pt_dir = np.linalg.norm(next_pt_dir)
                if norm_next_pt_dir > 1e-6: return next_pt_dir / norm_next_pt_dir
            return np.array([1.0, 0.0]) # Default
        return deriv_wrt_t / ds_dt

    def find_closest_point_on_path(self, x, y): # RENAMED
        if not self.bezier_segments or self.total_arclength_approx < 1e-9:
            return 0.0

        robot_pos = np.array([x, y])
        min_dist_sq_overall = float('inf')
        closest_s_overall = 0.0
        num_search_samples_per_segment = 50 # Increase for more accuracy if needed

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
            rospy.logwarn_throttle(1.0, "Path not defined or too short for MPC.")
            return 0.0, 0.0

        closest_s = self.find_closest_point_on_path(x, y)
        lookahead_s = np.clip(closest_s + self.lookahead_distance, 0, self.total_arclength_approx)
        lookahead_pt = self.get_point_on_path(lookahead_s)
        lookahead_x, lookahead_y = lookahead_pt[0], lookahead_pt[1]

        final_goal_pt = self.get_point_on_path(self.total_arclength_approx)
        distance_to_final_goal = np.linalg.norm(np.array([x,y]) - final_goal_pt)

        is_near_end_point = distance_to_final_goal < self.distance_threshold
        is_near_end_of_s = abs(self.total_arclength_approx - closest_s) < self.distance_threshold * 1.5
        
        if is_near_end_point and is_near_end_of_s:
            rospy.loginfo_once("Reached the final goal!") # Log once to avoid spam
            self.reached_goal = True
            return 0.0, 0.0

        path_derivative = self.get_derivative_on_path(lookahead_s)
        angle_to_goal_tangent = np.arctan2(path_derivative[1], path_derivative[0])
        
        heading_error = angle_to_goal_tangent - theta
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))

        # Pure pursuit like error terms
        distance_to_lookahead = np.linalg.norm(lookahead_pt - np.array([x,y]))

        heading_threshold = 0.1  # rad
        linear_speed_kp = 1.8
        angular_speed_kp = 1.8
        
        v = 0.0
        omega = 0.0

        if abs(heading_error) > heading_threshold :
            # Prioritize turning if heading error is large
            v = self.v_max * 0.1 # Slow down to turn
            if distance_to_lookahead < self.lookahead_distance * 0.3 and abs(heading_error) > np.pi/3:
                v = 0.0 # Stop and turn if very close but pointing wrong way
            omega = angular_speed_kp * heading_error
        else:
            # Heading is somewhat aligned, drive towards lookahead point
            v = linear_speed_kp * distance_to_lookahead
            omega = angular_speed_kp * heading_error # Fine tune heading

        # Ramping (optional, can be added back if smooth start/stop is critical)
        # ...

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