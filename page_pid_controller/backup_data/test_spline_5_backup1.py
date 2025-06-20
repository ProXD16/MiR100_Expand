
import rospy
from geometry_msgs.msg import Pose, Twist, PoseWithCovarianceStamped
import numpy as np
import tkinter as tk
import tkinter.ttk as ttk
import threading
import tf.transformations
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# from scipy.interpolate import splrep, splev # No longer used for spline calculation
from scipy.signal import butter, filtfilt

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
        
        # New spline representation: list of Bezier segments
        # Each segment: {'x_coeffs': (P0x,C1x,C2x,P3x), 'y_coeffs': (P0y,C1y,C2y,P3y), 
        #                's_start': float, 's_end': float, 'length': float,
        #                'arc_length_samples': np.array, 't_samples': np.array}
        self.bezier_segments = []
        self.num_samples_for_arc_length = 20 # Samples per Bezier segment for arc length approximation

        self.arclength = None
        self.waypoints_x = []
        self.waypoints_y = []
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
        self.b, self.a = butter(self.filter_order, self.cutoff_frequency / (1 / (2 * self.dt)), btype='low', analog=False)
        self.ramp_up_duration = 2.0  # Duration for velocity ramp-up
        self.ramp_down_distance = 0.5  # Distance to start ramp-down
        self.velocity_smoothing_alpha = 0.3  # Smoothing factor

    def lowpass_filter(self, data):
        padlen = 3 * self.filter_order
        if len(data) <= padlen:
            return data
        y = filtfilt(self.b, self.a, data, padlen=padlen)
        return y

    def smooth_velocity(self, new_v, new_omega):
        """Apply exponential moving average to smooth velocity commands."""
        smoothed_v = (1 - self.velocity_smoothing_alpha) * self.last_v + self.velocity_smoothing_alpha * new_v
        smoothed_omega = (1 - self.velocity_smoothing_alpha) * self.last_omega + self.velocity_smoothing_alpha * new_omega
        return smoothed_v, smoothed_omega

    def smooth_ramp_factor(self, factor):
        """Apply sinusoidal scaling for smooth ramp-up and ramp-down."""
        return np.sin(factor * np.pi / 2)

    # def pose_callback(self, msg):
    #     quat = msg.orientation
    #     if quat.w == 0.0 and quat.x == 0.0 and quat.y == 0.0 and quat.z == 0.0:
    #         rospy.logwarn("Invalid quaternion received, skipping pose update.")
    #         return

    #     try:
    #         euler = tf.transformations.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
    #         roll, pitch, yaw = euler[0], euler[1], euler[2]
    #     except Exception as e:
    #         rospy.logerr(f"Error converting quaternion to Euler: {e}")
    #         return

    #     self.x = msg.position.x
    #     self.y = msg.position.y
    #     self.theta = yaw
    #     self.current_pose = np.array([self.x, self.y, self.theta])
    #     self.trajectory_x.append(self.x)
    #     self.trajectory_y.append(self.y)

    #     if len(self.waypoints_x) == 0:
    #         self.waypoints_x.append(self.x)
    #         self.waypoints_y.append(self.y)
    #     else:
    #         self.waypoints_x[0] = self.x
    #         self.waypoints_y[0] = self.y

    def pose_callback(self, msg):
        msg = msg.pose.pose
        quat = msg.orientation
        if quat.w == 0.0 and quat.x == 0.0 and quat.y == 0.0 and quat.z == 0.0:
            rospy.logwarn("Invalid quaternion received, skipping pose update.")
            return

        try:
            euler = tf.transformations.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
            roll, pitch, yaw = euler[0], euler[1], euler[2]
        except Exception as e:
            rospy.logerr(f"Error converting quaternion to Euler: {e}")
            return

        self.x = msg.position.x
        self.y = msg.position.y
        self.theta = yaw
        self.current_pose = np.array([self.x, self.y, self.theta])
        self.trajectory_x.append(self.x)
        self.trajectory_y.append(self.y)

        if len(self.waypoints_x) == 0:
            self.waypoints_x.append(self.x)
            self.waypoints_y.append(self.y)
        else:
            self.waypoints_x[0] = self.x
            self.waypoints_y[0] = self.y

    def _get_catmull_rom_control_points(self, points_array, idx):
        """
        Helper to get the 4 points (p0, p1, p2, p3) for Catmull-Rom spline
        segment between points_array[idx] (p1) and points_array[idx+1] (p2).
        Handles endpoint duplication.
        """
        p1 = points_array[idx]
        p2 = points_array[idx+1]
        
        if idx == 0:
            p0 = p1 # Duplicate start point
        else:
            p0 = points_array[idx-1]
            
        if idx >= len(points_array) - 2:
            p3 = p2 # Duplicate end point
        else:
            p3 = points_array[idx+2]
            
        return p0, p1, p2, p3

    def _catmull_to_bezier_coeffs(self, p0, p1, p2, p3, tension=0.0):
        """
        Converts Catmull-Rom control points (p0, p1, p2, p3) for segment p1-p2
        to cubic Bezier control points (B0, B1, B2, B3).
        Here, B0=p1, B3=p2.
        For tension=0 (Cardinal spline), this matches the JS:
        c1 = p1 + (p2 - p0) / 6
        c2 = p2 - (p3 - p1) / 6
        """
        if not isinstance(p0, np.ndarray): p0 = np.array(p0)
        if not isinstance(p1, np.ndarray): p1 = np.array(p1)
        if not isinstance(p2, np.ndarray): p2 = np.array(p2)
        if not isinstance(p3, np.ndarray): p3 = np.array(p3)

        # Bezier control points for segment p1 to p2
        b0 = p1
        b1 = p1 + (p2 - p0) / 6.0
        b2 = p2 - (p3 - p1) / 6.0
        b3 = p2
        return b0, b1, b2, b3

    def _evaluate_bezier(self, coeffs, t):
        """Evaluates a cubic Bezier curve at parameter t (or array of t)."""
        t = np.asarray(t)
        b0, b1, b2, b3 = coeffs
        # Ensure coeffs are np.array for broadcasting if t is an array
        b0,b1,b2,b3 = np.array(b0), np.array(b1), np.array(b2), np.array(b3)
        
        # Reshape t to (n,1) if coeffs are (dim,) to allow broadcasting for (n,dim) result
        if t.ndim == 1 and b0.ndim ==1: # if t is 1D array and points are 1D (scalar components)
           t_ = t[:, np.newaxis]
        else: # t is scalar or already shaped
            t_ = t

        return ( (1-t_)**3 * b0 + 
                 3 * (1-t_)**2 * t_ * b1 + 
                 3 * (1-t_) * t_**2 * b2 + 
                 t_**3 * b3 )

    def _evaluate_bezier_derivative(self, coeffs, t):
        """Evaluates the derivative of a cubic Bezier curve at parameter t."""
        t = np.asarray(t)
        b0, b1, b2, b3 = coeffs
        b0,b1,b2,b3 = np.array(b0), np.array(b1), np.array(b2), np.array(b3)

        if t.ndim == 1 and b0.ndim ==1:
           t_ = t[:, np.newaxis]
        else:
            t_ = t
            
        return ( 3 * (1-t_)**2 * (b1 - b0) + 
                 6 * (1-t_) * t_ * (b2 - b1) + 
                 3 * t_**2 * (b3 - b2) )

    def calculate_spline(self):
        if len(self.waypoints_x) < 2:
            rospy.logwarn("Need at least two waypoints to create a spline.")
            return False

        self.bezier_segments = []
        current_arclength = 0.0

        waypoints_x_np = np.array(self.waypoints_x)
        waypoints_y_np = np.array(self.waypoints_y)

        num_segments = len(self.waypoints_x) - 1

        for i in range(num_segments):
            # Get Catmull-Rom points for x and y components
            p0x, p1x, p2x, p3x = self._get_catmull_rom_control_points(waypoints_x_np, i)
            p0y, p1y, p2y, p3y = self._get_catmull_rom_control_points(waypoints_y_np, i)

            # Convert to Bezier coefficients for x and y
            x_coeffs = self._catmull_to_bezier_coeffs(p0x, p1x, p2x, p3x)
            y_coeffs = self._catmull_to_bezier_coeffs(p0y, p1y, p2y, p3y)
            
            # Approximate arc length of this Bezier segment
            t_samples_arc = np.linspace(0, 1, self.num_samples_for_arc_length + 1)
            x_pts_on_segment = self._evaluate_bezier(x_coeffs, t_samples_arc)
            y_pts_on_segment = self._evaluate_bezier(y_coeffs, t_samples_arc)
            
            segment_len = 0.0
            arc_length_samples_local = [0.0]
            for k in range(1, len(t_samples_arc)):
                dist = np.sqrt((x_pts_on_segment[k] - x_pts_on_segment[k-1])**2 + 
                               (y_pts_on_segment[k] - y_pts_on_segment[k-1])**2)
                segment_len += dist
                arc_length_samples_local.append(segment_len)

            if segment_len < 1e-6 and num_segments > 1 : # Avoid issues with zero-length segments if not the only one
                rospy.logwarn(f"Segment {i} has near zero length. This might cause issues.")
                 # If a segment has zero length, make its arc_length_samples flat to avoid NaN in interp
                if len(arc_length_samples_local) > 1 : arc_length_samples_local = [0.0] * len(arc_length_samples_local)


            self.bezier_segments.append({
                'x_coeffs': x_coeffs,
                'y_coeffs': y_coeffs,
                's_start': current_arclength,
                'length': segment_len,
                's_end': current_arclength + segment_len,
                'arc_length_samples_local': np.array(arc_length_samples_local),
                't_samples_for_arc': t_samples_arc # These are the t values corresponding to arc_length_samples_local
            })
            current_arclength += segment_len
        
        self.arclength = current_arclength
        if self.arclength is None or self.arclength < 1e-6:
            rospy.logwarn("Total distance for spline is too small.")
            return False
            
        return True

    def _get_segment_and_t_from_s(self, s_target):
        if not self.bezier_segments or self.arclength is None:
            return None, None

        s_target = np.clip(s_target, 0, self.arclength)

        for i, segment in enumerate(self.bezier_segments):
            # Check if s_target is within this segment (or is the last point of the spline)
            if segment['s_start'] <= s_target <= segment['s_end'] or \
               (i == len(self.bezier_segments) - 1 and s_target > segment['s_end']): # Handle s_target == arclength
                
                s_local = s_target - segment['s_start']
                
                if segment['length'] < 1e-6: # Zero length segment
                    t = 0.0 if s_local == 0 else 1.0 # Or handle as error
                elif len(segment['arc_length_samples_local']) <= 1 or len(segment['t_samples_for_arc']) <= 1:
                    t = 0.0 # Fallback for malformed segment
                else:
                    # Interpolate to find t from s_local
                    t = np.interp(s_local, segment['arc_length_samples_local'], segment['t_samples_for_arc'])
                return segment, np.clip(t, 0, 1)
        
        # Should not be reached if s_target is clipped and arclength > 0
        rospy.logwarn_throttle(1.0, f"Could not find segment for s_target={s_target}, arclength={self.arclength}. Returning last segment.")
        last_segment = self.bezier_segments[-1]
        return last_segment, 1.0


    def _evaluate_spline_at_s(self, s_target, component):
        segment, t = self._get_segment_and_t_from_s(s_target)
        if segment is None:
            # Fallback: return last waypoint's coordinate if s is beyond arclength
            if component == 'x': return self.waypoints_x[-1]
            else: return self.waypoints_y[-1]

        coeffs = segment[f'{component}_coeffs']
        return self._evaluate_bezier(coeffs, t)

    def _evaluate_spline_derivative_at_s(self, s_target, component):
        segment, t = self._get_segment_and_t_from_s(s_target)
        if segment is None: return 0.0

        coeffs = segment[f'{component}_coeffs']
        val_dt = self._evaluate_bezier_derivative(coeffs, t)
        
        # Need ds/dt to convert d_component/dt to d_component/ds
        dx_dt = self._evaluate_bezier_derivative(segment['x_coeffs'], t)
        dy_dt = self._evaluate_bezier_derivative(segment['y_coeffs'], t)
        
        ds_dt = np.sqrt(dx_dt**2 + dy_dt**2)
        
        if ds_dt < 1e-6: # Avoid division by zero; implies stationary point or cusp
            return 0.0 
        return val_dt / ds_dt


    def find_closest_point_on_spline(self, x, y):
        if not self.bezier_segments or self.arclength is None or self.arclength < 1e-6:
            return 0.0
        
        # Sample points along the entire spline
        num_total_samples = 1000 
        s_values_sampled = np.linspace(0, self.arclength, num_total_samples)
        
        min_dist_sq = float('inf')
        closest_s = 0.0

        for s_sample in s_values_sampled:
            x_spline = self._evaluate_spline_at_s(s_sample, 'x')
            y_spline = self._evaluate_spline_at_s(s_sample, 'y')
            dist_sq = (x_spline - x)**2 + (y_spline - y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_s = s_sample
        return closest_s

    def mpc_control(self, x, y, theta):
        if not self.bezier_segments or self.arclength is None:
            rospy.logwarn("Spline is not defined. Cannot perform MPC control.")
            return 0.0, 0.0

        closest_s = self.find_closest_point_on_spline(x, y)

        lookahead_s = closest_s + self.lookahead_distance
        lookahead_s = np.clip(lookahead_s, 0, self.arclength) # Ensure lookahead_s is within bounds

        lookahead_x = self._evaluate_spline_at_s(lookahead_s, 'x')
        lookahead_y = self._evaluate_spline_at_s(lookahead_s, 'y')
        
        final_goal_x = self.waypoints_x[-1]
        final_goal_y = self.waypoints_y[-1]
        distance_to_final_goal = np.sqrt((x - final_goal_x)**2 + (y - final_goal_y)**2)
        if distance_to_final_goal < self.distance_threshold:
            rospy.loginfo("Reached the final goal!")
            self.reached_goal = True
            return 0.0, 0.0

        # Get derivatives at lookahead_s
        dx_ds = self._evaluate_spline_derivative_at_s(lookahead_s, 'x')
        dy_ds = self._evaluate_spline_derivative_at_s(lookahead_s, 'y')
        
        # Handle potential issue where derivative is zero (e.g. at sharp turns or end of spline)
        if abs(dx_ds) < 1e-6 and abs(dy_ds) < 1e-6:
            # Fallback: use direction from current pose to lookahead point
            angle_to_goal = np.arctan2(lookahead_y - y, lookahead_x - x)
        else:
            angle_to_goal = np.arctan2(dy_ds, dx_ds)

        heading_error = angle_to_goal - theta
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))

        x_error = lookahead_x - x
        y_error = lookahead_y - y
        distance_error = np.sqrt(x_error**2 + y_error**2)

        heading_threshold = 0.1
        linear_speed_kp = 1.8
        angular_speed_kp = 1.8

        if abs(heading_error) > heading_threshold:
            v = 0.0
            omega = angular_speed_kp * heading_error
        else:
            v = linear_speed_kp * distance_error
            omega = angular_speed_kp * heading_error

        # Smooth velocity commands
        v, omega = self.smooth_velocity(v, omega)

        # Apply velocity ramp-up
        if self.start_time is not None:
            current_time = rospy.Time.now().to_sec()
            elapsed_time = current_time - self.start_time
            if elapsed_time < self.ramp_up_duration:
                ramp_factor = self.smooth_ramp_factor(elapsed_time / self.ramp_up_duration)
                v *= ramp_factor
                omega *= ramp_factor

        # Apply velocity ramp-down
        if distance_to_final_goal < self.ramp_down_distance:
            ramp_down_factor = self.smooth_ramp_factor(distance_to_final_goal / self.ramp_down_distance)
            v *= ramp_down_factor
            omega *= ramp_down_factor

        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

        if self.start_time is not None:
            current_time = rospy.Time.now().to_sec()
            if len(self.time_data) > 0:
                dt_accel = current_time - (self.start_time + self.time_data[-1])
            else:
                dt_accel = current_time - self.start_time

            if dt_accel > 1e-6:
                linear_acceleration = (v - self.last_v) / dt_accel
                angular_acceleration = (omega - self.last_omega) / dt_accel
            else:
                linear_acceleration = 0.0
                angular_acceleration = 0.0

            self.acceleration_data.append(linear_acceleration)
            self.angular_acceleration_data.append(angular_acceleration)
            self.velocity_data.append(v)
            self.angular_velocity_data.append(omega)
            self.time_data.append(current_time - self.start_time)

        self.last_v = v
        self.last_omega = omega
        return v, omega

