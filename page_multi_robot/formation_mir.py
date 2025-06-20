#!/usr/bin/env python
import rospy
import math
import tf
from geometry_msgs.msg import Twist, Pose, Point, Quaternion, PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
import threading

# Hàm chuẩn hóa góc về [-pi, pi]
def normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))

class FormationController:
    def __init__(self):
        rospy.init_node('formation_controller')

        # --- Robot 1 (Leader) - Mô phỏng từ điều khiển bàn phím ---
        # Khởi tạo vị trí ban đầu cho robot 1
        self.robot1_pose = Pose()
        self.robot1_pose.position.x = 10.0
        self.robot1_pose.position.y = 8.0
        self.robot1_pose.orientation = Quaternion(*tf.transformations.quaternion_from_euler(0, 0, 0))
        self.robot1_yaw = math.pi / 4 # Lưu trữ yaw riêng để dễ tính toán

        self.robot1_cmd_vel = Twist() # Lưu trữ lệnh vận tốc cuối cùng
        self.last_leader_update_time = rospy.Time.now()

        # Subscriber để nhận lệnh điều khiển cho robot 1 (TỪ BÀN PHÍM)
        # Đảm bảo topic này khớp với topic mà node teleop của bạn publish tới
        rospy.Subscriber('/robot1_teleop/cmd_vel', Twist, self.robot1_cmd_vel_cb)
        rospy.loginfo("Đang chờ lệnh điều khiển cho Robot 1 trên topic /robot1_teleop/cmd_vel...")

        # --- Robot 2 (Follower) - Nhận vị trí từ AMCL và gửi lệnh điều khiển ---
        rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, self.robot2_pose_cb)
        self.robot2_cmd_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.robot2_pose = None
        self.robot2_yaw = None

        # Thông số đội hình
        self.desired_distance = 1.0  # Khoảng cách mong muốn 1m
        self.formation_angle = math.radians(-45) # Góc mong muốn so với hướng của leader (0 là ngang hàng bên phải)
                                                  # Pi là thẳng hàng phía sau
                                                  # Pi/2 là ngang hàng bên trái

        # Thông số điều khiển PID (có thể cần tinh chỉnh)
        self.kp_linear = 0.6  # Tăng nhẹ để phản ứng nhanh hơn với thay đổi của leader
        self.kp_angular = 1.2 # Tăng nhẹ để điều chỉnh góc nhanh hơn
        # self.kp_orient = 0.5 # Gain để giữ hướng tương đối (nếu cần)


        # Tần số điều khiển
        self.rate = rospy.Rate(20) # Tăng tần số để mô phỏng và điều khiển mượt hơn

    def robot1_cmd_vel_cb(self, msg):
        """Lưu trữ lệnh vận tốc từ bàn phím cho Robot 1"""
        self.robot1_cmd_vel = msg

    def update_robot1_pose(self):
        """Cập nhật vị trí mô phỏng của Robot 1 dựa trên cmd_vel"""
        current_time = rospy.Time.now()
        dt = (current_time - self.last_leader_update_time).to_sec()
        self.last_leader_update_time = current_time

        if dt <= 0: # Tránh lỗi chia cho 0 hoặc thời gian âm
            return

        # Tính toán sự thay đổi vị trí và hướng
        delta_x = self.robot1_cmd_vel.linear.x * math.cos(self.robot1_yaw) * dt
        delta_y = self.robot1_cmd_vel.linear.x * math.sin(self.robot1_yaw) * dt
        delta_yaw = self.robot1_cmd_vel.angular.z * dt

        # Cập nhật vị trí và yaw
        self.robot1_pose.position.x += delta_x
        self.robot1_pose.position.y += delta_y
        self.robot1_yaw = normalize_angle(self.robot1_yaw + delta_yaw)

        # Cập nhật orientation (quaternion) từ yaw mới
        self.robot1_pose.orientation = Quaternion(*tf.transformations.quaternion_from_euler(0, 0, self.robot1_yaw))

        # In vị trí mô phỏng để kiểm tra (tùy chọn)
        # rospy.loginfo_throttle(1.0, f"Sim Robot1 Pose: x={self.robot1_pose.position.x:.2f}, y={self.robot1_pose.position.y:.2f}, yaw={math.degrees(self.robot1_yaw):.1f}")


    def robot2_pose_cb(self, msg):
        """Cập nhật vị trí robot follower từ AMCL"""
        self.robot2_pose = msg.pose.pose
        self.robot2_yaw = self.get_yaw_from_pose(self.robot2_pose)

    def get_yaw_from_pose(self, pose):
        """Trích xuất góc yaw từ pose"""
        quaternion = (
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w)
        _, _, yaw = tf.transformations.euler_from_quaternion(quaternion)
        return yaw

    def control_robot2(self):
        """Điều khiển robot 2 để duy trì đội hình"""
        while not rospy.is_shutdown():
            # 1. Cập nhật vị trí mô phỏng của Robot 1
            self.update_robot1_pose()

            # 2. Kiểm tra xem đã có vị trí của Robot 2 chưa
            if self.robot2_pose is None or self.robot2_yaw is None:
                # rospy.logwarn_throttle(2.0,"Chưa nhận được vị trí Robot 2 từ AMCL.")
                self.rate.sleep()
                continue

            # 3. Lấy vị trí hiện tại của các robot
            x1 = self.robot1_pose.position.x
            y1 = self.robot1_pose.position.y
            yaw1 = self.robot1_yaw # Sử dụng yaw đã lưu

            x2 = self.robot2_pose.position.x
            y2 = self.robot2_pose.position.y
            yaw2 = self.robot2_yaw # Sử dụng yaw đã lưu

            # 4. Tính toán vị trí mục tiêu toàn cục (global target) cho Robot 2
            # Vị trí mục tiêu là vị trí của leader cộng với vector khoảng cách/góc mong muốn
            # Vector này quay theo hướng của leader (yaw1)
            target_x = x1 + self.desired_distance * math.cos(yaw1 + self.formation_angle)
            target_y = y1 + self.desired_distance * math.sin(yaw1 + self.formation_angle)
            # Mục tiêu hướng: Giữ hướng song song với leader
            target_yaw = yaw1 # Hoặc có thể là yaw1 + góc cố định nào đó nếu muốn

            # 5. Tính toán sai số vị trí toàn cục
            error_x = target_x - x2
            error_y = target_y - y2
            error_dist = math.sqrt(error_x**2 + error_y**2)

            # 6. Tính toán sai số góc
            # Góc cần thiết để robot 2 hướng về điểm mục tiêu
            angle_to_target = math.atan2(error_y, error_x)
            error_angle_to_target = normalize_angle(angle_to_target - yaw2)

            # Sai số giữa hướng hiện tại của robot 2 và hướng mục tiêu (hướng của leader)
            error_orientation = normalize_angle(target_yaw - yaw2)

            # 7. Tính toán lệnh điều khiển (Logic điều khiển mới)
            cmd = Twist()

            # Điều khiển vận tốc góc:
            # Ưu tiên hướng về phía điểm mục tiêu trước.
            # Có thể kết hợp cả việc hướng về điểm mục tiêu và giữ hướng song song leader.
            # Ví dụ: Chủ yếu quay theo hướng điểm mục tiêu, thêm một phần nhỏ để giữ hướng song song.
            # angular_vel = self.kp_angular * error_angle_to_target + self.kp_orient * error_orientation
            # Hoặc đơn giản hơn: Chỉ quay để hướng về điểm mục tiêu
            angular_vel = self.kp_angular * error_angle_to_target

            # Điều khiển vận tốc thẳng:
            # Chỉ di chuyển thẳng nếu robot đang hướng tương đối đúng về mục tiêu
            # Dùng cos(error_angle_to_target) để giảm tốc độ khi góc lệch lớn
            # max(0, ...) để tránh đi lùi khi góc lệch > 90 độ
            linear_vel = self.kp_linear * error_dist * max(0, math.cos(error_angle_to_target))
            # Giảm tốc độ khi đã gần đến mục tiêu để tránh overshoot
            linear_vel = min(linear_vel, self.kp_linear * error_dist) # Giới hạn bởi kp*error_dist thuần túy


            # 8. Giới hạn vận tốc
            max_linear = 0.5
            max_angular = 1.0
            cmd.linear.x = max(-max_linear, min(linear_vel, max_linear))
            cmd.angular.z = max(-max_angular, min(angular_vel, max_angular))

            # Nếu khoảng cách đã rất nhỏ, giảm tốc độ góc để ổn định hướng
            if error_dist < 0.1:
                 cmd.angular.z = self.kp_angular * error_orientation # Chuyển sang điều khiển giữ hướng
                 # Có thể dừng hẳn linear vel nếu muốn
                 # cmd.linear.x = 0.0


            # 9. Gửi lệnh điều khiển
            self.robot2_cmd_pub.publish(cmd)

            self.rate.sleep()

if __name__ == '__main__':
    try:
        controller = FormationController()
        # Không cần thread riêng vì update_robot1_pose được gọi trong vòng lặp chính
        controller.control_robot2()
    except rospy.ROSInterruptException:
        pass
    except Exception as e:
        rospy.logerr(f"Đã xảy ra lỗi: {e}")
        import traceback
        traceback.print_exc()