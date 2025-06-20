import rospy
from geometry_msgs.msg import Pose, Twist, PoseWithCovarianceStamped, PoseStamped
from nav_msgs.msg import Odometry
import numpy as np
import tkinter as tk
import tkinter.ttk as ttk
import threading
import tf.transformations
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.interpolate import CubicSpline
from scipy.signal import butter, filtfilt

# ==============================================================================
# PHẦN 1: CÁC LỚP BIỂU DIỄN PHÂN ĐOẠN ĐƯỜNG ĐI (PATH SEGMENTS)
# (Không thay đổi)
# ==============================================================================

class LineSegment:
    def __init__(self, start_point, end_point):
        self.start_point = np.array(start_point)
        self.end_point = np.array(end_point)
        self.vector = self.end_point - self.start_point
        self.length = np.linalg.norm(self.vector)
        self.unit_vector = self.vector / self.length if self.length > 1e-6 else np.array([0, 0])

    def get_point(self, s):
        s_clamped = np.clip(s, 0, self.length)
        return self.start_point + s_clamped * self.unit_vector

    def get_tangent(self, s):
        return self.unit_vector
    
    def get_curvature(self, s):
        return 0.0

class ArcSegment:
    def __init__(self, center, radius, start_angle, end_angle, clockwise=False):
        self.center = np.array(center)
        self.radius = radius
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.clockwise = clockwise
        
        if self.clockwise:
            if self.end_angle > self.start_angle: self.start_angle += 2 * np.pi
        else:
            if self.end_angle < self.start_angle: self.end_angle += 2 * np.pi
                
        self.angle_span = abs(self.end_angle - self.start_angle)
        self.length = self.radius * self.angle_span
        self.start_point = self.get_point(0)
        self.end_point = self.get_point(self.length)

    def get_point(self, s):
        s_clamped = np.clip(s, 0, self.length)
        current_angle_span = s_clamped / self.radius
        angle = self.start_angle - current_angle_span if self.clockwise else self.start_angle + current_angle_span
        return self.center + self.radius * np.array([np.cos(angle), np.sin(angle)])

    def get_tangent(self, s):
        s_clamped = np.clip(s, 0, self.length)
        current_angle_span = s_clamped / self.radius
        angle = self.start_angle - current_angle_span if self.clockwise else self.start_angle + current_angle_span
        tangent_angle = angle - np.pi / 2 if self.clockwise else angle + np.pi / 2
        return np.array([np.cos(tangent_angle), np.sin(tangent_angle)])
        
    def get_curvature(self, s):
        return 1.0 / self.radius if not self.clockwise else -1.0 / self.radius

class SplineSegment:
    def __init__(self, waypoints, start_tangent=None, end_tangent=None):
        self.waypoints = np.array(waypoints)
        if len(self.waypoints) < 2:
            raise ValueError("SplineSegment requires at least 2 waypoints.")
            
        distances = np.sqrt(np.sum(np.diff(self.waypoints, axis=0)**2, axis=1))
        arc_length_params = np.concatenate(([0], np.cumsum(distances)))
        self.length = arc_length_params[-1]
        
        self.t_params = arc_length_params / self.length if self.length > 1e-6 else np.linspace(0, 1, len(self.waypoints))
        
        bc_x_start, bc_y_start = 'natural', 'natural'
        bc_x_end, bc_y_end = 'natural', 'natural'

        if start_tangent is not None:
            norm_start_tangent = start_tangent / np.linalg.norm(start_tangent)
            dx_start = norm_start_tangent[0] * self.length
            dy_start = norm_start_tangent[1] * self.length
            bc_x_start = (1, dx_start)
            bc_y_start = (1, dy_start)

        if end_tangent is not None:
            norm_end_tangent = end_tangent / np.linalg.norm(end_tangent)
            dx_end = norm_end_tangent[0] * self.length
            dy_end = norm_end_tangent[1] * self.length
            bc_x_end = (1, dx_end)
            bc_y_end = (1, dy_end)

        self.spline_x = CubicSpline(self.t_params, self.waypoints[:, 0], bc_type=(bc_x_start, bc_x_end))
        self.spline_y = CubicSpline(self.t_params, self.waypoints[:, 1], bc_type=(bc_y_start, bc_y_end))
        
        self.spline_dx = self.spline_x.derivative()
        self.spline_dy = self.spline_y.derivative()
        self.spline_ddx = self.spline_dx.derivative()
        self.spline_ddy = self.spline_dy.derivative()
        
        num_samples = max(200, int(self.length * 20))
        fine_t = np.linspace(0, 1, num_samples)
        fine_points = np.vstack([self.spline_x(fine_t), self.spline_y(fine_t)]).T
        self.s_map = np.concatenate(([0], np.cumsum(np.sqrt(np.sum(np.diff(fine_points, axis=0)**2, axis=1)))))
        self.t_map = fine_t
        self.start_point = self.get_point(0)
        self.end_point = self.get_point(self.length)

    def _get_t_for_s(self, s):
        s_clamped = np.clip(s, 0, self.length)
        return np.interp(s_clamped, self.s_map, self.t_map)

    def get_point(self, s):
        t = self._get_t_for_s(s)
        return np.array([self.spline_x(t), self.spline_y(t)])

    def get_tangent(self, s):
        t = self._get_t_for_s(s)
        dx, dy = self.spline_dx(t), self.spline_dy(t)
        norm = np.hypot(dx, dy)
        return np.array([dx/norm, dy/norm]) if norm > 1e-6 else np.array([1, 0])
        
    def get_curvature(self, s):
        t = self._get_t_for_s(s)
        dx = self.spline_dx(t)
        dy = self.spline_dy(t)
        ddx = self.spline_ddx(t)
        ddy = self.spline_ddy(t) 
        
        numerator = dx * ddy - dy * ddx
        denominator = (dx**2 + dy**2)**1.5
        
        return numerator / denominator if denominator > 1e-9 else 0.0