class GUI:
    def __init__(self, master, mpc_controller):
        self.master = master
        master.title("MiR100 Spline Tracking (Catmull-Rom Bezier + Map)") # Updated title

        self.mpc_controller = mpc_controller

        self.start_button = tk.Button(master, text="Start Tracking", command=self.start_control_loop)
        self.start_button.grid(row=0, column=0)
        self.stop_button = tk.Button(master, text="Stop Tracking", command=self.stop_control_loop, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1)
        self.clear_button = tk.Button(master, text="Clear Waypoints", command=self.clear_waypoints)
        self.clear_button.grid(row=0, column=2)

        self.result_label = tk.Label(master, text="")
        self.result_label.grid(row=1, column=0, columnspan=3)

        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

        self.control_loop_running = False

        self.tabControl = ttk.Notebook(master)
        self.trajectory_tab = tk.Frame(self.tabControl)
        self.velocity_tab = tk.Frame(self.tabControl)
        self.acceleration_tab = tk.Frame(self.tabControl)
        self.tabControl.add(self.trajectory_tab, text='Trajectory')
        self.tabControl.add(self.velocity_tab, text='Velocity')
        self.tabControl.add(self.acceleration_tab, text='Acceleration')
        self.tabControl.grid(row=2, column=0, columnspan=3)

        self.fig_trajectory, self.ax_trajectory = plt.subplots()
        try:
            map_img = plt.imread("static/map_image.png")
            map_metadata = {"width": 400, "height": 400, "resolution": 0.05000000074505806,
                            "origin_x": 0.0, "origin_y": 0.0}
            extent = [
                map_metadata["origin_x"],
                map_metadata["origin_x"] + map_metadata["width"] * map_metadata["resolution"],
                map_metadata["origin_y"],
                map_metadata["origin_y"] + map_metadata["height"] * map_metadata["resolution"]
            ]
            self.ax_trajectory.imshow(map_img, extent=extent, aspect='equal', zorder=0, cmap='gray')
            self.ax_trajectory.set_xlim([extent[0], extent[1]])
            self.ax_trajectory.set_ylim([extent[2], extent[3]])
        except FileNotFoundError:
            rospy.logwarn("Map file 'static/map_image.png' not found. Displaying without map background.")
            self.ax_trajectory.set_xlim([-5, 25])
            self.ax_trajectory.set_ylim([-5, 25])

        self.ax_trajectory.set_xlabel("X (m)")
        self.ax_trajectory.set_ylabel("Y (m)")
        self.ax_trajectory.set_title("Robot Trajectory")
        self.line, = self.ax_trajectory.plot([], [], label="Robot Path", zorder=2)
        self.waypoints_plot, = self.ax_trajectory.plot([], [], 'bo', label="Waypoints", zorder=3)
        self.robot_plot, = self.ax_trajectory.plot([], [], 'go', label="Robot", markersize=10, zorder=4)
        self.spline_plot, = self.ax_trajectory.plot([], [], 'g-', label="Spline", linewidth=2, zorder=2)
        self.lookahead_plot, = self.ax_trajectory.plot([], [], 'yo', label="Lookahead Point", markersize=5, zorder=3)
        self.ax_trajectory.legend()

        self.canvas_trajectory = FigureCanvasTkAgg(self.fig_trajectory, master=self.trajectory_tab)
        self.canvas_trajectory.draw()
        self.canvas_trajectory.get_tk_widget().grid(row=0, column=0, columnspan=3)
        self.fig_trajectory.canvas.mpl_connect('button_press_event', self.onclick)

        self.fig_velocity, self.ax_velocity = plt.subplots()
        self.ax_velocity.set_xlabel("Time (s)")
        self.ax_velocity.set_ylabel("Velocity (m/s, rad/s)")
        self.ax_velocity.set_title("Robot Velocity")
        self.line_linear_velocity, = self.ax_velocity.plot([], [], label="Linear Velocity (Filtered)")
        self.line_angular_velocity, = self.ax_velocity.plot([], [], label="Angular Velocity (Filtered)")
        self.ax_velocity.legend()
        self.canvas_velocity = FigureCanvasTkAgg(self.fig_velocity, master=self.velocity_tab)
        self.canvas_velocity.draw()
        self.canvas_velocity.get_tk_widget().grid(row=0, column=0, columnspan=3)

        self.fig_acceleration, self.ax_acceleration = plt.subplots()
        self.ax_acceleration.set_xlabel("Time (s)")
        self.ax_acceleration.set_ylabel("Acceleration (m/s^2, rad/s^2)")
        self.ax_acceleration.set_title("Robot Acceleration")
        self.line_linear_acceleration, = self.ax_acceleration.plot([], [], label="Linear Acceleration")
        self.line_angular_acceleration, = self.ax_acceleration.plot([], [], label="Angular Acceleration")
        self.ax_acceleration.legend()
        self.canvas_acceleration = FigureCanvasTkAgg(self.fig_acceleration, master=self.acceleration_tab)
        self.canvas_acceleration.draw()
        self.canvas_acceleration.get_tk_widget().grid(row=0, column=0, columnspan=3)

    def onclick(self, event):
        if event.inaxes == self.ax_trajectory and not self.control_loop_running:
            if event.xdata is not None and event.ydata is not None:
                x = event.xdata
                y = event.ydata
                if len(self.mpc_controller.waypoints_x) >= 1:
                    self.mpc_controller.waypoints_x.append(x)
                    self.mpc_controller.waypoints_y.append(y)
                    self.update_waypoint_plot()
                    print(f"Added waypoint at x={x:.2f}, y={y:.2f}")
                else:
                    print("Waiting for initial robot pose to set the first waypoint.")

    def start_control_loop(self):
        if len(self.mpc_controller.waypoints_x) < 2:
            self.result_label.config(text="Error: Add at least one more waypoint.")
            return

        if not self.mpc_controller.calculate_spline():
            self.result_label.config(text="Error: Could not create spline.")
            return

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.DISABLED)
        self.result_label.config(text="Tracking started...")

        self.mpc_controller.reached_goal = False
        self.mpc_controller.velocity_data = []
        self.mpc_controller.angular_velocity_data = []
        self.mpc_controller.acceleration_data = []
        self.mpc_controller.angular_acceleration_data = []
        self.mpc_controller.time_data = []
        self.mpc_controller.last_v = 0.0
        self.mpc_controller.last_omega = 0.0
        self.mpc_controller.start_time = rospy.Time.now().to_sec()

        self.control_loop_running = True
        self.update_plot()

    def stop_control_loop(self):
        self.control_loop_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.NORMAL)
        self.send_command(0.0, 0.0)
        self.result_label.config(text="Tracking stopped.")

    def clear_waypoints(self):
        if self.control_loop_running:
            self.stop_control_loop()

        if self.mpc_controller.current_pose is not None:
            self.mpc_controller.waypoints_x = [self.mpc_controller.x]
            self.mpc_controller.waypoints_y = [self.mpc_controller.y]
        else:
            self.mpc_controller.waypoints_x = []
            self.mpc_controller.waypoints_y = []

        self.mpc_controller.bezier_segments = [] # Clear Bezier segments
        self.mpc_controller.arclength = None
        self.mpc_controller.trajectory_x = []
        self.mpc_controller.trajectory_y = []

        self.waypoints_plot.set_data(self.mpc_controller.waypoints_x, self.mpc_controller.waypoints_y)
        self.spline_plot.set_data([], [])
        self.line.set_data([], [])
        if self.mpc_controller.current_pose is not None:
            self.robot_plot.set_data([self.mpc_controller.x], [self.mpc_controller.y])
        else:
            self.robot_plot.set_data([], [])
        self.lookahead_plot.set_data([], [])

        self.canvas_trajectory.draw_idle()

        self.mpc_controller.velocity_data = []
        self.mpc_controller.angular_velocity_data = []
        self.mpc_controller.acceleration_data = []
        self.mpc_controller.angular_acceleration_data = []
        self.mpc_controller.time_data = []
        self.line_linear_velocity.set_data([], [])
        self.line_angular_velocity.set_data([], [])
        self.ax_velocity.relim()
        self.ax_velocity.autoscale_view()
        self.canvas_velocity.draw_idle()
        self.line_linear_acceleration.set_data([], [])
        self.line_angular_acceleration.set_data([], [])
        self.ax_acceleration.relim()
        self.ax_acceleration.autoscale_view()
        self.canvas_acceleration.draw_idle()

        self.result_label.config(text="Waypoints cleared. Add new waypoints.")

    def update_waypoint_plot(self):
        self.waypoints_plot.set_data(self.mpc_controller.waypoints_x, self.mpc_controller.waypoints_y)
        self.canvas_trajectory.draw_idle()

    def update_plot(self):
        if not self.control_loop_running:
            return

        if self.mpc_controller.current_pose is None:
            self.result_label.config(text="Waiting for initial pose from /robot_pose...")
            self.master.after(100, self.update_plot)
            return

        x = self.mpc_controller.x
        y = self.mpc_controller.y
        theta = self.mpc_controller.theta

        v, omega = self.mpc_controller.mpc_control(x, y, theta)
        self.send_command(v, omega)

        self.line.set_data(self.mpc_controller.trajectory_x, self.mpc_controller.trajectory_y)
        self.robot_plot.set_data([x], [y])

        # Update spline plotting for Bezier segments
        if self.mpc_controller.bezier_segments and self.mpc_controller.arclength is not None:
            x_spline_pts, y_spline_pts = [], []
            num_plot_samples_per_segment = 10 # For smoother visual
            for seg_idx, segment_data in enumerate(self.mpc_controller.bezier_segments):
                x_coeffs = segment_data['x_coeffs']
                y_coeffs = segment_data['y_coeffs']
                t_plot = np.linspace(0, 1, num_plot_samples_per_segment)
                
                # Use controller's _evaluate_bezier which handles np arrays correctly
                x_pts_seg = self.mpc_controller._evaluate_bezier(x_coeffs, t_plot)
                y_pts_seg = self.mpc_controller._evaluate_bezier(y_coeffs, t_plot)
                
                if seg_idx == 0:
                    x_spline_pts.extend(x_pts_seg)
                    y_spline_pts.extend(y_pts_seg)
                else: # Avoid duplicating connection points
                    x_spline_pts.extend(x_pts_seg[1:])
                    y_spline_pts.extend(y_pts_seg[1:])
            self.spline_plot.set_data(x_spline_pts, y_spline_pts)

            closest_s = self.mpc_controller.find_closest_point_on_spline(x, y)
            lookahead_s = closest_s + self.mpc_controller.lookahead_distance
            lookahead_s = np.clip(lookahead_s, 0, self.mpc_controller.arclength)
            
            lookahead_x = self.mpc_controller._evaluate_spline_at_s(lookahead_s, 'x')
            lookahead_y = self.mpc_controller._evaluate_spline_at_s(lookahead_s, 'y')
            self.lookahead_plot.set_data([lookahead_x], [lookahead_y])
        else:
            self.spline_plot.set_data([], [])
            self.lookahead_plot.set_data([], [])

        self.update_waypoint_plot()
        self.canvas_trajectory.draw_idle()

        if len(self.mpc_controller.time_data) > 0:
            filtered_velocity_data = self.mpc_controller.lowpass_filter(self.mpc_controller.velocity_data)
            filtered_angular_velocity_data = self.mpc_controller.lowpass_filter(self.mpc_controller.angular_velocity_data)
            self.line_linear_velocity.set_data(self.mpc_controller.time_data, filtered_velocity_data)
            self.line_angular_velocity.set_data(self.mpc_controller.time_data, filtered_angular_velocity_data)
            self.ax_velocity.relim()
            self.ax_velocity.autoscale_view()
            self.canvas_velocity.draw_idle()

        if len(self.mpc_controller.time_data) > 0:
            self.line_linear_acceleration.set_data(self.mpc_controller.time_data, self.mpc_controller.acceleration_data)
            self.line_angular_acceleration.set_data(self.mpc_controller.time_data, self.mpc_controller.angular_acceleration_data)
            self.ax_acceleration.relim()
            self.ax_acceleration.autoscale_view()
            self.canvas_acceleration.draw_idle()

        self.master.update_idletasks()

        if not self.mpc_controller.reached_goal:
            update_interval_ms = max(10, int(self.mpc_controller.dt * 1000))
            self.master.after(update_interval_ms, self.update_plot)
        else:
            self.result_label.config(text="Reached final goal!")
            self.stop_control_loop()

    def send_command(self, v, omega):
        twist_msg = Twist()
        twist_msg.linear.x = v
        twist_msg.angular.z = omega
        self.cmd_vel_pub.publish(twist_msg)

