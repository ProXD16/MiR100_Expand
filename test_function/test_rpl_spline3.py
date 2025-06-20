#!/usr/bin/env python3

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
from scipy.interpolate import CubicSpline
from scipy.signal import butter, filtfilt
import onnxruntime as ort
import os

class MPCController:
    def __init__(self, dt, v_max, v_min, omega_max, omega_min, lookahead_distance=0.15, filter_order=4, cutoff_frequency=4.0):
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
        self.spline_x = None
        self.spline_y = None
        self.spline_derivative_x = None
        self.spline_derivative_y = None
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
        self.cross_track_error_data = []
        self.heading_error_data = []
        self.start_time = None
        self.filter_order = filter_order
        self.cutoff_frequency = cutoff_frequency
        self.b, self.a = butter(self.filter_order, self.cutoff_frequency / (1 / (2 * self.dt)), btype='low', analog=False)
        self.ramp_up_duration = 2.0
        self.ramp_down_distance = 0.5
        self.velocity_smoothing_alpha = 0.3
        self.rate = rospy.Rate(100)  # 100 Hz, khớp với dt=0.01

        # Tải mô hình SAC
        self.sac_model_path = "sac_model.onnx"
        if not os.path.exists(self.sac_model_path):
            rospy.logerr(f"Không tìm thấy {self.sac_model_path}")
            raise FileNotFoundError(f"Yêu cầu {self.sac_model_path}")
        self.sac_session = ort.InferenceSession(self.sac_model_path)

    def lowpass_filter(self, data):
        padlen = 3 * self.filter_order
        if len(data) <= padlen:
            return data
        y = filtfilt(self.b, self.a, data, padlen=padlen)
        return y

    def smooth_velocity(self, new_v, new_omega):
        smoothed_v = (1 - self.velocity_smoothing_alpha) * self.last_v + self.velocity_smoothing_alpha * new_v
        smoothed_omega = (1 - self.velocity_smoothing_alpha) * self.last_omega + self.velocity_smoothing_alpha * new_omega
        return smoothed_v, smoothed_omega

    def smooth_ramp_factor(self, factor):
        return np.sin(factor * np.pi / 2)

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

        if len(self.waypoints_x) == 0:
            self.waypoints_x.append(self.x)
            self.waypoints_y.append(self.y)
        else:
            self.waypoints_x[0] = self.x
            self.waypoints_y[0] = self.y

    def calculate_spline(self):
        if len(self.waypoints_x) < 2:
            rospy.logwarn("Need at least two waypoints to create a spline.")
            return False

        waypoints_x = np.array(self.waypoints_x)
        waypoints_y = np.array(self.waypoints_y)

        distances = np.sqrt(np.diff(waypoints_x)**2 + np.diff(waypoints_y)**2)
        arc_length = np.concatenate(([0], np.cumsum(distances)))
        t = arc_length / arc_length[-1]

        try:
            self.spline_x = CubicSpline(t, waypoints_x)
            self.spline_y = CubicSpline(t, waypoints_y)
            self.spline_derivative_x = self.spline_x.derivative()
            self.spline_derivative_y = self.spline_y.derivative()
            self.total_arc_length = arc_length[-1]
            return True
        except Exception as e:
            rospy.logerr(f"Error creating spline: {e}")
            return False

    def find_closest_point_on_spline(self, x, y):
        t = np.linspace(0, 1, num=1000)
        spline_x = self.spline_x(t)
        spline_y = self.spline_y(t)
        distances = np.sqrt((spline_x - x)**2 + (spline_y - y)**2)
        closest_idx = np.argmin(distances)
        return t[closest_idx]

    def compute_lookahead_t(self, closest_t):
        t = np.linspace(0, 1, num=1000)
        spline_x = self.spline_x(t)
        spline_y = self.spline_y(t)
        arc_lengths = np.cumsum(np.sqrt(np.diff(spline_x, prepend=spline_x[0])**2 + np.diff(spline_y, prepend=spline_y[0])**2))
        arc_lengths = arc_lengths / arc_lengths[-1] * self.total_arc_length

        closest_idx = np.argmin(np.abs(t - closest_t))
        current_arc_length = arc_lengths[closest_idx]

        target_arc_length = current_arc_length + self.lookahead_distance
        if target_arc_length > self.total_arc_length:
            return 1.0

        lookahead_idx = np.argmin(np.abs(arc_lengths - target_arc_length))
        return t[lookahead_idx]

    def compute_sac_velocity(self, observation):
        # Thêm batch dimension để input có shape [1, 5]
        observation = observation.reshape(1, -1).astype(np.float32)
        inputs = {self.sac_session.get_inputs()[0].name: observation}
        action = self.sac_session.run(None, inputs)[0]
        # Trích xuất giá trị đơn từ action
        action_scalar = float(action[0][0])  # Chuyển ndarray thành float
        scaling_factor = 2.2  # Hệ số tỷ lệ từ bài báo
        k = (self.v_max - self.v_min) / 2
        b = (self.v_max + self.v_min) / 2
        v = scaling_factor * (k * action_scalar + b)
        v = np.clip(v, self.v_min, self.v_max)
        return v

    def mpc_control(self, x, y, theta):
        if self.spline_x is None or self.spline_y is None:
            rospy.logwarn("Spline is not defined. Cannot perform MPC control.")
            return 0.0, 0.0

        closest_t = self.find_closest_point_on_spline(x, y)
        lookahead_t = self.compute_lookahead_t(closest_t)

        final_goal_x = self.waypoints_x[-1]
        final_goal_y = self.waypoints_y[-1]
        distance_to_final_goal = np.sqrt((x - final_goal_x)**2 + (y - final_goal_y)**2)
        if distance_to_final_goal < self.distance_threshold:
            rospy.loginfo("Reached the final goal!")
            self.reached_goal = True
            return 0.0, 0.0

        # Tính lỗi theo dõi đường (cross-track error)
        dx = x - self.spline_x(closest_t)
        dy = y - self.spline_y(closest_t)
        tangent_x = self.spline_derivative_x(closest_t)
        tangent_y = self.spline_derivative_y(closest_t)
        norm_tangent = np.sqrt(tangent_x**2 + tangent_y**2)
        e_p = (dx * tangent_y - dy * tangent_x) / norm_tangent if norm_tangent != 0 else 0.0

        # Tính lỗi góc (heading error)
        angle_to_path = np.arctan2(tangent_y, tangent_x)
        psi_e = angle_to_path - theta
        psi_e = np.arctan2(np.sin(psi_e), np.cos(psi_e))

        # Tính lỗi góc tại điểm nhìn trước
        lookahead_angle = np.arctan2(self.spline_derivative_y(lookahead_t), self.spline_derivative_x(lookahead_t))
        psi_e2 = lookahead_angle - theta
        psi_e2 = np.arctan2(np.sin(psi_e2), np.cos(psi_e2))

        # Lưu dữ liệu lỗi
        self.cross_track_error_data.append(e_p)
        self.heading_error_data.append(psi_e)

        # Tính vận tốc từ SAC
        observation = np.array([e_p, psi_e, self.last_v, self.last_omega, psi_e2], dtype=np.float32)
        v = self.compute_sac_velocity(observation)

        # Tính vận tốc góc từ MPC
        heading_threshold = 0.1
        angular_speed_kp = 1.5
        if abs(psi_e) > heading_threshold:
            omega = angular_speed_kp * psi_e
        else:
            omega = angular_speed_kp * psi_e

        v, omega = self.smooth_velocity(v, omega)

        # Áp dụng ramp-up và ramp-down
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

        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

        # Lưu dữ liệu cho GUI
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
        master.title("MiR100 Spline Tracking")
        self.mpc_controller = mpc_controller

        # Kiểm tra bản đồ
        map_path = "static/map_image.png"
        if not os.path.exists(map_path):
            raise FileNotFoundError(f"Không tìm thấy {map_path}")

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
        self.error_tab = tk.Frame(self.tabControl)
        self.tabControl.add(self.trajectory_tab, text='Trajectory')
        self.tabControl.add(self.velocity_tab, text='Velocity')
        self.tabControl.add(self.acceleration_tab, text='Acceleration')
        self.tabControl.add(self.error_tab, text='Errors')
        self.tabControl.grid(row=2, column=0, columnspan=3)

        self.fig_trajectory, self.ax_trajectory = plt.subplots()
        map_img = plt.imread(map_path)
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
        self.line_linear_velocity, = self.ax_velocity.plot([], [], label="Linear Velocity")
        self.line_angular_velocity, = self.ax_velocity.plot([], [], label="Angular Velocity")
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

        self.fig_error, self.ax_error = plt.subplots()
        self.ax_error.set_xlabel("Time (s)")
        self.ax_error.set_ylabel("Error (m, rad)")
        self.ax_error.set_title("Tracking Errors")
        self.line_cross_track_error, = self.ax_error.plot([], [], label="Cross-Track Error")
        self.line_heading_error, = self.ax_error.plot([], [], label="Heading Error")
        self.ax_error.legend()
        self.canvas_error = FigureCanvasTkAgg(self.fig_error, master=self.error_tab)
        self.canvas_error.draw()
        self.canvas_error.get_tk_widget().grid(row=0, column=0, columnspan=3)

    def onclick(self, event):
        if event.xdata is not None and event.ydata is not None:
            x = event.xdata
            y = event.ydata
            if len(self.mpc_controller.waypoints_x) >= 1:
                self.mpc_controller.waypoints_x.append(x)
                self.mpc_controller.waypoints_y.append(y)
            self.update_waypoint_plot()
            print(f"Clicked at x={x}, y={y}")

    def start_control_loop(self):
        if not self.mpc_controller.calculate_spline():
            self.result_label.config(text="Error: Could not create spline. Add more waypoints.")
            return

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.DISABLED)
        self.mpc_controller.trajectory_x = []
        self.mpc_controller.trajectory_y = []
        self.mpc_controller.reached_goal = False
        self.mpc_controller.last_v = 0.0
        self.mpc_controller.last_omega = 0.0
        self.mpc_controller.velocity_data = []
        self.mpc_controller.angular_velocity_data = []
        self.mpc_controller.acceleration_data = []
        self.mpc_controller.angular_acceleration_data = []
        self.mpc_controller.time_data = []
        self.mpc_controller.cross_track_error_data = []
        self.mpc_controller.heading_error_data = []
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
        self.mpc_controller.spline_x = None
        self.mpc_controller.spline_y = None
        self.mpc_controller.spline_derivative_x = None
        self.spline_derivative_y = None
        self.waypoints_plot.set_data([], [])
        self.spline_plot.set_data([], [])
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
            self.result_label.config(text="Waiting for initial pose from /amcl_pose...")
            self.master.after(10, self.update_plot)
            return

        x = self.mpc_controller.x
        y = self.mpc_controller.y
        theta = self.mpc_controller.theta

        v, omega = self.mpc_controller.mpc_control(x, y, theta)
        self.send_command(v, omega)

        self.line.set_data(self.mpc_controller.trajectory_x, self.mpc_controller.trajectory_y)
        self.robot_plot.set_data([x], [y])

        if self.mpc_controller.spline_x is not None and self.mpc_controller.spline_y is not None:
            t_spline = np.linspace(0, 1, 1000)
            x_spline = self.mpc_controller.spline_x(t_spline)
            y_spline = self.mpc_controller.spline_y(t_spline)
            self.spline_plot.set_data(x_spline, y_spline)

            closest_t = self.mpc_controller.find_closest_point_on_spline(x, y)
            lookahead_t = self.mpc_controller.compute_lookahead_t(closest_t)
            lookahead_x = self.mpc_controller.spline_x(lookahead_t)
            lookahead_y = self.mpc_controller.spline_y(lookahead_t)
            self.lookahead_plot.set_data([lookahead_x], [lookahead_y])

        self.update_waypoint_plot()
        self.ax_trajectory.relim()
        self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()

        filtered_velocity_data = self.mpc_controller.lowpass_filter(self.mpc_controller.velocity_data)
        filtered_angular_velocity_data = self.mpc_controller.lowpass_filter(self.mpc_controller.angular_velocity_data)
        self.line_linear_velocity.set_data(self.mpc_controller.time_data, filtered_velocity_data)
        self.line_angular_velocity.set_data(self.mpc_controller.time_data, filtered_angular_velocity_data)
        self.ax_velocity.relim()
        self.ax_velocity.autoscale_view()
        self.canvas_velocity.draw_idle()

        self.line_linear_acceleration.set_data(self.mpc_controller.time_data, self.mpc_controller.acceleration_data)
        self.line_angular_acceleration.set_data(self.mpc_controller.time_data, self.mpc_controller.angular_acceleration_data)
        self.ax_acceleration.relim()
        self.ax_acceleration.autoscale_view()
        self.canvas_acceleration.draw_idle()

        self.line_cross_track_error.set_data(self.mpc_controller.time_data, self.mpc_controller.cross_track_error_data)
        self.line_heading_error.set_data(self.mpc_controller.time_data, self.mpc_controller.heading_error_data)
        self.ax_error.relim()
        self.ax_error.autoscale_view()
        self.canvas_error.draw_idle()

        self.master.update()

        if not self.mpc_controller.reached_goal:
            self.mpc_controller.rate.sleep()
            self.master.after(10, self.update_plot)
        else:
            self.stop_control_loop()

    def send_command(self, v, omega):
        twist_msg = Twist()
        # Đảm bảo v và omega là float
        v = float(v) if isinstance(v, np.ndarray) else v
        omega = float(omega) if isinstance(omega, np.ndarray) else omega
        twist_msg.linear.x = v
        twist_msg.angular.z = omega
        self.cmd_vel_pub.publish(twist_msg)
        print(f"Published to /cmd_vel: linear.x = {v:.6f}, angular.z = {omega:.6f}")

def ros_spin():
    rospy.spin()

if __name__ == '__main__':
    try:
        rospy.init_node('spline_tracking_node')
        dt = 0.01
        v_max = 0.4
        v_min = -0.4
        omega_max = 0.4
        omega_min = -0.4
        lookahead_distance = 0.15

        controller = MPCController(dt, v_max, v_min, omega_max, omega_min, lookahead_distance)
        rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, controller.pose_callback)
        root = tk.Tk()
        gui = GUI(root, controller)
        threading.Thread(target=ros_spin, daemon=True).start()
        root.mainloop()
    except Exception as e:
        rospy.logerr(f"Lỗi khi chạy node: {e}")
        raise