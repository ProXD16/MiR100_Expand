#!/usr/bin/env python
import rospy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool
import math

class ObstacleChecker:
    def __init__(self, height_threshold=0.5, distance_threshold=1.0, angle_range=30):
        self.height_threshold = height_threshold
        self.distance_threshold = distance_threshold
        self.angle_range = math.radians(angle_range) 
        self.front_scan = None
        self.back_scan = None
        self.front_sub = rospy.Subscriber('/f_scan', LaserScan, self.front_scan_callback)
        self.back_sub = rospy.Subscriber('/b_scan', LaserScan, self.back_scan_callback)
        self.obstacle_pub = rospy.Publisher('/obstacle_detected', Bool, queue_size=10)

    def front_scan_callback(self, data):
        self.front_scan = data

    def back_scan_callback(self, data):
        self.back_scan = data

    def check_obstacle(self):
        obstacle_detected = False
        if self.front_scan:
            obstacle_detected |= self.process_scan(self.front_scan, "front")
        if self.back_scan:
            obstacle_detected |= self.process_scan(self.back_scan, "back")

        if obstacle_detected:
            print("PHÁT HIỆN VẬT CẢN PHÍA TRÊN!")
        else:
            print("Không phát hiện vật cản phía trên.")

        self.obstacle_pub.publish(obstacle_detected)
        return obstacle_detected

    def process_scan(self, scan_data, scan_type):
        obstacle_detected = False
        angle_increment = scan_data.angle_increment
        angle_min = scan_data.angle_min
        angle_max = scan_data.angle_max
        center_angle = 0 if scan_type == "front" else math.pi 
        angle_lower_bound = center_angle - self.angle_range / 2
        angle_upper_bound = center_angle + self.angle_range / 2

        for i, distance in enumerate(scan_data.ranges):
            current_angle = angle_min + i * angle_increment
            if angle_lower_bound <= current_angle <= angle_upper_bound:
                if scan_data.range_min <= distance <= self.distance_threshold:
                    if distance * math.sin(current_angle) < self.height_threshold:
                        obstacle_detected = True
                        print(f"Vật cản phía trên phát hiện ở {scan_type}: "
                              f"Khoảng cách={distance:.2f}m, Góc={math.degrees(current_angle):.2f}°")
                        break
        return obstacle_detected

    def run(self):
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            self.check_obstacle()
            rate.sleep()

if __name__ == '__main__':
    try:
        rospy.init_node('obstacle_checker', anonymous=True)
        checker = ObstacleChecker(
            height_threshold=0.5, 
            distance_threshold=1.0, 
            angle_range=60
        )
        checker.run()
    except rospy.ROSInterruptException:
        pass