# ==============================================================================
# PHẦN 2: LỚP QUẢN LÝ ĐƯỜNG ĐI PHỨC HỢP (PATH MANAGER)
# (Không thay đổi)
# ==============================================================================

class PathManager:
    def __init__(self, num_points_per_meter=20):
        self.segments = []
        self.total_length = 0.0
        self.cumulative_lengths = [0.0]
        self.discretized_path = None
        self.num_points_per_meter = num_points_per_meter

    def add_segment(self, segment):
        self.segments.append(segment)
        self.total_length += segment.length
        self.cumulative_lengths.append(self.total_length)
        self._discretize_path()

    def clear(self):
        self.segments.clear()
        self.total_length = 0.0
        self.cumulative_lengths = [0.0]
        self.discretized_path = None

    def _discretize_path(self):
        if not self.segments:
            self.discretized_path = np.empty((0, 2))
            return
        
        path_points = []
        for segment in self.segments:
            num_points = max(2, int(segment.length * self.num_points_per_meter))
            s_values = np.linspace(0, segment.length, num_points)
            for s in s_values:
                path_points.append(segment.get_point(s))
        
        self.discretized_path = np.array(path_points)

    def get_discretized_path_points(self):
        if self.discretized_path is None:
            self._discretize_path()
        return self.discretized_path

    def get_point_at_global_s(self, global_s):
        global_s = np.clip(global_s, 0, self.total_length)
        segment_idx = np.searchsorted(self.cumulative_lengths, global_s, side='right') - 1
        segment_idx = max(0, min(segment_idx, len(self.segments) - 1))
        local_s = global_s - self.cumulative_lengths[segment_idx]
        return self.segments[segment_idx].get_point(local_s)

    def get_tangent_at_global_s(self, global_s):
        global_s = np.clip(global_s, 0, self.total_length)
        segment_idx = np.searchsorted(self.cumulative_lengths, global_s, side='right') - 1
        segment_idx = max(0, min(segment_idx, len(self.segments) - 1))
        local_s = global_s - self.cumulative_lengths[segment_idx]
        return self.segments[segment_idx].get_tangent(local_s)

    def get_curvature_at_global_s(self, global_s):
        global_s = np.clip(global_s, 0, self.total_length)
        segment_idx = np.searchsorted(self.cumulative_lengths, global_s, side='right') - 1
        segment_idx = max(0, min(segment_idx, len(self.segments) - 1))
        local_s = global_s - self.cumulative_lengths[segment_idx]
        return self.segments[segment_idx].get_curvature(local_s)

    def find_closest_point(self, robot_pos):
        if self.discretized_path is None or len(self.discretized_path) == 0:
            return 0.0, 0.0

        distances_sq = np.sum((self.discretized_path - robot_pos)**2, axis=1)
        closest_idx = np.argmin(distances_sq)
        
        if self.total_length > 0:
            global_s = (closest_idx / (len(self.discretized_path) - 1)) * self.total_length if len(self.discretized_path) > 1 else 0.0
        else:
            global_s = 0.0

        cross_track_error = np.sqrt(distances_sq[closest_idx])
        return global_s, cross_track_error

    def generate_example_path(self, start_pose):
        self.clear()
        
        p0 = start_pose[:2]
        theta0 = start_pose[2]
        line_seg1 = LineSegment(p0, p0 + 3.0 * np.array([np.cos(theta0), np.sin(theta0)]))
        self.add_segment(line_seg1)
        p1 = line_seg1.end_point
        
        radius = 1.2
        center = p1 + radius * np.array([np.cos(theta0 - np.pi/2), np.sin(theta0 - np.pi/2)])
        start_angle = np.arctan2(p1[1] - center[1], p1[0] - center[0])
        end_angle = start_angle - np.pi
        arc_seg = ArcSegment(center, radius, start_angle, end_angle, clockwise=True)
        self.add_segment(arc_seg)
        p2 = arc_seg.end_point

        tangent_at_p2 = arc_seg.get_tangent(arc_seg.length)
        line_seg2 = LineSegment(p2, p2 + 2.4 * tangent_at_p2)
        self.add_segment(line_seg2)
        p3 = line_seg2.end_point
        
        spline_start_point = p3
        tangent_at_p3 = line_seg2.get_tangent(line_seg2.length)
        forward_vec = tangent_at_p3
        left_vec = np.array([-forward_vec[1], forward_vec[0]])
        
        wp_rel_1 = np.array([1.2, 0.6])
        wp_rel_2 = np.array([0.0, 1.8])
        wp_rel_3 = np.array([0.6, 3.0])
        
        wp_abs_1 = spline_start_point + wp_rel_1[0] * forward_vec + wp_rel_1[1] * left_vec
        wp_abs_2 = spline_start_point + wp_rel_2[0] * forward_vec + wp_rel_2[1] * left_vec
        wp_abs_3 = spline_start_point + wp_rel_3[0] * forward_vec + wp_rel_3[1] * left_vec
        
        waypoints = [spline_start_point, wp_abs_1, wp_abs_2, wp_abs_3]
        
        self.add_segment(SplineSegment(waypoints, start_tangent=forward_vec))
        
        self._discretize_path()
        rospy.loginfo(f"Generated example path with {len(self.segments)} segments. Total length: {self.total_length:.2f}m")
        return True


