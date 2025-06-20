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
from scipy.interpolate import splrep, splev
from scipy.signal import butter, filtfilt

class Spline5_MPCController:
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
        self.spline_x = None
        self.spline_y = None
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

        self.waypoints_x = np.array(self.waypoints_x)
        self.waypoints_y = np.array(self.waypoints_y)

        distances = np.cumsum(np.sqrt(np.diff(self.waypoints_x)**2 + np.diff(self.waypoints_y)**2))
        distances = np.insert(distances, 0, 0)
        self.arclength = distances[-1]

        if self.arclength < 1e-6:
            rospy.logwarn("Total distance between waypoints is too small. Cannot create spline.")
            return False

        try:
            tck_x = splrep(distances, self.waypoints_x, k=5, s=0)
            tck_y = splrep(distances, self.waypoints_y, k=5, s=0)

            self.spline_x = tck_x
            self.spline_y = tck_y
            return True
        except Exception as e:
            rospy.logerr(f"Error creating spline: {e}")
            return False

    def find_closest_point_on_spline(self, x, y):
        if self.spline_x is None or self.spline_y is None or self.arclength is None:
            return 0.0
        s_range = np.linspace(0, self.arclength, num=1000)
        x_range = splev(s_range, self.spline_x)
        y_range = splev(s_range, self.spline_y)
        distances = np.sqrt((x_range - x)**2 + (y_range - y)**2)
        closest_idx = np.argmin(distances)
        return s_range[closest_idx]

    def mpc_control(self, x, y, theta):
        if self.spline_x is None or self.spline_y is None:
            rospy.logwarn("Spline is not defined. Cannot perform MPC control.")
            return 0.0, 0.0

        closest_s = self.find_closest_point_on_spline(x, y)

        lookahead_s = closest_s + self.lookahead_distance
        if lookahead_s > self.arclength:
            lookahead_s = self.arclength
        elif lookahead_s < 0:
            lookahead_s = 0

        lookahead_x = splev(lookahead_s, self.spline_x)
        lookahead_y = splev(lookahead_s, self.spline_y)

        final_goal_x = self.waypoints_x[-1]
        final_goal_y = self.waypoints_y[-1]
        distance_to_final_goal = np.sqrt((x - final_goal_x)**2 + (y - final_goal_y)**2)
        if distance_to_final_goal < self.distance_threshold:
            rospy.loginfo("Reached the final goal!")
            self.reached_goal = True
            return 0.0, 0.0

        dx_ds = splev(lookahead_s, self.spline_x, der=1)
        dy_ds = splev(lookahead_s, self.spline_y, der=1)
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