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
import onnxruntime as ort
import os

class PurePursuitController:
    def __init__(self, dt=0.05, v_max=0.4, v_min=-0.4, omega_max=1.0, omega_min=-1.0, 
                 wheelbase=0.172, lookahead_distance=0.2):
        self.dt = dt  # 0.05s for 20 Hz, matches paper
        self.v_max = v_max  # 0.4 m/s from paper
        self.v_min = v_min  # -0.4 m/s for symmetry
        self.omega_max = omega_max  # 1.0 rad/s from paper
        self.omega_min = omega_min  # -1.0 rad/s for symmetry
        self.wheelbase = wheelbase  # 0.172 m from paper
        self.lookahead_distance = lookahead_distance  # 0.2 m from paper
        self.current_pose = None
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.current_v = 0.0  # Current linear velocity
        self.current_omega = 0.0  # Current angular velocity
        self.trajectory_x = []
        self.trajectory_y = []
        self.spline_x = None
        self.spline_y = None
        self.spline_derivative_x = None
        self.spline_derivative_y = None
        self.waypoints_x = []
        self.waypoints_y = []
        self.distance_threshold = 0.2  # Consistent with paper
        self.reached_goal = False
        self.velocity_data = []
        self.angular_velocity_data = []
        self.time_data = []
        self.cross_track_error_data = []
        self.heading_error_data = []
        self.start_time = None
        self.rate = rospy.Rate(20)  # 20 Hz to match paper

        # Load SAC model
        self.sac_model_path = "sac_model.onnx"
        if not os.path.exists(self.sac_model_path):
            rospy.logerr(f"Could not find {self.sac_model_path}")
            raise FileNotFoundError(f"Required {self.sac_model_path}")
        self.sac_session = ort.InferenceSession(self.sac_model_path)

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
        arc_lengths = np.cumsum(np.sqrt(np.diff(spline_x, prepend=spline_x[0])**2 + 
                                       np.diff(spline_y, prepend=spline_y[0])**2))
        arc_lengths = arc_lengths / arc_lengths[-1] * self.total_arc_length

        closest_idx = np.argmin(np.abs(t - closest_t))
        current_arc_length = arc_lengths[closest_idx]

        target_arc_length = current_arc_length + self.lookahead_distance
        if target_arc_length > self.total_arc_length:
            return 1.0

        lookahead_idx = np.argmin(np.abs(arc_lengths - target_arc_length))
        return t[lookahead_idx]

    def compute_sac_velocity_rate(self, observation):
        observation = observation.reshape(1, -1).astype(np.float32)
        inputs = {self.sac_session.get_inputs()[0].name: observation}
        action = self.sac_session.run(None, inputs)[0]
        action_scalar = float(action[0][0])
        # Scale action to velocity rate [-0.5, 0.3] m/s^2
        dv_min, dv_max = -0.5, 0.3
        k = (dv_max - dv_min) / 2
        b = (dv_max + dv_min) / 2
        dv = k * action_scalar + b
        dv = np.clip(dv, dv_min, dv_max)
        # Apply experimental scaling factor
        dv *= 2.2
        return dv

    def enforce_wheelbase_constraint(self, v, omega):
        # Constraint: v + (b/2) * |ω| <= v_max
        wheelbase_term = (self.wheelbase / 2) * abs(omega)
        if v + wheelbase_term > self.v_max:
            # Scale v to satisfy constraint
            v = self.v_max - wheelbase_term
            v = np.clip(v, self.v_min, self.v_max)
        return v, omega

    def pure_pursuit_control(self, x, y, theta):
        if self.spline_x is None or self.spline_y is None:
            rospy.logwarn("Spline is not defined. Cannot perform Pure Pursuit control.")
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

        # Compute cross-track error
        dx = x - self.spline_x(closest_t)
        dy = y - self.spline_y(closest_t)
        tangent_x = self.spline_derivative_x(closest_t)
        tangent_y = self.spline_derivative_y(closest_t)
        norm_tangent = np.sqrt(tangent_x**2 + tangent_y**2)
        e_p = (dx * tangent_y - dy * tangent_x) / norm_tangent if norm_tangent != 0 else 0.0

        # Compute heading error
        angle_to_path = np.arctan2(tangent_y, tangent_x)
        psi_e = angle_to_path - theta
        psi_e = np.arctan2(np.sin(psi_e), np.cos(psi_e))

        # Compute lookahead heading error
        lookahead_angle = np.arctan2(self.spline_derivative_y(lookahead_t), 
                                    self.spline_derivative_x(lookahead_t))
        psi_e2 = lookahead_angle - theta
        psi_e2 = np.arctan2(np.sin(psi_e2), np.cos(psi_e2))

        # Store error data
        self.cross_track_error_data.append(e_p)
        self.heading_error_data.append(psi_e)

        # Compute velocity rate using SAC
        observation = np.array([e_p, psi_e, self.current_v, self.current_omega, psi_e2], 
                             dtype=np.float32)
        dv = self.compute_sac_velocity_rate(observation)

        # Integrate velocity rate to get new velocity
        v = self.current_v + dv * self.dt
        v = np.clip(v, self.v_min, self.v_max)

        # Pure Pursuit: Compute angular velocity
        x_lookahead = self.spline_x(lookahead_t)
        y_lookahead = self.spline_y(lookahead_t)
        alpha = np.arctan2(y_lookahead - y, x_lookahead - x) - theta
        alpha = np.arctan2(np.sin(alpha), np.cos(alpha))
        L = np.sqrt((x_lookahead - x)**2 + (y_lookahead - y)**2)
        if L < 1e-3:
            omega = 0.0
        else:
            omega = (2 * v * np.sin(alpha)) / L
        omega = np.clip(omega, self.omega_min, self.omega_max)

        # Enforce wheelbase constraint
        v, omega = self.enforce_wheelbase_constraint(v, omega)

        # Store data
        if self.start_time is not None:
            self.velocity_data.append(v)
            self.angular_velocity_data.append(omega)
            self.time_data.append(rospy.Time.now().to_sec() - self.start_time)

        self.current_v = v
        self.current_omega = omega
        return v, omega