# ==============================================================================
# PHẦN 3: BỘ ĐIỀU KHIỂN MPC 
# (Không thay đổi)
# ==============================================================================

class MPCController:
    def __init__(self, dt, v_max, v_min, omega_max, omega_min, lookahead_min, lookahead_max, curvature_threshold, factor_change_rate):
        self.dt = dt
        self.v_max, self.v_min = v_max, v_min
        self.omega_max, self.omega_min = omega_max, omega_min
        self.lookahead_min = lookahead_min
        self.lookahead_max = lookahead_max
        self.curvature_threshold = curvature_threshold
        self.lookahead_distance = lookahead_max
        self.factor_change_rate = factor_change_rate
        self.smoothed_curvature_factor = 0.0
        
        self.current_pose = None
        self.x, self.y, self.theta = 0.0, 0.0, 0.0
        self.path_manager = PathManager()
        self.path_milestones = []
        self.reached_goal = False
        self.distance_threshold = 0.1
        self.trajectory_x, self.trajectory_y = [], []
        self.velocity_data, self.angular_velocity_data = [], []
        self.acceleration_data, self.angular_acceleration_data = [], []
        self.time_data = []
        self.odom_time_data, self.odom_linear_v_data, self.odom_angular_v_data = [], [], []
        self.cross_track_errors, self.heading_errors = [], []
        self.start_time = None
        self.last_v, self.last_omega = 0.0, 0.0
        self.ramp_up_duration = 2.0
        self.ramp_down_distance = 1.5
        
        self.stepping_mode = False
        self.current_milestone_target_index = 0

    def pose_callback(self, msg):
        pose_msg = msg
        quat = pose_msg.orientation
        try:
            euler = tf.transformations.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
        except Exception as e:
            rospy.logwarn_throttle(5, f"Quaternion conversion failed: {e}")
            return
        self.x, self.y, self.theta = pose_msg.position.x, pose_msg.position.y, euler[2]
        self.current_pose = np.array([self.x, self.y, self.theta])
        if self.start_time is not None and not self.reached_goal:
            self.trajectory_x.append(self.x)
            self.trajectory_y.append(self.y)

    def odom_callback(self, msg):
        if self.start_time is None or self.reached_goal: return
        elapsed_time = rospy.Time.now().to_sec() - self.start_time
        self.odom_time_data.append(elapsed_time)
        self.odom_linear_v_data.append(msg.twist.twist.linear.x)
        self.odom_angular_v_data.append(msg.twist.twist.angular.z)
    
    def calculate_and_store_errors(self, cte, global_s):
        self.cross_track_errors.append(cte)
        path_tangent = self.path_manager.get_tangent_at_global_s(global_s)
        path_angle = np.arctan2(path_tangent[1], path_tangent[0])
        heading_error = path_angle - self.theta
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))
        self.heading_errors.append(abs(heading_error))

    def mpc_control(self, x, y, theta):
        if self.path_manager.total_length == 0:
            return 0.0, 0.0

        closest_s, cte = self.path_manager.find_closest_point(np.array([x, y]))
        self.calculate_and_store_errors(cte, closest_s)

        if self.stepping_mode:
            if self.current_milestone_target_index <= 0 or self.current_milestone_target_index >= len(self.path_manager.cumulative_lengths):
                rospy.logwarn("Invalid milestone target index.")
                self.reached_goal = True
                return 0.0, 0.0
            target_s = self.path_manager.cumulative_lengths[self.current_milestone_target_index]
            goal_message = f"Reached milestone {self.current_milestone_target_index}!"
        else:
            target_s = self.path_manager.total_length
            goal_message = "Reached the final goal!"

        remaining_distance = target_s - closest_s
        if remaining_distance < self.distance_threshold:
            rospy.loginfo(goal_message)
            self.reached_goal = True
            return 0.0, 0.0
        
        prediction_horizon = self.lookahead_max * float(1.0 / 1.2)
        num_samples = 80
        s_samples = np.linspace(closest_s, min(self.path_manager.total_length, closest_s + prediction_horizon), num_samples)
        
        try:
            curvatures_ahead = np.abs([self.path_manager.get_curvature_at_global_s(s) for s in s_samples])
            max_curvature_ahead = np.max(curvatures_ahead)
        except (ValueError, IndexError):
            max_curvature_ahead = abs(self.path_manager.get_curvature_at_global_s(closest_s))

        raw_factor = min(1.0, max_curvature_ahead / self.curvature_threshold)
        
        max_factor_change = self.factor_change_rate * self.dt
        factor_error = raw_factor - self.smoothed_curvature_factor
        change = np.clip(factor_error, -max_factor_change, max_factor_change)
        self.smoothed_curvature_factor += change
        
        self.lookahead_distance = self.lookahead_max - (self.lookahead_max - self.lookahead_min) * self.smoothed_curvature_factor
        
        lookahead_s = np.clip(closest_s + self.lookahead_distance, 0, self.path_manager.total_length)
        lookahead_point = self.path_manager.get_point_at_global_s(lookahead_s)
        angle_to_lookahead = np.arctan2(lookahead_point[1] - y, lookahead_point[0] - x)
        heading_error = np.arctan2(np.sin(angle_to_lookahead - theta), np.cos(angle_to_lookahead - theta))
        
        angular_speed_kp = 3.0
        v_base = self.v_max * max(0.1, 1 - 1.5 * abs(heading_error) / np.pi)
        
        v_curvature_scaling = max(0.2, 1.0 - 0.9 * self.smoothed_curvature_factor)
        
        v = v_base * v_curvature_scaling
        omega = angular_speed_kp * heading_error

        elapsed_time = rospy.Time.now().to_sec() - self.start_time
        if elapsed_time < self.ramp_up_duration:
            v *= np.sin((elapsed_time / self.ramp_up_duration) * np.pi / 2)
        if remaining_distance < self.ramp_down_distance:
            v *= np.sin((remaining_distance / self.ramp_down_distance) * np.pi / 2)

        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)
        
        time_log = elapsed_time
        dt_accel = time_log - (self.time_data[-1] if self.time_data else 0)
        linear_accel = (v - self.last_v) / dt_accel if dt_accel > 1e-6 else 0.0
        angular_accel = (omega - self.last_omega) / dt_accel if dt_accel > 1e-6 else 0.0
        self.acceleration_data.append(linear_accel); self.angular_acceleration_data.append(angular_accel)
        self.velocity_data.append(v); self.angular_velocity_data.append(omega)
        self.time_data.append(time_log)
        self.last_v, self.last_omega = v, omega
        
        return v, omega

