#!/usr/bin/env python
import rospy
import math
import tf
import traceback
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
import tf.transformations

def normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))

class FormationController:
    def __init__(self):
        rospy.init_node('formation_controller')
        self.leader_pose = None
        self.leader_yaw = None
        self.leader_cmd_vel = Twist()
        self.follower_pose = None
        self.follower_yaw = None
        self.desired_distance = 1.0  
        self.formation_angle = math.radians(-90)  
        self.formation_tolerance = 0.05  
        self.angle_tolerance = math.radians(5) 
        self.kp_linear = 0.6
        self.kp_angular = 1.2
        self.max_linear_speed = 1.0
        self.max_angular_speed = 1.5 
        self.safety_distance = 0.8 
        self.rate = rospy.Rate(10) 
        self.leader_cmd_pub = rospy.Publisher('/mir/cmd_vel', Twist, queue_size=10)
        self.follower_cmd_pub = rospy.Publisher('/mir2/mobile_base_controller/cmd_vel', Twist, queue_size=10)
        rospy.Subscriber('/mir/amcl_pose', PoseWithCovarianceStamped, self.leader_pose_callback)
        rospy.Subscriber('/mir2/amcl_pose', PoseWithCovarianceStamped, self.follower_pose_callback)
        rospy.Subscriber('/mir/cmd_vel', Twist, self.leader_cmd_vel_callback)

    def leader_cmd_vel_callback(self, msg):
        self.leader_cmd_vel = msg

    def leader_pose_callback(self, msg):
        self.leader_pose = msg.pose.pose
        self.leader_yaw = self.get_yaw_from_pose(self.leader_pose)

    def follower_pose_callback(self, msg):
        self.follower_pose = msg.pose.pose
        self.follower_yaw = self.get_yaw_from_pose(self.follower_pose)

    def get_yaw_from_pose(self, pose):
        quaternion = (
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w
        )
        _, _, yaw = tf.transformations.euler_from_quaternion(quaternion)
        return yaw
    
    def check_collision_risk(self):
        if self.leader_pose is None or self.follower_pose is None:
            return False
        dx = self.leader_pose.position.x - self.follower_pose.position.x
        dy = self.leader_pose.position.y - self.follower_pose.position.y
        distance = math.sqrt(dx**2 + dy**2)
        return distance < self.safety_distance

    def control_follower(self):
        while not rospy.is_shutdown():
            if None in [self.leader_pose, self.leader_yaw, self.follower_pose, self.follower_yaw]:
                rospy.logwarn_throttle(1.0, "Waiting for pose data...")
                self.rate.sleep()
                continue
            lx, ly = self.leader_pose.position.x, self.leader_pose.position.y
            lyaw = self.leader_yaw
            fx, fy = self.follower_pose.position.x, self.follower_pose.position.y
            fyaw = self.follower_yaw
            target_x = lx + self.desired_distance * math.cos(lyaw + self.formation_angle)
            target_y = ly + self.desired_distance * math.sin(lyaw + self.formation_angle)
            target_yaw = lyaw  
            error_x = target_x - fx
            error_y = target_y - fy
            error_dist = math.sqrt(error_x**2 + error_y**2)
            angle_to_target = math.atan2(error_y, error_x)
            error_angle = normalize_angle(angle_to_target - fyaw)
            error_orientation = normalize_angle(target_yaw - fyaw)
            cmd = Twist()
            collision_risk = self.check_collision_risk()
            if collision_risk:
                rospy.logwarn_throttle(1.0, "Collision risk detected! Avoiding...")
                dx = lx - fx
                dy = ly - fy
                distance = math.sqrt(dx**2 + dy**2)
                if distance > 0:
                    cmd.linear.x = -0.3 * (self.safety_distance - distance)
                    cmd.angular.z = self.kp_angular * normalize_angle(math.atan2(dy, dx) - fyaw)
            else:
                if error_dist > self.formation_tolerance:
                    angular_vel = self.kp_angular * error_angle
                    linear_vel = self.kp_linear * error_dist * max(0, math.cos(error_angle))
                    cmd.linear.x = max(-self.max_linear_speed, min(linear_vel, self.max_linear_speed))
                    cmd.angular.z = max(-self.max_angular_speed, min(angular_vel, self.max_angular_speed))
                else:
                    cmd.linear.x = 0.0
                    cmd.angular.z = self.kp_angular * error_orientation

            self.follower_cmd_pub.publish(cmd)
            self.rate.sleep()

if __name__ == '__main__':
    try:
        controller = FormationController()
        controller.control_follower()
    except rospy.ROSInterruptException:
        pass
    except Exception as e:
        rospy.logerr(f"Error: {e}")
        traceback.print_exc()