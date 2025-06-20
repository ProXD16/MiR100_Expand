#!/usr/bin/env python
import rospy
from geometry_msgs.msg import Pose, Twist, PoseWithCovarianceStamped
import math

d = 0.5  # Khoảng cách mong muốn
Kp_linear = 0.5
Kp_angular = 1.2

# Biến lưu vị trí và góc quay
xl, yl, theta_l = None, None, None
x_mir2, y_mir2, theta_mir2 = None, None, None

def quaternion_to_yaw(z, w):
    # Chuyển đổi quaternion sang góc yaw (rad)
    return math.atan2(2 * w * z, 1 - 2 * z * z)

def mir1_pose_callback(msg):
    global xl, yl, theta_l
    xl = msg.position.x
    yl = msg.position.y
    z = msg.orientation.z
    w = msg.orientation.w
    theta_l = quaternion_to_yaw(z, w)
    rospy.loginfo(f"MiR1 - x: {xl:.3f}, y: {yl:.3f}, yaw: {math.degrees(theta_l):.3f}°")

def mir2_pose_callback(msg):
    global x_mir2, y_mir2, theta_mir2
    x_mir2 = msg.pose.pose.position.x
    y_mir2 = msg.pose.pose.position.y
    z = msg.pose.pose.orientation.z
    w = msg.pose.pose.orientation.w
    theta_mir2 = quaternion_to_yaw(z, w)
    rospy.loginfo(f"MiR2 - x: {x_mir2:.3f}, y: {y_mir2:.3f}, yaw: {math.degrees(theta_mir2):.3f}°")

def control_loop():
    rate = rospy.Rate(10)  # 10Hz
    while not rospy.is_shutdown():
        if None not in [xl, yl, theta_l, x_mir2, y_mir2, theta_mir2]:
            # Tính vị trí mong muốn của MiR2
            xf = xl - d * math.cos(theta_l)
            yf = yl - d * math.sin(theta_l)
            
            # Sai số vị trí
            ex = xf - x_mir2
            ey = yf - y_mir2
            
            # Điều khiển
            linear_velocity = Kp_linear * math.sqrt(ex**2 + ey**2)
            angular_error = math.atan2(ey, ex) - theta_mir2
            angular_velocity = Kp_angular * math.atan2(math.sin(angular_error), math.cos(angular_error))
            
            # Xuất tín hiệu
            cmd_vel = Twist()
            cmd_vel.linear.x = linear_velocity
            cmd_vel.angular.z = angular_velocity
            cmd_vel_pub.publish(cmd_vel)
            
            rospy.loginfo(f"Control - linear.x: {cmd_vel.linear.x:.3f}, angular.z: {cmd_vel.angular.z:.3f}")
        rate.sleep()

def main():
    rospy.init_node('mir_follower_control', anonymous=True)
    rospy.Subscriber("/mir/amcl_pose", PoseWithCovarianceStamped, mir2_pose_callback)
    rospy.Subscriber("/robot_pose", Pose, mir1_pose_callback)
    global cmd_vel_pub
    cmd_vel_pub = rospy.Publisher("/mir/cmd_vel", Twist, queue_size=10)
    rospy.loginfo("Bắt đầu điều khiển đội hình MiR...")
    control_loop()

if __name__ == "__main__":
    main()