# ==============================================================================
# PHẦN 4: GIAO DIỆN GUI
# [SỬA ĐỔI] Thay đổi logic khởi tạo lookahead trong chế độ stepping
# ==============================================================================

class GUI:
    def __init__(self, master, mpc_controller):
        self.master = master
        master.title("MiR100 Composite Path Tracking")
        self.mpc_controller = mpc_controller
        
        control_frame = tk.Frame(master)
        control_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        self.continuous_button = tk.Button(control_frame, text="Start Continuous", command=self.start_continuous_tracking, state=tk.DISABLED)
        self.continuous_button.pack(side=tk.LEFT, padx=5)
        
        self.step_button = tk.Button(control_frame, text="Step to Next Milestone", command=self.step_to_next_milestone, state=tk.DISABLED)
        self.step_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(control_frame, text="Stop Tracking", command=self.stop_control_loop, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = tk.Button(control_frame, text="Clear Path", command=self.clear_path)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.result_label = tk.Label(master, text="Waiting for initial robot pose...")
        self.result_label.grid(row=1, column=0, columnspan=3)
        
        metrics_frame = ttk.LabelFrame(master, text="Error Metrics", padding="10")
        metrics_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        self.max_cte_var = tk.StringVar(value="Max CTE: N/A"); self.avg_cte_var = tk.StringVar(value="Avg CTE: N/A")
        self.max_he_var = tk.StringVar(value="Max Heading Err: N/A"); self.avg_he_var = tk.StringVar(value="Avg Heading Err: N/A")
        tk.Label(metrics_frame, textvariable=self.max_cte_var).grid(row=0, column=0, sticky="w", padx=5)
        tk.Label(metrics_frame, textvariable=self.avg_cte_var).grid(row=1, column=0, sticky="w", padx=5)
        tk.Label(metrics_frame, textvariable=self.max_he_var).grid(row=0, column=1, sticky="w", padx=20)
        tk.Label(metrics_frame, textvariable=self.avg_he_var).grid(row=1, column=1, sticky="w", padx=20)
        
        self.tabControl = ttk.Notebook(master)
        self.trajectory_tab, self.velocity_tab, self.acceleration_tab = ttk.Frame(self.tabControl), ttk.Frame(self.tabControl), ttk.Frame(self.tabControl)
        self.tabControl.add(self.trajectory_tab, text='Trajectory'); self.tabControl.add(self.velocity_tab, text='Velocity'); self.tabControl.add(self.acceleration_tab, text='Acceleration')
        self.tabControl.grid(row=3, column=0, columnspan=3, sticky="nsew")
        master.grid_rowconfigure(3, weight=1); master.grid_columnconfigure(0, weight=1)

        # --- Khung "Go to Pose" giờ sẽ publish tới /move_base_simple/goal
        goto_frame = ttk.LabelFrame(master, text="Go to Pose (via /move_base_simple/goal)", padding="10")
        goto_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        tk.Label(goto_frame, text="Target (x, y, qz, qw):").pack(side=tk.LEFT, padx=5)
        self.goal_entry = tk.Entry(goto_frame, width=30)
        self.goal_entry.insert(0, "10, 10, 0, 1") # Tọa độ mặc định
        self.goal_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.goto_button = tk.Button(goto_frame, text="Send Simple Goal", command=self.go_to_pose, state=tk.DISABLED)
        self.goto_button.pack(side=tk.LEFT, padx=5)

        self.fig_trajectory, self.ax_trajectory = plt.subplots()
        self.ax_trajectory.set_xlabel("X (m)"); self.ax_trajectory.set_ylabel("Y (m)"); self.ax_trajectory.set_title("Robot Trajectory vs. Reference Path")
        self.ax_trajectory.axis('equal')
        self.line_actual, = self.ax_trajectory.plot([], [], 'r-', label="Quỹ đạo thực tế", zorder=3)
        self.line_ref, = self.ax_trajectory.plot([], [], 'c--', label="Quỹ đạo tham chiếu", zorder=2)
        self.robot_plot, = self.ax_trajectory.plot([], [], 'bo', label="Robot", markersize=8, zorder=5)
        self.lookahead_plot, = self.ax_trajectory.plot([], [], 'yo', label="Điểm Lookahead", markersize=5, zorder=4)
        self.milestone_plot, = self.ax_trajectory.plot([], [], 'go', label="Mốc (Segment Joints)", markersize=7, linestyle='None', zorder=4)
        self.ax_trajectory.legend()
        self.canvas_trajectory = FigureCanvasTkAgg(self.fig_trajectory, master=self.trajectory_tab); self.canvas_trajectory.draw(); self.canvas_trajectory.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.fig_velocity, self.ax_velocity = plt.subplots(); self.ax_velocity.set_xlabel("Time (s)"); self.ax_velocity.set_ylabel("Velocity (m/s, rad/s)"); self.ax_velocity.set_title("Robot Velocity (Commanded vs. Odom)")
        self.line_linear_velocity, = self.ax_velocity.plot([], [], label="Linear V (Cmd)"); self.line_angular_velocity, = self.ax_velocity.plot([], [], label="Angular V (Cmd)")
        self.line_odom_linear_velocity, = self.ax_velocity.plot([], [], '--', label="Linear V (Odom)"); self.line_odom_angular_velocity, = self.ax_velocity.plot([], [], '--', label="Angular V (Odom)")
        self.ax_velocity.legend(); self.canvas_velocity = FigureCanvasTkAgg(self.fig_velocity, master=self.velocity_tab); self.canvas_velocity.draw(); self.canvas_velocity.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.fig_acceleration, self.ax_acceleration = plt.subplots(); self.ax_acceleration.set_xlabel("Time (s)"); self.ax_acceleration.set_ylabel("Acceleration (m/s^2, rad/s^2)"); self.ax_acceleration.set_title("Robot Acceleration")
        self.line_linear_acceleration, = self.ax_acceleration.plot([], [], label="Linear Accel"); self.line_angular_acceleration, = self.ax_acceleration.plot([], [], label="Angular Accel")
        self.ax_acceleration.legend(); self.canvas_acceleration = FigureCanvasTkAgg(self.fig_acceleration, master=self.acceleration_tab); self.canvas_acceleration.draw(); self.canvas_acceleration.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.simple_goal_pub = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=1)
        self.control_loop_running = False
        self.master.after(500, self.check_initial_pose)

    def check_initial_pose(self):
        if self.mpc_controller.current_pose is not None:
            self.continuous_button.config(state=tk.NORMAL)
            self.step_button.config(state=tk.NORMAL)
            self.goto_button.config(state=tk.NORMAL)
            self.result_label.config(text="Robot pose received. Ready to generate path or send a goal.")
        else:
            self.master.after(500, self.check_initial_pose)

    def _prepare_path_visualization(self):
        """Hàm nội bộ để chuẩn bị và vẽ quỹ đạo tham chiếu."""
        self.mpc_controller.path_milestones.clear()
        if self.mpc_controller.path_manager.segments:
            self.mpc_controller.path_milestones.append(self.mpc_controller.path_manager.segments[0].start_point)
            for segment in self.mpc_controller.path_manager.segments:
                self.mpc_controller.path_milestones.append(segment.end_point)
        
        if self.mpc_controller.path_milestones:
            milestone_points = np.array(self.mpc_controller.path_milestones)
            self.milestone_plot.set_data(milestone_points[:, 0], milestone_points[:, 1])
        else:
            self.milestone_plot.set_data([], [])

        path_points = self.mpc_controller.path_manager.get_discretized_path_points()
        if path_points.size > 0:
            self.line_ref.set_data(path_points[:, 0], path_points[:, 1])
            self.ax_trajectory.relim(); self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()

    def _start_tracking(self, stepping_mode=False):
        """Hàm nội bộ để bắt đầu vòng lặp điều khiển, không tạo lại quỹ đạo."""
        if self.mpc_controller.path_manager.total_length == 0:
            self.result_label.config(text="No path to track. Please generate a path first.")
            return

        self._prepare_path_visualization()

        self.mpc_controller.stepping_mode = stepping_mode

        all_data = [
            self.mpc_controller.trajectory_x, self.mpc_controller.trajectory_y,
            self.mpc_controller.velocity_data, self.mpc_controller.angular_velocity_data,
            self.mpc_controller.acceleration_data, self.mpc_controller.angular_acceleration_data,
            self.mpc_controller.time_data, self.mpc_controller.odom_time_data,
            self.mpc_controller.odom_linear_v_data, self.mpc_controller.odom_angular_v_data,
            self.mpc_controller.cross_track_errors, self.mpc_controller.heading_errors
        ]
        for lst in all_data: lst.clear()
        
        self.mpc_controller.last_v = 0.0; self.mpc_controller.last_omega = 0.0
        self.mpc_controller.reached_goal = False
        self.mpc_controller.start_time = rospy.Time.now().to_sec()

        # --- [SỬA ĐỔI] Thay đổi logic reset lookahead cho chế độ stepping ---
        # Khi bắt đầu một chặng mới ở chế độ stepping, ta muốn robot có tầm nhìn ngắn (lookahead_min)
        # để nó tập trung vào việc định hướng đúng theo đoạn đường ngay phía trước.
        # Đặt smoothed_curvature_factor = 1.0 sẽ buộc lookahead_distance = lookahead_min.
        # Đối với chế độ chạy liên tục, ta vẫn bắt đầu với tầm nhìn xa (factor = 0.0).
        if stepping_mode:
            self.mpc_controller.smoothed_curvature_factor = 1.0
            rospy.loginfo("Stepping mode activated: Initializing with minimum lookahead distance.")
        else:
            self.mpc_controller.smoothed_curvature_factor = 0.0
        # --- [KẾT THÚC SỬA ĐỔI] ---

        self.continuous_button.config(state=tk.DISABLED)
        self.step_button.config(state=tk.DISABLED)
        self.goto_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.DISABLED)
        
        self.result_label.config(text="Tracking started...")
        self.control_loop_running = True
        self.update_plot()
        
    def start_continuous_tracking(self):
        """Tạo quỹ đạo mẫu và bắt đầu chạy liên tục."""
        if self.mpc_controller.current_pose is None:
            self.result_label.config(text="Cannot start. Waiting for initial pose.")
            return

        if not self.mpc_controller.path_manager.generate_example_path(self.mpc_controller.current_pose):
            self.result_label.config(text="Error generating path.")
            return
        
        self.mpc_controller.current_milestone_target_index = 0
        self._start_tracking(stepping_mode=False)

    def step_to_next_milestone(self):
        """Di chuyển đến mốc tiếp theo trên quỹ đạo."""
        if self.mpc_controller.current_pose is None:
            self.result_label.config(text="Cannot start. Waiting for initial pose.")
            return

        if self.mpc_controller.path_manager.total_length == 0:
            if not self.mpc_controller.path_manager.generate_example_path(self.mpc_controller.current_pose):
                self.result_label.config(text="Error generating path.")
                return
            self.mpc_controller.current_milestone_target_index = 0
        
        self.mpc_controller.current_milestone_target_index += 1

        if self.mpc_controller.current_milestone_target_index >= len(self.mpc_controller.path_manager.cumulative_lengths):
            self.result_label.config(text="End of path reached. Resetting.")
            self.mpc_controller.current_milestone_target_index = 0
            return

        target_dist = self.mpc_controller.path_manager.cumulative_lengths[self.mpc_controller.current_milestone_target_index]
        self.result_label.config(text=f"Stepping to milestone {self.mpc_controller.current_milestone_target_index} (at {target_dist:.2f}m)...")
        self._start_tracking(stepping_mode=True)
    
    def go_to_pose(self):
        """
        Gửi một mục tiêu đến move_base thông qua topic /move_base_simple/goal
        thay vì dùng bộ điều khiển MPC nội bộ.
        """
        if self.mpc_controller.current_pose is None:
            self.result_label.config(text="Cannot send goal. Waiting for initial pose.")
            return
        
        try:
            # Phân tích chuỗi đầu vào: x, y, qz, qw
            parts = [float(p.strip()) for p in self.goal_entry.get().split(',')]
            if len(parts) != 4:
                raise ValueError("Input must be 4 numbers: x, y, qz, qw")
            target_x, target_y, target_qz, target_qw = parts
        except ValueError as e:
            self.result_label.config(text=f"Invalid pose format: {e}")
            return
        
        # Dừng vòng lặp điều khiển MPC hiện tại nếu nó đang chạy
        if self.control_loop_running:
            self.stop_control_loop()
            rospy.loginfo("MPC control loop stopped to send a new simple goal.")
        
        # Tạo thông điệp PoseStamped
        goal_msg = PoseStamped()
        goal_msg.header.stamp = rospy.Time.now()
        goal_msg.header.frame_id = "map"  # Giả định khung tọa độ là 'map', đây là giá trị phổ biến

        goal_msg.pose.position.x = target_x
        goal_msg.pose.position.y = target_y
        goal_msg.pose.position.z = 0.0 # 2D navigation

        # Trong 2D navigation, thường chỉ cần yaw (quay quanh trục z)
        # nên x, y của quaternion là 0
        goal_msg.pose.orientation.x = 0.0
        goal_msg.pose.orientation.y = 0.0
        goal_msg.pose.orientation.z = target_qz
        goal_msg.pose.orientation.w = target_qw
        
        # Xuất bản (publish) mục tiêu
        self.simple_goal_pub.publish(goal_msg)

        # Cập nhật GUI
        self.result_label.config(text=f"Sent goal ({target_x:.2f}, {target_y:.2f}) to /move_base_simple/goal.")
        rospy.loginfo(f"Published goal to /move_base_simple/goal: Pose(x={target_x}, y={target_y})")


    def stop_control_loop(self):
        self.control_loop_running = False
        
        path_exists = self.mpc_controller.path_manager.total_length > 0
        self.continuous_button.config(state=tk.NORMAL)
        self.step_button.config(state=tk.NORMAL)
        self.goto_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.NORMAL)
        
        self.send_command(0.0, 0.0)
        self.result_label.config(text="Tracking stopped. Analysis complete.")
        
        if self.mpc_controller.cross_track_errors:
            self.max_cte_var.set(f"Max CTE: {max(self.mpc_controller.cross_track_errors):.4f} m")
            self.avg_cte_var.set(f"Avg CTE: {np.mean(self.mpc_controller.cross_track_errors):.4f} m")
        if self.mpc_controller.heading_errors:
            self.max_he_var.set(f"Max Heading Err: {np.rad2deg(max(self.mpc_controller.heading_errors)):.2f} deg")
            self.avg_he_var.set(f"Avg Heading Err: {np.rad2deg(np.mean(self.mpc_controller.heading_errors)):.2f} deg")

    def clear_path(self):
        if self.control_loop_running: self.stop_control_loop()
        self.mpc_controller.path_manager.clear()
        self.mpc_controller.current_milestone_target_index = 0
        self.line_ref.set_data([], []); self.line_actual.set_data([], [])
        self.lookahead_plot.set_data([], [])
        self.milestone_plot.set_data([], [])
        if self.mpc_controller.current_pose is not None: self.robot_plot.set_data([self.mpc_controller.x], [self.mpc_controller.y])
        else: self.robot_plot.set_data([], [])
        self.canvas_trajectory.draw_idle()
        self.result_label.config(text="Path cleared. Ready to generate a new path.")
        
        self.continuous_button.config(state=tk.NORMAL)
        self.step_button.config(state=tk.NORMAL)

        self.max_cte_var.set("Max CTE: N/A"); self.avg_cte_var.set("Avg CTE: N/A")
        self.max_he_var.set("Max Heading Err: N/A"); self.avg_he_var.set("Avg Heading Err: N/A")
        all_lines = [self.line_linear_velocity, self.line_angular_velocity, self.line_odom_linear_velocity, self.line_odom_angular_velocity, self.line_linear_acceleration, self.line_angular_acceleration]
        for line in all_lines: line.set_data([],[])
        for ax, canvas in [(self.ax_velocity, self.canvas_velocity), (self.ax_acceleration, self.canvas_acceleration)]: ax.relim(); ax.autoscale_view(); canvas.draw_idle()

    def update_plot(self):
        if not self.control_loop_running: return
        x, y, theta = self.mpc_controller.x, self.mpc_controller.y, self.mpc_controller.theta
        v, omega = self.mpc_controller.mpc_control(x, y, theta)
        self.send_command(v, omega)
        self.line_actual.set_data(self.mpc_controller.trajectory_x, self.mpc_controller.trajectory_y)
        self.robot_plot.set_data([x], [y])
        closest_s, _ = self.mpc_controller.path_manager.find_closest_point(np.array([x, y]))
        lookahead_s = np.clip(closest_s + self.mpc_controller.lookahead_distance, 0, self.mpc_controller.path_manager.total_length)
        lookahead_point = self.mpc_controller.path_manager.get_point_at_global_s(lookahead_s)
        self.lookahead_plot.set_data([lookahead_point[0]], [lookahead_point[1]])
        self.canvas_trajectory.draw_idle()
        
        if self.mpc_controller.time_data:
            self.line_linear_velocity.set_data(self.mpc_controller.time_data, self.mpc_controller.velocity_data)
            self.line_angular_velocity.set_data(self.mpc_controller.time_data, self.mpc_controller.angular_velocity_data)
            self.ax_velocity.relim(); self.ax_velocity.autoscale_view(); self.canvas_velocity.draw_idle()
            self.line_linear_acceleration.set_data(self.mpc_controller.time_data, self.mpc_controller.acceleration_data)
            self.line_angular_acceleration.set_data(self.mpc_controller.time_data, self.mpc_controller.angular_acceleration_data)
            self.ax_acceleration.relim(); self.ax_acceleration.autoscale_view(); self.canvas_acceleration.draw_idle()
            
        if self.mpc_controller.odom_time_data:
            self.line_odom_linear_velocity.set_data(self.mpc_controller.odom_time_data, self.mpc_controller.odom_linear_v_data)
            self.line_odom_angular_velocity.set_data(self.mpc_controller.odom_time_data, self.mpc_controller.odom_angular_v_data)
            self.canvas_velocity.draw_idle()

        self.master.update_idletasks()
        if not self.mpc_controller.reached_goal:
            update_interval_ms = max(10, int(self.mpc_controller.dt * 1000 * 0.8))
            self.master.after(update_interval_ms, self.update_plot)
        else:
            self.stop_control_loop()

    def send_command(self, v, omega):
        twist_msg = Twist(); twist_msg.linear.x = v; twist_msg.angular.z = omega
        self.cmd_vel_pub.publish(twist_msg)


