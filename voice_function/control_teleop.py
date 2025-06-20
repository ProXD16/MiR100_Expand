#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
import rospy
from geometry_msgs.msg import Twist,PoseStamped
import speech_recognition as sr
import time # Dùng time.sleep hoặc rospy.sleep đều được, nhưng rospy.sleep tốt hơn trong ROS

# --- Định nghĩa lớp RobotController (Lấy từ code trước) ---
class RobotController:
    """
    Một lớp đơn giản để điều khiển robot gửi lệnh Twist trên topic /cmd_vel.
    """
    def __init__(self, linear_speed=0.2, angular_speed=0.5, cmd_vel_topic='/cmd_vel', goal_topic="/move_base_simple/goal"):
        """
        Khởi tạo bộ điều khiển robot.
        """
        try:
            # Tạo publisher trong __init__ của lớp
            self.pub = rospy.Publisher(cmd_vel_topic, Twist, queue_size=10)
            self.goal_pub = rospy.Publisher(goal_topic, PoseStamped, queue_size=10)
        except Exception as e:
             
             return

        self.linear_speed = linear_speed
        self.angular_speed = angular_speed
        self.cmd_vel_topic = cmd_vel_topic
        self.goal_topic = goal_topic
        self.twist = Twist()

        
        # Đăng ký hàm dừng robot khi node tắt
        rospy.on_shutdown(self.stop_on_exit)
        # Đảm bảo robot dừng khi khởi tạo
        self.stop()

    def publish_goal(self, x, y, angle):
        if self.goal_pub:
            try:
                pose = PoseStamped()
                pose.header.stamp = rospy.Time.now()
                pose.header.frame_id = "map"
                pose.pose.position.x = float(x)
                pose.pose.position.y = float(y)
                pose.pose.orientation.z = math.sin(angle / 2)
                pose.pose.orientation.w = math.cos(angle / 2)
                self.goal_pub.publish(pose)
                return "Goal published successfully! (x: {}, y: {}, angle: {})".format(x, y, angle)
            except Exception as e:
                return f"Error publishing goal: {e}"
        return "Goal publisher not initialized."    

    def _publish_velocity(self):
        """Hàm nội bộ để gửi tin nhắn twist hiện tại."""
        try:
            self.pub.publish(self.twist)
        except rospy.ROSException as e:
             rospy.logerr(f"Lỗi khi gửi lệnh tới '{self.cmd_vel_topic}': {e}")

    def move_forward(self):
        """Gửi lệnh đi thẳng về phía trước."""
        rospy.loginfo("Robot command: Đi tới")
        self.twist.linear.x = self.linear_speed
        self.twist.angular.z = 0.0
        self._publish_velocity()

    def move_backward(self):
        """Gửi lệnh đi lùi."""
        rospy.loginfo("Robot command: Đi lùi")
        self.twist.linear.x = -self.linear_speed
        self.twist.angular.z = 0.0
        self._publish_velocity()

    def turn_left(self):
        """Gửi lệnh quay sang trái."""
        rospy.loginfo("Robot command: Quay trái")
        self.twist.linear.x = 0.0
        self.twist.angular.z = self.angular_speed
        self._publish_velocity()

    def turn_right(self):
        """Gửi lệnh quay sang phải."""
        rospy.loginfo("Robot command: Quay phải")
        self.twist.linear.x = 0.0
        self.twist.angular.z = -self.angular_speed
        self._publish_velocity()

    def move_forward_left(self):
        rospy.loginfo("Robot command: tien quay trai")
        self.twist.linear.x = self.linear_speed
        self.twist.angular.z = self.angular_speed
        self._publish_velocity()

    def move_forward_right(self):
        rospy.loginfo("Robot command: tien quay phai")
        self.twist.linear.x = self.linear_speed
        self.twist.angular.z = -self.angular_speed
        self._publish_velocity()

    def move_backward_left(self):
        rospy.loginfo("Robot command: lui quay trai")
        self.twist.linear.x = -self.linear_speed
        self.twist.angular.z = self.angular_speed
        self._publish_velocity()

    def move_backward_right(self):
        rospy.loginfo("Robot command: lui quay phai")
        self.twist.linear.x = -self.linear_speed
        self.twist.angular.z = -self.angular_speed
        self._publish_velocity()
        
    def stop(self):
        """Gửi lệnh dừng hoàn toàn."""
        rospy.loginfo("Robot command: Dừng")
        self.twist.linear.x = 0.0
        self.twist.angular.z = 0.0
        # Gửi lệnh dừng vài lần để đảm bảo
        for _ in range(3):
            if rospy.is_shutdown(): # Kiểm tra nếu node đã bị tắt giữa chừng
                break
            self._publish_velocity()
            try:
                rospy.sleep(0.01) # Dùng rospy.sleep thay vì time.sleep
            except rospy.ROSInterruptException:
                rospy.loginfo("Ngắt trong lúc gửi lệnh dừng.")
                break


    def stop_on_exit(self):
        """Hàm được gọi tự động khi node tắt để dừng robot."""
        rospy.loginfo("Node đang tắt. Gửi lệnh dừng cuối cùng...")
        self.stop()
        rospy.loginfo("Robot đã dừng.")

# --- Hàm chính điều khiển bằng giọng nói ---


# --- Phần chạy chính của chương trình ---
if __name__ == '__main__':
    rospy.init_node('voice_robot_controller_node', anonymous=True)

        # 2. Tạo đối tượng điều khiển Robot
        # Điều chỉnh tốc độ và topic nếu cần
    controller = RobotController(linear_speed=0.15, angular_speed=0.4, cmd_vel_topic='/cmd_vel') # Giảm tốc độ mặc định cho an toàn
