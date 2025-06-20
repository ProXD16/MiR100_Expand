import rospy
from geometry_msgs.msg import Pose, Twist, PoseWithCovarianceStamped
import numpy as np
import tf.transformations
from scipy.signal import butter, filtfilt
from numpy import cos, sin, arctan2, sqrt

def circle_from_3_points(p1, p2, p3):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    A = x1*(y2-y3) - y1*(x2-x3) + x2*y3 - x3*y2
    B = (x1**2 + y1**2) * (y3-y2) + (x2**2 + y2**2) * (y1-y3) + (x3**2 + y3**2) * (y2-y1)
    C = (x1**2 + y1**2) * (x2-x3) + (x2**2 + y2**2) * (x3-x1) + (x3**2 + y3**2) * (x1-x2)
    D = (x1**2 + y1**2) * (x3*y2 - x2*y3) + (x2**2 + y2**2) * (x1*y3 - x3*y1) + (x3**2 + y3**2) * (x2*y1 - x1*y2)
    if A == 0:
        return None, None 
    cx = -B / (2*A)
    cy = -C / (2*A)
    r = sqrt((cx - x1)**2 + (cy - y1)**2)
    return (cx, cy), r

def angle_between_vectors(v1, v2):
    v1_u = v1 / np.linalg.norm(v1)
    v2_u = v2 / np.linalg.norm(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))

class Arc_MPCController:
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
        #Circle properties (center coordinates, radius, start, end angle)
        self.circle_center = None
        self.circle_radius = None
        self.arc_start_angle = None
        self.arc_end_angle = None

    def lowpass_filter(self, data):
        padlen = 3 * self.filter_order
        if len(data) <= padlen:
            return data
        y = filtfilt(self.b, self.a, data, padlen=padlen)
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
        self.arc_start_angle = arctan2(self.waypoints_y[0] - cy, self.waypoints_x[0] - cx) #Start at robot pose
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
        #You will need to implement logic to correctly handle angles and wrap around
        angle = self.clamp_angle(angle, self.arc_start_angle, self.arc_end_angle)

        return angle

    def clamp_angle(self, angle, start_angle, end_angle):
        """Clamps an angle to be within the range of start_angle and end_angle."""
        # This is a simplified clamping; you may need more sophisticated logic
        # depending on the direction of the arc.
        if start_angle < end_angle:
            return max(min(angle, end_angle), start_angle)
        else: #end_angle < start_angle
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

        #Clamp lookahead angle to ensure it is not out of bound
        lookahead_angle = self.clamp_angle(lookahead_angle, self.arc_start_angle, self.arc_end_angle)

        # Convert the lookahead angle to x, y coordinates
        cx, cy = self.circle_center
        lookahead_x = cx + self.circle_radius * cos(lookahead_angle)
        lookahead_y = cy + self.circle_radius * sin(lookahead_angle)

        # Check if the goal is reached
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

        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

        # Calculate acceleration (same as before)
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
