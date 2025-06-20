#!/usr/bin/env python
import rospy
from sensor_msgs.msg import LaserScan
import math

class DistanceMeasurer:
    def __init__(self, 
                 front_scan_topic="/f_scan", 
                 back_scan_topic="/b_scan", 
                 default_measurement_angle_deg_total=50.0):
        
        rospy.loginfo("Initializing DistanceMeasurer...")
        self.front_scan_data = None
        self.back_scan_data = None
        
        self.front_scan_topic = front_scan_topic
        self.back_scan_topic = back_scan_topic
        
        self.default_measurement_angle_rad_half = math.radians(default_measurement_angle_deg_total / 2.0)

        self.config = {
            "front": {"min_angle": 0, "max_angle": 0, "increment": 0, "num_ranges": 0, "has_config": False, "topic": front_scan_topic, "sub": None},
            "back":  {"min_angle": 0, "max_angle": 0, "increment": 0, "num_ranges": 0, "has_config": False, "topic": back_scan_topic, "sub": None}
        }

        self._init_subscriber("front")
        self._init_subscriber("back")
        
        rospy.loginfo("DistanceMeasurer initialized.")

    def _init_subscriber(self, direction_key):
        cfg = self.config[direction_key]
        topic = cfg["topic"]
        if topic:
            try:
                rospy.loginfo(f"Waiting for first message on {topic} ({direction_key})...")
                initial_scan_msg = rospy.wait_for_message(topic, LaserScan, timeout=3.0) # Giảm timeout
                self._configure_from_scan_data(initial_scan_msg, direction_key)
                if direction_key == "front":
                    cfg["sub"] = rospy.Subscriber(topic, LaserScan, self._front_scan_callback)
                elif direction_key == "back":
                    cfg["sub"] = rospy.Subscriber(topic, LaserScan, self._back_scan_callback)
                rospy.loginfo(f"Subscribed to {direction_key} LiDAR: {topic}")
            except rospy.ROSException:
                rospy.logwarn(f"Timeout/Error for {direction_key} LiDAR '{topic}'. {direction_key.capitalize()} measurements may fail.")
            except Exception as e:
                rospy.logerr(f"Error initializing {direction_key} LiDAR for DistanceMeasurer: {e}")
        else:
            rospy.logdebug(f"{direction_key.capitalize()} scan topic not provided for DistanceMeasurer.")


    def _configure_from_scan_data(self, scan_msg, direction_key):
        if scan_msg and direction_key in self.config:
            cfg = self.config[direction_key]
            if not cfg["has_config"]: # Chỉ cấu hình một lần
                cfg["min_angle"] = scan_msg.angle_min
                cfg["max_angle"] = scan_msg.angle_max
                cfg["increment"] = scan_msg.angle_increment
                cfg["num_ranges"] = len(scan_msg.ranges)
                cfg["has_config"] = True
                rospy.loginfo(f"DistanceMeasurer: {direction_key.capitalize()} LiDAR configured: {cfg['num_ranges']} ranges, "
                              f"angles [{math.degrees(cfg['min_angle']):.1f}, {math.degrees(cfg['max_angle']):.1f}]deg")
        else:
            rospy.logwarn(f"DistanceMeasurer: Could not configure {direction_key} LiDAR.")

    def _front_scan_callback(self, msg):
        if not self.config["front"]["has_config"]:
            self._configure_from_scan_data(msg, "front")
        self.front_scan_data = msg

    def _back_scan_callback(self, msg):
        if not self.config["back"]["has_config"]:
            self._configure_from_scan_data(msg, "back")
        self.back_scan_data = msg

    def _get_distance_from_specific_lidar(self, direction_key, measurement_angle_deg_total=None):
        """
        Hàm nội bộ để lấy khoảng cách từ một LiDAR cụ thể.
        """
        scan_data_to_use = None
        if direction_key == "front":
            scan_data_to_use = self.front_scan_data
        elif direction_key == "back":
            scan_data_to_use = self.back_scan_data
        else: # Không nên xảy ra nếu gọi từ nội bộ
            return float('inf')

        cfg = self.config[direction_key]

        if scan_data_to_use is None or not cfg["has_config"]:
            # Không log warning ở đây vì get_overall_minimum_distance sẽ xử lý
            return float('inf') 

        if cfg["num_ranges"] == 0:
            return float('inf')
        
        current_angle_rad_half = self.default_measurement_angle_rad_half
        if measurement_angle_deg_total is not None:
            current_angle_rad_half = math.radians(measurement_angle_deg_total / 2.0)

        # Giả định tia giữa của mỗi LiDAR là hướng 0 độ của nó (thẳng trước/sau của robot)
        center_index_approx = cfg["num_ranges"] // 2 
        
        if cfg["increment"] == 0:
             dist = scan_data_to_use.ranges[center_index_approx]
             return dist if self._is_valid_reading(dist, scan_data_to_use.range_min, scan_data_to_use.range_max) else float('inf')

        indices_one_side = int(math.ceil(current_angle_rad_half / abs(cfg["increment"])))
        start_index = max(0, center_index_approx - indices_one_side)
        end_index = min(cfg["num_ranges"] - 1, center_index_approx + indices_one_side)
        
        min_dist_found = float('inf')
        for i in range(start_index, end_index + 1):
            distance = scan_data_to_use.ranges[i]
            if self._is_valid_reading(distance, scan_data_to_use.range_min, scan_data_to_use.range_max):
                if distance < min_dist_found:
                    min_dist_found = distance
        return min_dist_found

    def get_overall_minimum_distance(self, measurement_angle_deg_total=None):
        """
        Đo từ cả LiDAR trước và sau (nếu có), trả về khoảng cách nhỏ nhất tìm thấy.
        """
        dist_front = float('inf')
        dist_back = float('inf')

        # Chỉ đo nếu topic được cung cấp và subscriber đã được thiết lập (hoặc có dữ liệu config)
        if self.config["front"]["topic"] and (self.config["front"]["sub"] is not None or self.config["front"]["has_config"]):
            dist_front = self._get_distance_from_specific_lidar("front", measurement_angle_deg_total)
        else:
            rospy.logdebug_throttle(10, "Front LiDAR not configured/available for overall min distance.")


        if self.config["back"]["topic"] and (self.config["back"]["sub"] is not None or self.config["back"]["has_config"]):
            dist_back = self._get_distance_from_specific_lidar("back", measurement_angle_deg_total)
        else:
             rospy.logdebug_throttle(10, "Back LiDAR not configured/available for overall min distance.")

        if dist_front == float('inf') and dist_back == float('inf'):
            rospy.logwarn_throttle(5, "DistanceMeasurer: No valid LiDAR data from front or back.")
        
        min_overall = min(dist_front, dist_back)
        # rospy.logdebug(f"Overall min distance: front={dist_front if dist_front!=float('inf') else 'N/A'}, "
        #               f"back={dist_back if dist_back!=float('inf') else 'N/A'}, result={min_overall if min_overall!=float('inf') else 'inf'}")
        return min_overall

    def _is_valid_reading(self, distance, min_range, max_range):
        return not math.isinf(distance) and not math.isnan(distance) and \
               min_range <= distance <= max_range