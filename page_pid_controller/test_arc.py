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
from numpy import cos, sin, arctan2, sqrt

def circle_from_3_points(p1, p2, p3):
    """Calculates the center and radius of a circle passing through three points."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    A = x1*(y2-y3) - y1*(x2-x3) + x2*y3 - x3*y2
    B = (x1**2 + y1**2) * (y3-y2) + (x2**2 + y2**2) * (y1-y3) + (x3**2 + y3**2) * (y2-y1)
    C = (x1**2 + y1**2) * (x2-x3) + (x2**2 + y2**2) * (x3-x1) + (x3**2 + y3**2) * (x1-x2)
    D = (x1**2 + y1**2) * (x3*y2 - x2*y3) + (x2**2 + y2**2) * (x1*y3 - x3*y1) + (x3**2 + y3**2) * (x2*y1 - x1*y2)

    if A == 0:
        return None, None  # Points are collinear

    # Center of the circle
    cx = -B / (2*A)
    cy = -C / (2*A)

    # Radius of the circle
    r = sqrt((cx - x1)**2 + (cy - y1)**2)

    return (cx, cy), r

def angle_between_vectors(v1, v2):
    """Calculates the angle between two vectors."""
    v1_u = v1 / np.linalg.norm(v1)
    v2_u = v2 / np.linalg.norm(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))

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
        # Circle properties (center coordinates, radius, start, end angle)
        self.circle_center = None
        self.circle_radius = None
        self.arc_start_angle = None
        self.arc_end_angle = None
        self.ramp_up_duration = 2.0  # Duration for velocity ramp-up in seconds
        self.ramp_down_distance = 0.5  # Distance from goal to start ramping down velocities

    def lowpass_filter(self, data):
        padlen = 3 * self.filter_order
        if len(data) <= padlen:
            return data
        y = filtfilt(self.b, self.a, data, padlen=padlen)
        return y

    # def pose_callback(self, msg):
    #     quat = msg.pose.pose.orientation
    #     if quat.w == 0.0 and quat.x == 0.0 and quat.y == 0.0 and quat.z == 0.0:
    #         rospy.logwarn("Invalid quaternion received, skipping pose update.")
    #         return

    #     try:
    #         euler = tf.transformations.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
    #         roll, pitch, yaw = euler[0], euler[1], euler[2]
    #     except Exception as e:
    #         rospy.logerr(f"Error converting quaternion to Euler: {e}")
    #         return

    #     self.x = msg.pose.pose.position.x
    #     self.y = msg.pose.pose.position.y
    #     self.theta = yaw
    #     self.current_pose = np.array([self.x, self.y, self.theta])
    #     self.trajectory_x.append(self.x)
    #     self.trajectory_y.append(self.y)

    #     # First waypoint is always current pose
    #     if len(self.waypoints_x) == 0:
    #         self.waypoints_x.append(self.x)
    #         self.waypoints_y.append(self.y)
    #     else:
    #         self.waypoints_x[0] = self.x
    #         self.waypoints_y[0] = self.y

    def pose_callback(self, msg):
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

        # First waypoint is always current pose
        if len(self.waypoints_x) == 0:
            self.waypoints_x.append(self.x)
            self.waypoints_y.append(self.y)
        else:
            self.waypoints_x[0] = self.x
            self.waypoints_y[0] = self.y

    def calculate_circle_parameters(self):
        """Calculates the center, radius, and start/end angles of the circle."""
        if len(self.waypoints_x) != 3:
            rospy.logwarn("Need exactly three waypoints to define a circular arc.")
            return False

        p1 = (self.waypoints_x[0], self.waypoints_y[0])
        p2 = (self.waypoints_x[1], self.waypoints_y[1])
        p3 = (self.waypoints_x[2], self.waypoints_y[2])

        circle_center, circle_radius = circle_from_3_points(p1, p2, p3)

        if circle_center is None or circle_radius is None:
            rospy.logerr("Could not calculate circle parameters. Points may be collinear.")
            return False

        self.circle_center = circle_center
        self.circle_radius = circle_radius

        # Calculate start and end angles
        cx, cy = self.circle_center
        self.arc_start_angle = arctan2(self.waypoints_y[0] - cy, self.waypoints_x[0] - cx)  # Start at robot pose
        self.arc_end_angle = arctan2(self.waypoints_y[2] - cy, self.waypoints_x[2] - cx)

        return True

    def find_closest_point_on_arc(self, x, y):
        """Finds the angle on the circular arc closest to the given point."""
        if self.circle_center is None or self.circle_radius is None:
            rospy.logwarn("Circle parameters not calculated.")
            return None

        cx, cy = self.circle_center
        dx = x - cx
        dy = y - cy
        angle = arctan2(dy, dx)

        # Ensure the angle is within the arc's range (consider direction)
        angle = self.clamp_angle(angle, self.arc_start_angle, self.arc_end_angle)

        return angle

    def clamp_angle(self, angle, start_angle, end_angle):
        """Clamps an angle to be within the range of start_angle and end_angle."""
        if start_angle < end_angle:
            return max(min(angle, end_angle), start_angle)
        else:  # end_angle < start_angle
            return max(min(angle, start_angle), end_angle)

    def mpc_control(self, x, y, theta):
        if self.circle_center is None or self.circle_radius is None:
            rospy.logwarn("Circle parameters are not defined. Cannot perform MPC control.")
            return 0.0, 0.0

        # Find the closest point on the arc (angle)
        closest_angle = self.find_closest_point_on_arc(x, y)

        if closest_angle is None:
            return 0.0, 0.0

        # Calculate the lookahead point along the arc
        lookahead_angle = closest_angle + self.lookahead_distance / self.circle_radius  # s = r*theta --> theta = s/r

        # Clamp lookahead angle to ensure it is not out of bound
        lookahead_angle = self.clamp_angle(lookahead_angle, self.arc_start_angle, self.arc_end_angle)

        # Convert the lookahead angle to x, y coordinates
        cx, cy = self.circle_center
        lookahead_x = cx + self.circle_radius * cos(lookahead_angle)
        lookahead_y = cy + self.circle_radius * sin(lookahead_angle)

        # Check if the goal is reached based on current parameters, not waypoints
        distance_to_end = sqrt((x - (cx + self.circle_radius * cos(self.arc_end_angle)))**2 +
                               (y - (cy + self.circle_radius * sin(self.arc_end_angle)))**2)

        if distance_to_end < self.distance_threshold:
            rospy.loginfo("Reached the final goal!")
            self.reached_goal = True
            return 0.0, 0.0

        # Calculate the desired heading angle (tangent to the circle at lookahead point)
        desired_heading = lookahead_angle + np.pi/2  # Tangent to the circle
        heading_error = desired_heading - theta
        heading_error = arctan2(sin(heading_error), cos(heading_error))  # Normalize to [-pi, pi]

        # Calculate position error
        x_error = lookahead_x - x
        y_error = lookahead_y - y
        distance_error = sqrt(x_error**2 + y_error**2)

        # Control logic
        heading_threshold = 0.1
        linear_speed_kp = 1.8
        angular_speed_kp = 1.8

        if abs(heading_error) > heading_threshold:
            v = 0.0
            omega = angular_speed_kp * heading_error
        else:
            v = linear_speed_kp * distance_error
            omega = angular_speed_kp * heading_error

        # Apply velocity ramp-up
        if self.start_time is not None:
            current_time = rospy.Time.now().to_sec()
            elapsed_time = current_time - self.start_time
            if elapsed_time < self.ramp_up_duration:
                ramp_factor = elapsed_time / self.ramp_up_duration
                v *= ramp_factor
                omega *= ramp_factor

        # Apply velocity ramp-down when close to goal
        if distance_to_end < self.ramp_down_distance:
            ramp_down_factor = distance_to_end / self.ramp_down_distance
            v *= ramp_down_factor
            omega *= ramp_down_factor

        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

        # Calculate acceleration
        if self.start_time is not None:
            current_time = rospy.Time.now().to_sec()
            dt = current_time - self.start_time

            linear_acceleration = (v - self.last_v) / dt if dt > 0 else 0.0
            angular_acceleration = (omega - self.last_omega) / dt if dt > 0 else 0.0

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
        master.title("MiR100 Arc Tracking")

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

        # Tab control
        self.tabControl = ttk.Notebook(master)

        self.trajectory_tab = tk.Frame(self.tabControl)
        self.velocity_tab = tk.Frame(self.tabControl)
        self.acceleration_tab = tk.Frame(self.tabControl)

        self.tabControl.add(self.trajectory_tab, text='Trajectory')
        self.tabControl.add(self.velocity_tab, text='Velocity')
        self.tabControl.add(self.acceleration_tab, text='Acceleration')
        self.tabControl.grid(row=2, column=0, columnspan=3)

        # Trajectory Tab
        self.fig_trajectory, self.ax_trajectory = plt.subplots()
        # Load the map image and metadata
        map_img = plt.imread("static/map_image.png")
        map_metadata = {"width": 357, "height": 332, "resolution": 0.05000000074505806,
                        "origin_x": 0.0, "origin_y": 0.0}

        # Calculate the extent of the image in world coordinates
        extent = [
            map_metadata["origin_x"],  # Left edge (x_min)
            map_metadata["origin_x"] + map_metadata["width"] * map_metadata["resolution"],  # Right edge (x_max)
            map_metadata["origin_y"],  # Bottom edge (y_min)
            map_metadata["origin_y"] + map_metadata["height"] * map_metadata["resolution"]  # Top edge (y_max)
        ]

        # Display the map image as the background
        self.ax_trajectory.imshow(map_img, extent=extent, aspect='equal', zorder=0)  # zorder=0 puts it behind other plots

        # Set initial axis limits to match the map
        self.ax_trajectory.set_xlim([extent[0], extent[1]])
        self.ax_trajectory.set_ylim([extent[2], extent[3]])
        self.ax_trajectory.set_xlabel("X (m)")
        self.ax_trajectory.set_ylabel("Y (m)")
        self.ax_trajectory.set_title("Robot Trajectory")
        self.line, = self.ax_trajectory.plot([], [], label="Robot Path", zorder=2)
        self.waypoints_plot, = self.ax_trajectory.plot([], [], 'bo', label="Waypoints", zorder=3)
        self.robot_plot, = self.ax_trajectory.plot([], [], 'go', label="Robot", markersize=10, zorder=4)
        self.arc_plot, = self.ax_trajectory.plot([], [], 'g-', label="Arc", linewidth=2, zorder=2)
        self.lookahead_plot, = self.ax_trajectory.plot([], [], 'yo', label="Lookahead Point", markersize=5, zorder=3)
        self.ax_trajectory.legend()

        self.canvas_trajectory = FigureCanvasTkAgg(self.fig_trajectory, master=self.trajectory_tab)
        self.canvas_trajectory.draw()
        self.canvas_trajectory.get_tk_widget().grid(row=0, column=0, columnspan=3)

        self.fig_trajectory.canvas.mpl_connect('button_press_event', self.onclick)

        # Velocity Tab
        self.fig_velocity, self.ax_velocity = plt.subplots()
        self.ax_velocity.set_xlabel("Time (s)")
        self.ax_velocity.set_ylabel("Velocity (m/s, rad/s)")
        self.ax_velocity.set_title("Robot Velocity")
        self.line_linear_velocity, = self.ax_velocity.plot([], [], label="Linear Velocity")
        self.line_angular_velocity, = self.ax_velocity.plot([], [], label="Angular Velocity")
        self.ax_velocity.legend()

        self.canvas_velocity = FigureCanvasTkAgg(self.fig_velocity, master=self.velocity_tab)
        self.canvas_velocity.draw()
        self.canvas_velocity.get_tk_widget().grid(row=0, column=0, columnspan=3)

        # Acceleration Tab
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
        if event.xdata is not None and event.ydata is not None:
            x = event.xdata
            y = event.ydata

            if len(self.mpc_controller.waypoints_x) < 3:
                self.mpc_controller.waypoints_x.append(x)
                self.mpc_controller.waypoints_y.append(y)
            self.update_waypoint_plot()
            print(f"Clicked at x={x}, y={y}")

    def start_control_loop(self):
        if len(self.mpc_controller.waypoints_x) != 3:
            self.result_label.config(text="Error: Need exactly three waypoints.")
            return

        if not self.mpc_controller.calculate_circle_parameters():
            self.result_label.config(text="Error: Could not calculate arc parameters.")
            return

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.DISABLED)

        self.mpc_controller.trajectory_x = []
        self.mpc_controller.trajectory_y = []
        self.mpc_controller.reached_goal = False

        # Reset velocity and acceleration data
        self.mpc_controller.velocity_data = []
        self.mpc_controller.angular_velocity_data = []
        self.mpc_controller.acceleration_data = []
        self.mpc_controller.angular_acceleration_data = []
        self.mpc_controller.time_data = []
        self.mpc_controller.start_time = rospy.Time.now().to_sec()

        self.control_loop_running = True

        self.update_plot()

    def stop_control_loop(self):
        self.control_loop_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.NORMAL)
        self.send_command(0.0, 0.0)

    def clear_waypoints(self):
        self.mpc_controller.waypoints_x = []
        self.mpc_controller.waypoints_y = []
        self.mpc_controller.circle_center = None
        self.mpc_controller.circle_radius = None
        self.arc_start_angle = None
        self.arc_end_angle = None
        self.waypoints_plot.set_data([], [])
        self.arc_plot.set_data([], [])
        self.line.set_data([], [])
        self.robot_plot.set_data([], [])
        self.lookahead_plot.set_data([], [])
        self.ax_trajectory.relim()
        self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()

    def update_waypoint_plot(self):
        self.waypoints_plot.set_data(self.mpc_controller.waypoints_x, self.mpc_controller.waypoints_y)
        self.ax_trajectory.relim()
        self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()

    def update_plot(self):
        if not self.control_loop_running:
            return

        if self.mpc_controller.current_pose is None:
            self.result_label.config(text="Waiting for initial pose from /robot_pose...")
            self.master.after(10, self.update_plot)
            return

        x = self.mpc_controller.x
        y = self.mpc_controller.y
        theta = self.mpc_controller.theta

        v, omega = self.mpc_controller.mpc_control(x, y, theta)
        self.send_command(v, omega)

        # Trajectory Tab
        self.line.set_data(self.mpc_controller.trajectory_x, self.mpc_controller.trajectory_y)
        self.robot_plot.set_data([x], [y])

        if self.mpc_controller.circle_center is not None and self.mpc_controller.circle_radius is not None:
            # Plot the arc
            cx, cy = self.mpc_controller.circle_center
            theta_arc = np.linspace(self.mpc_controller.arc_start_angle, self.mpc_controller.arc_end_angle, 100)
            x_arc = cx + self.mpc_controller.circle_radius * np.cos(theta_arc)
            y_arc = cy + self.mpc_controller.circle_radius * np.sin(theta_arc)
            self.arc_plot.set_data(x_arc, y_arc)

            # Plot the lookahead point
            closest_angle = self.mpc_controller.find_closest_point_on_arc(x, y)
            if closest_angle is not None:
                lookahead_angle = closest_angle + self.mpc_controller.lookahead_distance / self.mpc_controller.circle_radius
                lookahead_angle = self.mpc_controller.clamp_angle(lookahead_angle, self.mpc_controller.arc_start_angle, self.mpc_controller.arc_end_angle)
                lookahead_x = cx + self.mpc_controller.circle_radius * np.cos(lookahead_angle)
                lookahead_y = cy + self.mpc_controller.circle_radius * np.sin(lookahead_angle)
                self.lookahead_plot.set_data([lookahead_x], [lookahead_y])

        self.update_waypoint_plot()
        self.ax_trajectory.relim()
        self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()

        # Velocity Tab
        filtered_velocity_data = self.mpc_controller.lowpass_filter(self.mpc_controller.velocity_data)
        filtered_angular_velocity_data = self.mpc_controller.lowpass_filter(self.mpc_controller.angular_velocity_data)

        self.line_linear_velocity.set_data(self.mpc_controller.time_data, filtered_velocity_data)
        self.line_angular_velocity.set_data(self.mpc_controller.time_data, filtered_angular_velocity_data)
        self.ax_velocity.relim()
        self.ax_velocity.autoscale_view()
        self.canvas_velocity.draw_idle()

        # Acceleration Tab
        self.line_linear_acceleration.set_data(self.mpc_controller.time_data, self.mpc_controller.acceleration_data)
        self.line_angular_acceleration.set_data(self.mpc_controller.time_data, self.mpc_controller.angular_acceleration_data)
        self.ax_acceleration.relim()
        self.ax_acceleration.autoscale_view()
        self.canvas_acceleration.draw_idle()

        self.master.update()

        if not self.mpc_controller.reached_goal:
            self.master.after(10, self.update_plot)
        else:
            self.stop_control_loop()

    def send_command(self, v, omega):
        twist_msg = Twist()
        twist_msg.linear.x = v
        twist_msg.angular.z = omega
        self.cmd_vel_pub.publish(twist_msg)
        print(f"Published to /cmd_vel: linear.x = {v:.6f}, angular.z = {omega:.6f}")

def ros_spin():
    rospy.spin()

if __name__ == '__main__':
    rospy.init_node('arc_tracking_node')

    dt = 0.1
    v_max = 1.0
    v_min = -1.0
    omega_max = 1.5
    omega_min = -1.5
    lookahead_distance = 0.2

    controller = MPCController(dt, v_max, v_min, omega_max, omega_min, lookahead_distance)

    # rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, controller.pose_callback)
    rospy.Subscriber('/robot_pose', Pose, controller.pose_callback)

    root = tk.Tk()
    gui = GUI(root, controller)

    threading.Thread(target=ros_spin, daemon=True).start()

    root.mainloop()