import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
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

class MPCController:
    def __init__(self, dt, v_max, v_min, omega_max, omega_min, filter_order=3, cutoff_frequency=2.0):
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
        self.gui = None  # Reference to the GUI
        self.filter_order = filter_order
        self.cutoff_frequency = cutoff_frequency
        self.b, self.a = butter(self.filter_order, self.cutoff_frequency / (1 / (2 * self.dt)), btype='low', analog=False)
        self.velocity_data = []
        self.angular_velocity_data = []
        self.acceleration_data = []
        self.angular_acceleration_data = []
        self.time_data = []
        self.start_time = None
        self.last_v = 0.0  # Store previous linear velocity
        self.last_omega = 0.0  # Store previous angular velocity

    def lowpass_filter(self, data):
        padlen = 3 * self.filter_order
        if len(data) <= padlen:  # Need enough data points for padding
            return data
        y = filtfilt(self.b, self.a, data, padlen=padlen)  # Add padlen parameter
        return y

    def pose_callback(self, msg):
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

        # Update plot directly from pose_callback (FASTEST)
        if self.gui and hasattr(self.gui, 'control_loop_running') and self.gui.control_loop_running:
            self.gui.master.after(0, self.gui.update_plot_from_callback)

    def mpc_control(self, x, y, theta, x_goal, y_goal):
        x_error = x_goal - x
        y_error = y_goal - y
        distance_to_goal = np.sqrt(x_error**2 + y_error**2)
        angle_to_goal = np.arctan2(y_error, x_error)
        heading_error = angle_to_goal - theta
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))

        heading_threshold = 0.5
        linear_speed_kp = 0.3
        angular_speed_kp = 0.5

        if abs(heading_error) > heading_threshold:
            v = 0.0
            omega = angular_speed_kp * heading_error
        else:
            v = linear_speed_kp * distance_to_goal
            omega = angular_speed_kp * heading_error

        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

        # Calculate accelerations
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
        master.title("MiR100 MPC Control")

        self.mpc_controller = mpc_controller

        self.label_x = tk.Label(master, text="X Goal:")
        self.label_y = tk.Label(master, text="Y Goal:")
        self.entry_x = tk.Entry(master)
        self.entry_y = tk.Entry(master)

        self.label_x.grid(row=0, column=0)
        self.entry_x.grid(row=0, column=1)
        self.label_y.grid(row=1, column=0)
        self.entry_y.grid(row=0, column=3)

        self.start_button = tk.Button(master, text="Start", command=self.start_control_loop)
        self.start_button.grid(row=2, column=0)
        self.stop_button = tk.Button(master, text="Stop", command=self.stop_control_loop, state=tk.DISABLED)
        self.stop_button.grid(row=2, column=1)

        self.result_label = tk.Label(master, text="")
        self.result_label.grid(row=3, column=0, columnspan=2)

        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

        self.control_loop_running = False
        self.goal_x = 0.0
        self.goal_y = 0.0
        self.distance_threshold = 0.1

        # Notebook (Tabbed Interface)
        self.tabControl = ttk.Notebook(master)
        self.trajectory_tab = ttk.Frame(self.tabControl)
        self.velocity_tab = ttk.Frame(self.tabControl)
        self.acceleration_tab = ttk.Frame(self.tabControl)

        self.tabControl.add(self.trajectory_tab, text="Trajectory")
        self.tabControl.add(self.velocity_tab, text="Velocity")
        self.tabControl.add(self.acceleration_tab, text="Acceleration")
        self.tabControl.grid(row=4, column=0, columnspan=2)

        # Trajectory Tab
        self.fig_trajectory, self.ax_trajectory = plt.subplots()
        self.ax_trajectory.set_xlim([0, 20])  # Adjust limits as needed
        self.ax_trajectory.set_ylim([0, 20])
        self.ax_trajectory.set_xlabel("X (m)")
        self.ax_trajectory.set_ylabel("Y (m)")
        self.ax_trajectory.set_title("Robot Trajectory")
        self.line, = self.ax_trajectory.plot([], [], label="Robot Path")
        self.goal_marker, = self.ax_trajectory.plot([], [], 'ro', label="Goal")
        self.ax_trajectory.legend()

        self.canvas_trajectory = FigureCanvasTkAgg(self.fig_trajectory, master=self.trajectory_tab)
        self.canvas_trajectory.draw()
        self.canvas_trajectory.get_tk_widget().grid(row=0, column=0, columnspan=2)

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
        self.canvas_velocity.get_tk_widget().grid(row=0, column=0, columnspan=2)

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
        self.canvas_acceleration.get_tk_widget().grid(row=0, column=0, columnspan=2)

    def start_control_loop(self):
        try:
            self.goal_x = float(self.entry_x.get())
            self.goal_y = float(self.entry_y.get())
        except ValueError:
            self.result_label.config(text="Lỗi: Vui lòng nhập giá trị số hợp lệ cho tọa độ mục tiêu")
            return

        self.entry_x.config(state=tk.DISABLED)
        self.entry_y.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        self.mpc_controller.trajectory_x = []
        self.mpc_controller.trajectory_y = []
        # Reset velocity and acceleration data
        self.mpc_controller.velocity_data = []
        self.mpc_controller.angular_velocity_data = []
        self.mpc_controller.acceleration_data = []
        self.mpc_controller.angular_acceleration_data = []
        self.mpc_controller.time_data = []
        self.mpc_controller.start_time = rospy.Time.now().to_sec()

        self.control_loop_running = True

        self.goal_marker.set_data([self.goal_x], [self.goal_y])
        self.update_plot()

    def stop_control_loop(self):
        self.control_loop_running = False
        self.entry_x.config(state=tk.NORMAL)
        self.entry_y.config(state=tk.NORMAL)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.send_command(0.0, 0.0)
        self.update_plot()

    def update_plot(self):
        if not self.control_loop_running:
            return

        if self.mpc_controller.current_pose is None:
            self.result_label.config(text="Waiting for initial pose from /amcl_pose...")
            self.master.after(50, self.update_plot)
            return

        x = self.mpc_controller.x
        y = self.mpc_controller.y
        theta = self.mpc_controller.theta

        v, omega = self.mpc_controller.mpc_control(x, y, theta, self.goal_x, self.goal_y)
        self.send_command(v, omega)

        distance_to_goal = np.sqrt((self.goal_x - x)**2 + (self.goal_y - y)**2)

        # Update Trajectory Tab
        self.line.set_data(self.mpc_controller.trajectory_x, self.mpc_controller.trajectory_y)
        self.ax_trajectory.relim()  # Recalculate limits
        self.ax_trajectory.autoscale_view()  # Autoscale
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

        if distance_to_goal < self.distance_threshold:
            self.result_label.config(text="Đã đến mục tiêu!")
            self.send_command(0.0, 0.0)
            self.stop_control_loop()
            return

        self.master.after(50, self.update_plot)

    def send_command(self, v, omega):
        twist_msg = Twist()
        twist_msg.linear.x = v
        twist_msg.angular.z = omega
        self.cmd_vel_pub.publish(twist_msg)
        print(f"Published to /cmd_vel: linear.x = {v:.6f}, angular.z = {omega:.6f}")

def ros_spin():
    rospy.spin()

if __name__ == '__main__':
    rospy.init_node('mpc_controller_node')

    dt = 0.1
    v_max = 1
    v_min = -1
    omega_max = 0.8
    omega_min = -0.8

    controller = MPCController(dt, v_max, v_min, omega_max, omega_min)

    rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, controller.pose_callback)

    root = tk.Tk()
    gui = GUI(root, controller)

    threading.Thread(target=ros_spin, daemon=True).start()
    root.mainloop()