def ros_spin():
    try: rospy.spin()
    except rospy.ROSInterruptException: pass

if __name__ == '__main__':
    gui_instance = None
    try:
        rospy.init_node('composite_path_tracker_node')
        dt = 0.01
        v_max, v_min = 1.0, 0.0
        omega_max, omega_min = 1.5, -1.5
        
        lookahead_min = 0.25
        lookahead_max = 1.0
        curvature_threshold = 1.2
        factor_change_rate = 5.0
        
        controller = MPCController(dt, v_max, v_min, omega_max, omega_min, 
                                   lookahead_min, lookahead_max, curvature_threshold,
                                   factor_change_rate)
        
        rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, lambda msg: controller.pose_callback(msg.pose.pose), queue_size=1)
        # rospy.Subscriber('/robot_pose', Pose, lambda msg: controller.pose_callback(msg), queue_size=1)
        rospy.Subscriber('/odom', Odometry, controller.odom_callback, queue_size=1)
        
        root = tk.Tk()
        gui_instance = GUI(root, controller)
        ros_thread = threading.Thread(target=ros_spin, daemon=True)
        ros_thread.start()
        root.mainloop()
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        print("Shutting down...")
        if gui_instance and gui_instance.cmd_vel_pub:
            try:
                gui_instance.send_command(0.0, 0.0)
                rospy.sleep(0.2)
                print("Zero velocity command sent.")
            except Exception as e_final:
                print(f"Error sending final zero cmd: {e_final}")
        if not rospy.is_shutdown():
            rospy.signal_shutdown("Application exit")
        print("Exiting application.")