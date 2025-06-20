import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist, Pose
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

class LineMPCController:
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
        self.ramp_up_duration = 4.0  # Duration for velocity ramp-up in seconds
        self.ramp_down_distance = 0.5  # Distance from goal to start ramping down velocities

    def lowpass_filter(self, data):
        padlen = 3 * self.filter_order
        if len(data) <= padlen:  # Need enough data points for padding
            return data
        y = filtfilt(self.b, self.a, data, padlen=padlen)  # Add padlen parameter
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

    #     # Update plot directly from pose_callback (FASTEST)
    #     if self.gui and hasattr(self.gui, 'control_loop_running') and self.gui.control_loop_running:
    #         self.gui.master.after(0, self.gui.update_plot_from_callback)

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

        heading_threshold = 0.1
        linear_speed_kp = 0.3
        angular_speed_kp = 0.5

        if abs(heading_error) > heading_threshold:
            v = 0.0
            omega = angular_speed_kp * heading_error
        else:
            v = linear_speed_kp * distance_to_goal
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
        if distance_to_goal < self.ramp_down_distance:
            ramp_down_factor = distance_to_goal / self.ramp_down_distance
            v *= ramp_down_factor
            omega *= ramp_down_factor

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