def ros_spin():
    rospy.spin()

if __name__ == '__main__':
    final_pub = None
    try:
        rospy.init_node('spline_tracking_node_catmull_rom_map') # Updated node name
        dt = 0.1 
        v_max = 0.4
        v_min = -0.4
        omega_max = 0.4
        omega_min = -0.4
        lookahead_distance = 0.05
        filter_order = 4
        cutoff_freq = 2.0

        controller = MPCController(dt, v_max, v_min, omega_max, omega_min,
                                   lookahead_distance, filter_order, cutoff_freq)
        # rospy.Subscriber('/robot_pose', Pose, controller.pose_callback)
        rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, controller.pose_callback)
        root = tk.Tk()
        gui = GUI(root, controller)
        ros_thread = threading.Thread(target=ros_spin, daemon=True)
        ros_thread.start()
        root.mainloop()
    except rospy.ROSInterruptException:
        print("ROS node interrupted.")
    except KeyboardInterrupt:
        print("Script terminated by user.")
    finally:
        if rospy.is_shutdown():
            print("ROS is already shutdown.")
        else:
            print("Sending zero velocity command before exiting.")
            try:
                if 'gui' in locals() and gui and gui.cmd_vel_pub:
                    gui.send_command(0.0, 0.0)
                    rospy.sleep(0.2) # Give time for the message to be sent
                else: # Fallback if GUI object or publisher isn't available
                    if not final_pub:
                         # Create a temporary publisher if needed
                        final_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
                        rospy.sleep(0.2) # Allow publisher to connect
                    if final_pub:
                        final_pub.publish(Twist()) # Send zero velocities
                        rospy.sleep(0.2)
            except Exception as e:
                print(f"Error sending final zero command: {e}")