class GUI:
    def __init__(self, master, controller):
        self.master = master
        master.title("MiR100 Spline Tracking")
        self.controller = controller

        # Check map
        map_path = "static/map_image.png"
        if not os.path.exists(map_path):
            raise FileNotFoundError(f"Could not find {map_path}")

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
        self.error_tab = tk.Frame(self.tabControl)
        self.tabControl.add(self.trajectory_tab, text='Trajectory')
        self.tabControl.add(self.velocity_tab, text='Velocity')
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
            if len(self.controller.waypoints_x) >= 1:
                self.controller.waypoints_x.append(x)
                self.controller.waypoints_y.append(y)
            self.update_waypoint_plot()
            print(f"Clicked at x={x}, y={y}")

    def start_control_loop(self):
        if not self.controller.calculate_spline():
            self.result_label.config(text="Error: Could not create spline. Add more waypoints.")
            return

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.DISABLED)
        self.controller.trajectory_x = []
        self.controller.trajectory_y = []
        self.controller.reached_goal = False
        self.controller.current_v = 0.0
        self.controller.current_omega = 0.0
        self.controller.velocity_data = []
        self.controller.angular_velocity_data = []
        self.controller.time_data = []
        self.controller.cross_track_error_data = []
        self.controller.heading_error_data = []
        self.controller.start_time = rospy.Time.now().to_sec()
        self.control_loop_running = True
        self.update_plot()

    def stop_control_loop(self):
        self.control_loop_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.NORMAL)
        self.send_command(0.0, 0.0)

    def clear_waypoints(self):
        self.controller.waypoints_x = []
        self.controller.waypoints_y = []
        self.controller.spline_x = None
        self.controller.spline_y = None
        self.controller.spline_derivative_x = None
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
        self.waypoints_plot.set_data(self.controller.waypoints_x, self.controller.waypoints_y)
        self.ax_trajectory.relim()
        self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()

    def update_plot(self):
        if not self.control_loop_running:
            return

        if self.controller.current_pose is None:
            self.result_label.config(text="Waiting for initial pose from /amcl_pose...")
            self.master.after(50, self.update_plot)
            return

        x = self.controller.x
        y = self.controller.y
        theta = self.controller.theta

        v, omega = self.controller.pure_pursuit_control(x, y, theta)
        self.send_command(v, omega)

        self.line.set_data(self.controller.trajectory_x, self.controller.trajectory_y)
        self.robot_plot.set_data([x], [y])

        if self.controller.spline_x is not None and self.controller.spline_y is not None:
            t_spline = np.linspace(0, 1, 1000)
            x_spline = self.controller.spline_x(t_spline)
            y_spline = self.controller.spline_y(t_spline)
            self.spline_plot.set_data(x_spline, y_spline)

            closest_t = self.controller.find_closest_point_on_spline(x, y)
            lookahead_t = self.controller.compute_lookahead_t(closest_t)
            lookahead_x = self.controller.spline_x(lookahead_t)
            lookahead_y = self.controller.spline_y(lookahead_t)
            self.lookahead_plot.set_data([lookahead_x], [lookahead_y])

        self.update_waypoint_plot()
        self.ax_trajectory.relim()
        self.ax_trajectory.autoscale_view()
        self.canvas_trajectory.draw_idle()

        self.line_linear_velocity.set_data(self.controller.time_data, self.controller.velocity_data)
        self.line_angular_velocity.set_data(self.controller.time_data, self.controller.angular_velocity_data)
        self.ax_velocity.relim()
        self.ax_velocity.autoscale_view()
        self.canvas_velocity.draw_idle()

        self.line_cross_track_error.set_data(self.controller.time_data, self.controller.cross_track_error_data)
        self.line_heading_error.set_data(self.controller.time_data, self.controller.heading_error_data)
        self.ax_error.relim()
        self.ax_error.autoscale_view()
        self.canvas_error.draw_idle()

        self.master.update()

        if not self.controller.reached_goal:
            self.controller.rate.sleep()
            self.master.after(50, self.update_plot)
        else:
            self.stop_control_loop()

    def send_command(self, v, omega):
        twist_msg = Twist()
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
        dt = 0.01  # Matches paper's 20 Hz
        v_max = 0.5  # Matches paper
        v_min = -0.5
        omega_max = 0.5  # Matches paper
        omega_min = -0.5
        wheelbase = 0.6  # Matches paper
        lookahead_distance = 0.2  # Matches paper

        controller = PurePursuitController(dt, v_max, v_min, omega_max, omega_min, 
                                         wheelbase, lookahead_distance)
        rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, controller.pose_callback)
        root = tk.Tk()
        gui = GUI(root, controller)
        threading.Thread(target=ros_spin, daemon=True).start()
        root.mainloop()
    except Exception as e:
        rospy.logerr(f"Error running node: {e}")
        raise