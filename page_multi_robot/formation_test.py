import rospy, math, tf, traceback, threading
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
import tf.transformations
import tkinter as tk

def normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))

class FormationController2Rows:
    def __init__(self):
        rospy.init_node('formation_controller')
        self.leader_pose, self.leader_yaw = None, None
        self.leader_cmd_vel = Twist()
        self.follower_pose, self.follower_yaw = None, None
        self.last_leader_update_time = rospy.Time.now()
        self.desired_distance = 1.0
        self.formation_angle = math.radians(-90)
        self.kp_linear, self.kp_angular = 0.6, 1.2
        self.max_linear_controller, self.max_angular_controller = 1.0, 1.5
        self.safety_distance = 0.8
        self.check_safety = True
        self.rate = rospy.Rate(10)
        self.leader_cmd_vel_pub = rospy.Publisher('/mir/cmd_vel', Twist, queue_size=10)
        rospy.Subscriber('/mir/amcl_pose', PoseWithCovarianceStamped, self.leader_pose_callback)
        rospy.Subscriber('/mir2/amcl_pose', PoseWithCovarianceStamped, self.follower_pose_callback)
        rospy.Subscriber('/mir/cmd_vel', Twist, self.leader_cmd_vel_callback) 
        self.follower_cmd_vel = rospy.Publisher('/mir2/mobile_base_controller/cmd_vel', Twist, queue_size=10)

    def leader_cmd_vel_callback(self, msg):
        self.leader_cmd_vel = msg

    def leader_pose_callback(self, msg):
        self.leader_pose = msg.pose.pose
        self.leader_yaw = self.get_yaw_from_pose(self.leader_pose)

    def follower_pose_callback(self, msg):
        self.follower_pose = msg.pose.pose
        self.follower_yaw = self.get_yaw_from_pose(self.follower_pose)

    def get_yaw_from_pose(self, msg):
        quaternion = (
            msg.orientation.x,
            msg.orientation.y,
            msg.orientation.z,
            msg.orientation.w
        )
        _, _, yaw = tf.transformations.euler_from_quaternion(quaternion)
        return yaw
    
    def check_collision_risk(self):
        if self.leader_pose is None or self.follower_pose is None:
            return False
        dx = self.leader_pose.position.x - self.follower_pose.position.x
        dy = self.leader_pose.position.y - self.follower_pose.position.y  
        distance = math.sqrt(dx ** 2 + dy ** 2)
        return distance < self.safety_distance  

    def control_follower(self):
        while not rospy.is_shutdown():  
            if self.check_safety:
                if self.leader_pose is None or self.leader_yaw is None or self.follower_pose is None or self.follower_yaw is None:
                    self.rate.sleep()
                    continue

                leader_x, leader_y = self.leader_pose.position.x, self.leader_pose.position.y
                leader_yaw = self.leader_yaw

                follower_x, follower_y = self.follower_pose.position.x, self.follower_pose.position.y
                follower_yaw = self.follower_yaw

                target_follower_x = leader_x + self.desired_distance * math.cos(leader_yaw + self.formation_angle)
                target_follower_y = leader_y + self.desired_distance * math.sin(leader_yaw + self.formation_angle)
                target_follower_yaw = leader_yaw

                error_follower_x = target_follower_x - follower_x
                error_follower_y = target_follower_y - follower_y
                error_distance_follower = math.sqrt(error_follower_x ** 2 + error_follower_y ** 2)

                angle_to_target = math.atan2(error_follower_y, error_follower_x)
                error_angle_to_target = normalize_angle(angle_to_target - follower_yaw)
                error_orientation = normalize_angle(target_follower_yaw - follower_yaw)

                cmd = Twist()
                angular_vel = self.kp_angular * error_angle_to_target
                linear_vel = self.kp_linear * error_distance_follower
                linear_vel = min(linear_vel, self.kp_linear * error_distance_follower)
                cmd.linear.x = max(-self.max_linear_controller, min(linear_vel, self.max_linear_controller))
                cmd.angular.z = max(-self.max_angular_controller, min(angular_vel, self.max_angular_controller))
                self.check_safety = not self.check_collision_risk()  

                if error_distance_follower < 0.01 and self.check_safety:
                    cmd.angular.z = self.kp_angular * error_orientation
                    cmd.linear.x = 0.0
                self.follower_cmd_vel.publish(cmd)
            else:
                cmd = Twist()
                cmd.linear.x, cmd.angular.z = 0.0, 0.0
                self.follower_cmd_vel.publish(cmd)
                rospy.loginfo("STOPPED due to safety concern!")
            
            self.rate.sleep()

if __name__ == '__main__':
    try:
        controller = FormationController2Rows()
        controller.control_follower()
    except rospy.ROSInterruptException:
        pass
    except Exception as e:
        rospy.logerr(f"ERROR: {e}")
        traceback.print_exc()