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
from scipy.signal import butter, filtfilt
import math

class PathWithFilletController:
    def __init__(self, dt, v_max, v_min, omega_max, omega_min, lookahead_distance=0.15, 
                 fillet_radius=0.5, filter_order=4, cutoff_frequency=4.0):
        """Initialize the PathWithFilletController."""
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
        self.waypoints_x = []
        self.waypoints_y = []
        self.distance_threshold = 0.2
        self.lookahead_distance = lookahead_distance
        self.fillet_radius = fillet_radius
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
        self.ramp_up_duration = 2.0
        self.ramp_down_distance = 0.5
        self.velocity_smoothing_alpha = 0.3
        self.path_segments = []
        self.path_x = []
        self.path_y = []
        self.total_path_length = 0.0
        self.current_segment_idx = 0

    def lowpass_filter(self, data):
        """Apply a low-pass filter to the input data."""
        padlen = 3 * self.filter_order
        if len(data) <= padlen:
            return data
        y = filtfilt(self.b, self.a, data, padlen=padlen)
        return y

    def smooth_velocity(self, new_v, new_omega):
        """Smooth the velocity commands."""
        smoothed_v = (1 - self.velocity_smoothing_alpha) * self.last_v + self.velocity_smoothing_alpha * new_v
        smoothed_omega = (1 - self.velocity_smoothing_alpha) * self.last_omega + self.velocity_smoothing_alpha * new_omega
        return smoothed_v, smoothed_omega

    def smooth_ramp_factor(self, factor):
        """Calculate a smooth ramp factor for velocity scaling."""
        return np.sin(factor * np.pi / 2)

    def pose_callback(self, msg):
        """Callback for receiving robot pose from /amcl_pose."""
        quat = msg.pose.pose.orientation
        if quat.w == 0.0 and quat.x == 0.0 and quat.y == 0.0 and quat.z == 0.0:
            rospy.logwarn("Invalid quaternion received, skipping pose update.")
            return

        try:
            euler = tf.transformations.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
            roll, pitch, yaw = euler[0], euler[1], euler[2]
        except Exception as e:
            rospy.logerr(f"Error converting quaternion to Euler: {e}")
            return

        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
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

    def vector_magnitude(self, v):
        """Calculate the magnitude of a 2D vector."""
        return np.sqrt(v[0]**2 + v[1]**2)

    def normalize_vector(self, v):
        """Normalize a 2D vector."""
        mag = self.vector_magnitude(v)
        if mag == 0:
            return np.array([0, 0])
        return v / mag

    def calculate_path_with_fillet(self):
        """Calculate a path with two straight lines connected by a circular fillet."""
        if len(self.waypoints_x) < 3:
            rospy.logwarn("Need at least three waypoints to create a path with fillet.")
            return False

        self.path_segments = []
        self.path_x = []
        self.path_y = []

        # Extract waypoints
        p1 = np.array([self.waypoints_x[0], self.waypoints_y[0]])
        p2 = np.array([self.waypoints_x[1], self.waypoints_y[1]])
        p3 = np.array([self.waypoints_x[2], self.waypoints_y[2]])

        # Calculate vectors
        v1 = p2 - p1  # Vector from P1 to P2
        v2 = p3 - p2  # Vector from P2 to P3
        len_v1 = self.vector_magnitude(v1)
        len_v2 = self.vector_magnitude(v2)

        # Check if segments are long enough for the fillet
        if len_v1 < self.fillet_radius or len_v2 < self.fillet_radius:
            rospy.logwarn("Segments too short for fillet radius. Reducing radius.")
            self.fillet_radius = min(len_v1, len_v2) * 0.5
            if self.fillet_radius < 0.01:
                rospy.logwarn("Segments too short to create a fillet.")
                return False

        # Normalize vectors
        u1 = self.normalize_vector(v1)  # Direction P1 -> P2
        u2 = self.normalize_vector(v2)  # Direction P2 -> P3

        # Calculate angle between segments
        dot_product = np.dot(u1, u2)
        angle = np.arccos(np.clip(dot_product, -1.0, 1.0))
        if abs(np.sin(angle)) < 1e-6:
            rospy.logwarn("Segments are nearly collinear, cannot create fillet.")
            return False

        # Calculate tangent distance
        tangent_distance = self.fillet_radius / np.tan(angle / 2)

        # Limit tangent distance to avoid exceeding segment lengths
        max_tangent = min(len_v1, len_v2) * 0.9  # Allow up to 90% of segment length
        if tangent_distance > max_tangent:
            tangent_distance = max_tangent
            self.fillet_radius = tangent_distance * np.tan(angle / 2)
            rospy.logwarn(f"Adjusted fillet radius to {self.fillet_radius:.2f} m due to segment length.")

        # Calculate tangent points
        t1 = p2 - u1 * tangent_distance  # Tangent point on P1-P2
        t2 = p2 + u2 * tangent_distance  # Tangent point on P2-P3

        # Calculate circle center
        # Vector from P2 to midpoint of chord T1-T2
        chord_mid = (t1 + t2) / 2
        vec_p2_to_mid = chord_mid - p2
        dist_p2_to_mid = self.vector_magnitude(vec_p2_to_mid)

        # Distance from P2 to circle center
        dist_p2_to_center = self.fillet_radius / np.sin(angle / 2)

        # Normalize vector from P2 to chord midpoint
        if dist_p2_to_mid < 1e-6:
            # If T1 and T2 are very close, use perpendicular bisector
            vec_perp = np.array([-u1[1], u1[0]])
            if np.dot(vec_perp, u2) < 0:
                vec_perp = -vec_perp
        else:
            vec_perp = vec_p2_to_mid / dist_p2_to_mid

        # Calculate circle center
        circle_center = p2 + vec_perp * dist_p2_to_center

        # Verify the center by checking distances to T1 and T2
        dist_center_t1 = self.vector_magnitude(circle_center - t1)
        dist_center_t2 = self.vector_magnitude(circle_center - t2)
        if abs(dist_center_t1 - self.fillet_radius) > 1e-3 or abs(dist_center_t2 - self.fillet_radius) > 1e-3:
            rospy.logwarn("Circle center calculation inaccurate, adjusting...")
            # Fallback: Average of points offset from T1 and T2
            offset_vec = vec_perp * np.sqrt(self.fillet_radius**2 - (dist_p2_to_mid)**2)
            circle_center = chord_mid + offset_vec

        # Calculate arc angles
        v_t1 = t1 - circle_center
        v_t2 = t2 - circle_center
        start_angle = np.arctan2(v_t1[1], v_t1[0])
        end_angle = np.arctan2(v_t2[1], v_t2[0])

        # Ensure the arc goes the correct way (shorter arc, inside the angle)
        angle_diff = end_angle - start_angle
        if angle_diff > np.pi:
            end_angle -= 2 * np.pi
        elif angle_diff < -np.pi:
            end_angle += 2 * np.pi

        # Ensure arc direction matches the turn direction
        cross_product = u1[0] * u2[1] - u1[1] * u2[0]
        if (end_angle > start_angle and cross_product < 0) or (end_angle < start_angle and cross_product > 0):
            if end_angle > start_angle:
                end_angle -= 2 * np.pi
            else:
                end_angle += 2 * np.pi

        # Store path segments
        self.path_segments.append({"type": "line", "start": p1, "end": t1})
        self.path_segments.append({"type": "arc", "center": circle_center, "radius": self.fillet_radius,
                                  "start_angle": start_angle, "end_angle": end_angle})
        self.path_segments.append({"type": "line", "start": t2, "end": p3})

        self.generate_path_points()
        return True

    def generate_path_points(self, num_points=500):
        """Generate a dense set of points along the path for visualization."""
        self.path_x = []
        self.path_y = []

        if not self.path_segments:
            return

        total_length = 0
        segment_lengths = []

        for segment in self.path_segments:
            if segment["type"] == "line":
                length = self.vector_magnitude(segment["end"] - segment["start"])
            else:
                angle_diff = abs(segment["end_angle"] - segment["start_angle"])
                length = segment["radius"] * angle_diff

            segment_lengths.append(length)
            total_length += length

        self.total_path_length = total_length

        points_per_segment = [max(int(length / total_length * num_points), 10) for length in segment_lengths]

        for i, segment in enumerate(self.path_segments):
            n_pts = points_per_segment[i]

            if segment["type"] == "line":
                t_values = np.linspace(0, 1, n_pts)
                for t in t_values:
                    pt = segment["start"] + t * (segment["end"] - segment["start"])
                    self.path_x.append(pt[0])
                    self.path_y.append(pt[1])
            else:
                start_angle = segment["start_angle"]
                end_angle = segment["end_angle"]
                # Ensure correct direction for arc
                if end_angle < start_angle:
                    angles = np.linspace(start_angle, end_angle, n_pts)
                else:
                    angles = np.linspace(start_angle, end_angle, n_pts)
                for angle in angles:
                    x = segment["center"][0] + segment["radius"] * np.cos(angle)
                    y = segment["center"][1] + segment["radius"] * np.sin(angle)
                    self.path_x.append(x)
                    self.path_y.append(y)

    def find_closest_point_on_path(self, x, y):
        """Find the closest point on the path to the given position."""
        if not self.path_x or not self.path_y:
            return None, 0, 0

        path_points = np.column_stack((self.path_x, self.path_y))
        point = np.array([x, y])

        distances = np.sqrt(np.sum((path_points - point)**2, axis=1))
        closest_idx = np.argmin(distances)
        path_distance = closest_idx / len(self.path_x) * self.total_path_length

        return closest_idx, path_distance, distances[closest_idx]

    def find_lookahead_point(self, current_idx, lookahead_distance):
        """Find a point on the path that is approximately lookahead_distance ahead."""
        if current_idx is None or len(self.path_x) == 0:
            return None

        path_points = np.column_stack((self.path_x, self.path_y))
        total_points = len(path_points)

        lookahead_points = int((lookahead_distance / self.total_path_length) * total_points)
        lookahead_idx = min(current_idx + lookahead_points, total_points - 1)

        return lookahead_idx

    def calculate_path_heading(self, idx):
        """Calculate the path heading at the given index."""
        if idx is None or len(self.path_x) < 2 or idx >= len(self.path_x) - 1:
            return 0.0

        next_idx = min(idx + 1, len(self.path_x) - 1)
        dx = self.path_x[next_idx] - self.path_x[idx]
        dy = self.path_y[next_idx] - self.path_y[idx]

        return np.arctan2(dy, dx)

    def path_control(self, x, y, theta):
        """Control logic for following the path."""
        if not self.path_x or not self.path_y:
            rospy.logwarn("Path is not defined. Cannot perform path control.")
            return 0.0, 0.0

        closest_idx, path_distance, closest_distance = self.find_closest_point_on_path(x, y)
        lookahead_idx = self.find_lookahead_point(closest_idx, self.lookahead_distance)

        if lookahead_idx is None:
            rospy.logwarn("Could not find lookahead point.")
            return 0.0, 0.0

        lookahead_x = self.path_x[lookahead_idx]
        lookahead_y = self.path_y[lookahead_idx]

        path_heading = self.calculate_path_heading(lookahead_idx)

        dx = lookahead_x - x
        dy = lookahead_y - y
        distance_to_lookahead = np.sqrt(dx**2 + dy**2)

        distance_to_end = np.sqrt((x - self.path_x[-1])**2 + (y - self.path_y[-1])**2)
        if distance_to_end < self.distance_threshold:
            rospy.loginfo("Reached the end of the path!")
            self.reached_goal = True
            return 0.0, 0.0

        heading_error = path_heading - theta
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))

        heading_threshold = 0.1
        linear_speed_kp = 1.2
        angular_speed_kp = 1.5

        if abs(heading_error) > heading_threshold:
            v = 0.2
            omega = angular_speed_kp * heading_error
        else:
            v = linear_speed_kp * min(distance_to_lookahead, 0.5)
            omega = angular_speed_kp * heading_error

        v, omega = self.smooth_velocity(v, omega)

        if self.start_time is not None:
            current_time = rospy.Time.now().to_sec()
            elapsed_time = current_time - self.start_time
            if elapsed_time < self.ramp_up_duration:
                ramp_factor = self.smooth_ramp_factor(elapsed_time / self.ramp_up_duration)
                v *= ramp_factor
                omega *= ramp_factor

        if distance_to_end < self.ramp_down_distance:
            ramp_down_factor = self.smooth_ramp_factor(distance_to_end / self.ramp_down_distance)
            v *= ramp_down_factor
            omega *= ramp_down_factor

        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

        if self.start_time is not None:
            current_time = rospy.Time.now().to_sec()
            dt = current_time - self.start_time

            linear_acceleration = (v - self.last_v) / self.dt if self.dt > 0 else 0.0
            angular_acceleration = (omega - self.last_omega) / self.dt if self.dt > 0 else 0.0

            self.acceleration_data.append(linear_acceleration)
            self.angular_acceleration_data.append(angular_acceleration)
            self.velocity_data.append(v)
            self.angular_velocity_data.append(omega)
            self.time_data.append(dt)

        self.last_v = v
        self.last_omega = omega

        return v, omega

