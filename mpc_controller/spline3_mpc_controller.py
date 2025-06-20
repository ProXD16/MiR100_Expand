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

class Spline3_MPCController:
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
        self.start_time = None
        self.filter_order = filter_order
        self.cutoff_frequency = cutoff_frequency
        self.b, self.a = butter(self.filter_order, self.cutoff_frequency / (1 / (2 * self.dt)), btype='low', analog=False)
        self.ramp_up_duration = 2.0
        self.ramp_down_distance = 0.5
        self.velocity_smoothing_alpha = 0.3

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

    def mpc_control(self, x, y, theta):
        if self.spline_x is None or self.spline_y is None:
            rospy.logwarn("Spline is not defined. Cannot perform MPC control.")
            return 0.0, 0.0

        closest_t = self.find_closest_point_on_spline(x, y)
        lookahead_t = self.compute_lookahead_t(closest_t)

        lookahead_x = self.spline_x(lookahead_t)
        lookahead_y = self.spline_y(lookahead_t)

        final_goal_x = self.waypoints_x[-1]
        final_goal_y = self.waypoints_y[-1]
        distance_to_final_goal = np.sqrt((x - final_goal_x)**2 + (y - final_goal_y)**2)
        if distance_to_final_goal < self.distance_threshold:
            rospy.loginfo("Reached the final goal!")
            self.reached_goal = True
            return 0.0, 0.0

        dx_dt = self.spline_derivative_x(lookahead_t)
        dy_dt = self.spline_derivative_y(lookahead_t)
        angle_to_goal = np.arctan2(dy_dt, dx_dt)
        if lookahead_t < closest_t:
            angle_to_goal = np.arctan2(-dy_dt, -dx_dt)
        heading_error = angle_to_goal - theta
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))

        x_error = lookahead_x - x
        y_error = lookahead_y - y
        distance_error = np.sqrt(x_error**2 + y_error**2)

        heading_threshold = 0.1
        linear_speed_kp = 1.5
        angular_speed_kp = 1.5

        if abs(heading_error) > heading_threshold:
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

        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

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