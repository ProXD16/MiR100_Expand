import rospy
import numpy as np
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import tf, math

class CircularMotionController:
    def __init__(self):
        rospy.init_node('circle_controller')
        
        # Tham số đường tròn
        self.center_x = 0.0  # Tọa độ tâm
        self.center_y = 0.0
        self.radius = 1.0    # Bán kính (m)
        self.speed = 0.2     # Tốc độ (m/s)
        
        # PID parameters
        self.Kp = 1.5
        self.Ki = 0.01
        self.Kd = 0.2
        
        # Biến điều khiển
        self.integral = 0
        self.prev_error = 0
        
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        rospy.Subscriber('/odom', Odometry, self.odom_callback)
        
    def odom_callback(self, msg):
        # Lấy vị trí và hướng hiện tại
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        quat = msg.pose.pose.orientation
        (_, _, yaw) = tf.transformations.euler_from_quaternion(
            [quat.x, quat.y, quat.z, quat.w])
        
        # Tính toán điều khiển
        twist = Twist()
        
        # 1. Tính vận tốc góc mong muốn
        desired_omega = self.speed / self.radius
        
        # 2. Tính sai số bán kính
        dx = x - self.center_x
        dy = y - self.center_y
        current_radius = math.sqrt(dx**2 + dy**2)
        radius_error = self.radius - current_radius
        
        # 3. Điều khiển PID để hiệu chỉnh
        self.integral += radius_error
        derivative = radius_error - self.prev_error
        correction = self.Kp*radius_error + self.Ki*self.integral + self.Kd*derivative
        self.prev_error = radius_error
        
        # 4. Áp dụng vận tốc
        twist.linear.x = self.speed + correction
        twist.angular.z = desired_omega
        
        self.cmd_vel_pub.publish(twist)

if __name__ == '__main__':
    controller = CircularMotionController()
    rospy.spin()