class GUI:
    def __init__(self, master, controller):
        """Initialize the GUI for path tracking."""
        self.master = master
        master.title("Robot Path Tracking with Circular Fillet")
        self.controller = controller

        control_frame = tk.Frame(master)
        control_frame.grid(row=0, column=0, sticky='ew')

        self.start_button = tk.Button(control_frame, text="Start Tracking", command=self.start_control_loop)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)

        self.stop_button = tk.Button(control_frame, text="Stop Tracking", command=self.stop_control_loop, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)

        self.clear_button = tk.Button(control_frame, text="Clear Waypoints", command=self.clear_waypoints)
        self.clear_button.grid(row=0, column=2, padx=5, pady=5)

        radius_frame = tk.Frame(master)
        radius_frame.grid(row=1, column=0, sticky='ew')

        tk.Label(radius_frame, text="Fillet Radius (m):").grid(row=0, column=0, padx=5, pady=5)
        self.radius_var = tk.DoubleVar(value=0.5)
        self.radius_entry = tk.Entry(radius_frame, textvariable=self.radius_var, width=6)
        self.radius_entry.grid(row=0, column=1, padx=5, pady=5)

        self.update_radius_button = tk.Button(radius_frame, text="Update Radius", command=self.update_radius)
        self.update_radius_button.grid(row=0, column=2, padx=5, pady=5)

        self.status_label = tk.Label(master, text="Click to add waypoints. Need at least 3 points.")
        self.status_label.grid(row=2, column=0, pady=5)

        self.tabControl = ttk.Notebook(master)
        self.trajectory_tab = tk.Frame(self.tabControl)
        self.velocity_tab = tk.Frame(self.tabControl)
        self.acceleration_tab = tk.Frame(self.tabControl)

        self.tabControl.add(self.trajectory_tab, text='Trajectory')
        self.tabControl.add(self.velocity_tab, text='Velocity')
        self.tabControl.add(self.acceleration_tab, text='Acceleration')
        self.tabControl.grid(row=3, column=0, sticky='nsew')

        self.setup_trajectory_plot()
        self.setup_velocity_plot()
        self.setup_acceleration_plot()

        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.control_loop_running = False

        master.grid_rowconfigure(3, weight=1)
        master.grid_columnconfigure(0, weight=1)

    def setup_trajectory_plot(self):
        """Setup the trajectory plot in the GUI."""
        self.fig_trajectory, self.ax_trajectory = plt.subplots(figsize=(8, 7))

        try:
            map_img = plt.imread("static/map_image.png")
            map_metadata = {"width": 422, "height": 395, "resolution": 0.05000000074505806,
                            "origin_x": 0.0, "origin_y": 0.0}
            extent = [
                map_metadata["origin_x"],
                map_metadata["origin_x"] + map_metadata["width"] * map_metadata["resolution"],
                map_metadata["origin_y"],
                map_metadata["origin_y"] + map_metadata["height"] * map_metadata["resolution"]
            ]
            self.ax_trajectory.imshow(map_img, extent=extent, aspect='equal', zorder=0)
            self.ax_trajectory.set_xlim([extent[0], extent[1]])
            self.ax_trajectory.set_ylim([extent[2], extent[3]])
        except:
            self.ax_trajectory.set_xlim([-10, 10])
            self.ax_trajectory.set_ylim([-10, 10])
            print("Map image not found. Using default plot limits.")

        self.ax_trajectory.set_xlabel("X (m)")
        self.ax_trajectory.set_ylabel("Y (m)")
        self.ax_trajectory.set_title("Robot Trajectory")
        self.ax_trajectory.grid(True)

        self.robot_path, = self.ax_trajectory.plot([], [], 'b-', label="Robot Path", linewidth=2, zorder=2)
        self.path_plot, = self.ax_trajectory.plot([], [], 'g-', label="Planned Path", linewidth=2, zorder=1)
        self.waypoints_plot, = self.ax_trajectory.plot([], [], 'ro', label="Waypoints", markersize=8, zorder=3)
        self.robot_plot, = self.ax_trajectory.plot([], [], 'go', label="Robot", markersize=10, zorder=4)
        self.lookahead_plot, = self.ax_trajectory.plot([], [], 'yo', label="Lookahead Point", markersize=5, zorder=3)

        self.ax_trajectory.legend(loc='upper right')

        self.canvas_trajectory = FigureCanvasTkAgg(self.fig_trajectory, master=self.trajectory_tab)
        self.canvas_trajectory.draw()
        self.canvas_trajectory.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.fig_trajectory.canvas.mpl_connect('button_press_event', self.onclick)

    def setup_velocity_plot(self):
        """Setup the velocity plot in the GUI."""
        self.fig_velocity, self.ax_velocity = plt.subplots(figsize=(8, 4))
        self.ax_velocity.set_xlabel("Time (s)")
        self.ax_velocity.set_ylabel("Velocity (m/s, rad/s)")
        self.ax_velocity.set_title("Robot Velocity")
        self.ax_velocity.grid(True)

        self.line_linear_velocity, = self.ax_velocity.plot([], [], 'b-', label="Linear Velocity")
        self.line_angular_velocity, = self.ax_velocity.plot([], [], 'r-', label="Angular Velocity")

        self.ax_velocity.legend(loc='upper right')

        self.canvas_velocity = FigureCanvasTkAgg(self.fig_velocity, master=self.velocity_tab)
        self.canvas_velocity.draw()
        self.canvas_velocity.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def setup_acceleration_plot(self):
        """Setup the acceleration plot in the GUI."""
        self.fig_acceleration, self.ax_acceleration = plt.subplots(figsize=(8, 4))
        self.ax_acceleration.set_xlabel("Time (s)")
        self.ax_acceleration.set_ylabel("Acceleration (m/s^2, rad/s^2)")
        self.ax_acceleration.set_title("Robot Acceleration")
        self.ax_acceleration.grid(True)

        self.line_linear_acceleration, = self.ax_acceleration.plot([], [], 'b-', label="Linear Acceleration")
        self.line_angular_acceleration, = self.ax_acceleration.plot([], [], 'r-', label="Angular Acceleration")

        self.ax_acceleration.legend(loc='upper right')

        self.canvas_acceleration = FigureCanvasTkAgg(self.fig_acceleration, master=self.acceleration_tab)
        self.canvas_acceleration.draw()
        self.canvas_acceleration.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def onclick(self, event):
        """Handle mouse clicks to add waypoints."""
        if event.xdata is not None and event.ydata is not None:
            x = event.xdata
            y = event.ydata

            if len(self.controller.waypoints_x) >= 1:
                self.controller.waypoints_x.append(x)
                self.controller.waypoints_y.append(y)
                print(f"Added waypoint at x={x:.2f}, y={y:.2f}")

                num_points = len(self.controller.waypoints_x)
                if num_points < 3:
                    self.status_label.config(text=f"Added point {num_points}. Need at least 3 points.")
                else:
                    self.status_label.config(text=f"Path has {num_points} points. Ready to start tracking.")
                    self.controller.fillet_radius = self.radius_var.get()
                    if self.controller.calculate_path_with_fillet():
                        self.update_path_plot()

            self.update_waypoint_plot()

    def update_radius(self):
        """Update the fillet radius and recalculate the path."""
        try:
            new_radius = float(self.radius_var.get())
            if new_radius <= 0:
                self.status_label.config(text="Radius must be positive.")
                return

            self.controller.fillet_radius = new_radius

            if len(self.controller.waypoints_x) >= 3:
                if self.controller.calculate_path_with_fillet():
                    self.update_path_plot()
                    self.status_label.config(text=f"Updated fillet radius to {new_radius:.2f} m")
                else:
                    self.status_label.config(text="Failed to update path. Check waypoints.")
        except ValueError:
            self.status_label.config(text="Invalid radius value.")

    def update_waypoint_plot(self):
        """Update the waypoint plot in the GUI."""
        self.waypoints_plot.set_data(self.controller.waypoints_x, self.controller.waypoints_y)
        self.ax_trajectory.relim()
        self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()

    def update_path_plot(self):
        """Update the planned path plot in the GUI."""
        self.path_plot.set_data(self.controller.path_x, self.controller.path_y)
        self.ax_trajectory.relim()
        self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()

    def start_control_loop(self):
        """Start the control loop for path tracking."""
        if len(self.controller.waypoints_x) < 3:
            self.status_label.config(text="Need at least 3 waypoints to start tracking.")
            return

        if not self.controller.path_x:
            if not self.controller.calculate_path_with_fillet():
                self.status_label.config(text="Error: Could not create path. Check waypoints.")
                return
            self.update_path_plot()

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.DISABLED)
        self.update_radius_button.config(state=tk.DISABLED)

        self.controller.trajectory_x = []
        self.controller.trajectory_y = []
        self.controller.reached_goal = False
        self.controller.last_v = 0.0
        self.controller.last_omega = 0.0
        self.controller.velocity_data = []
        self.controller.angular_velocity_data = []
        self.controller.acceleration_data = []
        self.controller.angular_acceleration_data = []
        self.controller.time_data = []
        self.controller.start_time = rospy.Time.now().to_sec()
        self.control_loop_running = True

        self.update_plot()

    def stop_control_loop(self):
        """Stop the control loop and reset the robot."""
        self.control_loop_running = False
        self.send_command(0.0, 0.0)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.NORMAL)
        self.update_radius_button.config(state=tk.NORMAL)
        self.status_label.config(text="Tracking stopped. Click to add waypoints.")

    def clear_waypoints(self):
        """Clear all waypoints and reset the path."""
        self.controller.waypoints_x = []
        self.controller.waypoints_y = []
        self.controller.path_x = []
        self.controller.path_y = []
        self.controller.path_segments = []
        self.controller.total_path_length = 0.0
        self.waypoints_plot.set_data([], [])
        self.path_plot.set_data([], [])
        self.robot_path.set_data([], [])
        self.robot_plot.set_data([], [])
        self.lookahead_plot.set_data([], [])
        self.ax_trajectory.relim()
        self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()
        self.status_label.config(text="Waypoints cleared. Click to add new waypoints.")

    def update_plot(self):
        """Update all plots during the control loop."""
        if not self.control_loop_running:
            return

        if self.controller.current_pose is None:
            self.status_label.config(text="Waiting for initial pose from /amcl_pose...")
            self.master.after(10, self.update_plot)
            return

        x = self.controller.x
        y = self.controller.y
        theta = self.controller.theta

        v, omega = self.controller.path_control(x, y, theta)
        self.send_command(v, omega)

        self.robot_path.set_data(self.controller.trajectory_x, self.controller.trajectory_y)
        self.robot_plot.set_data([x], [y])

        closest_idx, _, _ = self.controller.find_closest_point_on_path(x, y)
        lookahead_idx = self.controller.find_lookahead_point(closest_idx, self.controller.lookahead_distance)
        if lookahead_idx is not None:
            lookahead_x = self.controller.path_x[lookahead_idx]
            lookahead_y = self.controller.path_y[lookahead_idx]
            self.lookahead_plot.set_data([lookahead_x], [lookahead_y])
        else:
            self.lookahead_plot.set_data([], [])

        self.ax_trajectory.relim()
        self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()

        filtered_velocity_data = self.controller.lowpass_filter(self.controller.velocity_data)
        filtered_angular_velocity_data = self.controller.lowpass_filter(self.controller.angular_velocity_data)
        self.line_linear_velocity.set_data(self.controller.time_data, filtered_velocity_data)
        self.line_angular_velocity.set_data(self.controller.time_data, filtered_angular_velocity_data)
        self.ax_velocity.relim()
        self.ax_velocity.autoscale_view()
        self.canvas_velocity.draw_idle()

        self.line_linear_acceleration.set_data(self.controller.time_data, self.controller.acceleration_data)
        self.line_angular_acceleration.set_data(self.controller.time_data, self.controller.angular_acceleration_data)
        self.ax_acceleration.relim()
        self.ax_acceleration.autoscale_view()
        self.canvas_acceleration.draw_idle()

        self.master.update()

        if not self.controller.reached_goal:
            self.master.after(10, self.update_plot)
        else:
            self.stop_control_loop()

    def send_command(self, v, omega):
        """Send velocity commands to the robot."""
        twist_msg = Twist()
        twist_msg.linear.x = v
        twist_msg.angular.z = omega
        self.cmd_vel_pub.publish(twist_msg)
        print(f"Published to /cmd_vel: linear.x = {v:.6f}, angular.z = {omega:.6f}")

def ros_spin():
    """Keep ROS spinning in a separate thread."""
    rospy.spin()

if __name__ == '__main__':
    rospy.init_node('path_with_fillet_node')
    dt = 0.01
    v_max = 0.4
    v_min = -0.4
    omega_max = 0.4
    omega_min = -0.4
    lookahead_distance = 0.15

    controller = PathWithFilletController(dt, v_max, v_min, omega_max, omega_min, lookahead_distance)
    rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, controller.pose_callback)
    root = tk.Tk()
    gui = GUI(root, controller)
    threading.Thread(target=ros_spin, daemon=True).start()
    root.mainloop()