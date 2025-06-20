#!/usr/bin/env python
import rospy
import numpy as np
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid
import cv2
from bresenham import bresenham
import math
from scipy.signal import medfilt
from scipy.ndimage import gaussian_filter

class HectorMapper:
    def __init__(self):
        rospy.init_node('hector_mapper', anonymous=True)

        # Thông số bản đồ
        self.map_width = 50.0
        self.map_height = 50.0
        self.resolution = 0.05
        self.grid_width = int(self.map_width / self.resolution)
        self.grid_height = int(self.map_height / self.resolution)
        self.origin_x = -self.map_width / 2
        self.origin_y = -self.map_height / 2

        # Occupancy grid và grid map chất lượng
        self.grid = -1 * np.ones((self.grid_height, self.grid_width), dtype=np.int8)
        self.quality_grid = np.zeros((self.grid_height, self.grid_width))
        self.accumulated_scan = None  # Lưu trữ dữ liệu tích lũy

        # Publisher và Subscriber
        self.map_pub = rospy.Publisher('/simple_map', OccupancyGrid, queue_size=10)
        self.lidar_sub = rospy.Subscriber('/f_scan', LaserScan, self.lidar_callback, queue_size=1)  # CHANGED: queue_size=1 để tránh tích lũy tin nhắn

        # Map message
        self.map_msg = OccupancyGrid()
        self.map_msg.header.frame_id = "map"
        self.map_msg.info.resolution = self.resolution
        self.map_msg.info.width = self.grid_width
        self.map_msg.info.height = self.grid_height
        self.map_msg.info.origin.position.x = self.origin_x
        self.map_msg.info.origin.position.y = self.origin_y
        self.map_msg.info.origin.orientation.w = 1.0

        # Pose robot bắt đầu ở giữa bản đồ
        self.robot_x = self.grid_width // 2
        self.robot_y = self.grid_height // 2
        self.robot_theta = 0.0

        # Tham số Hector SLAM
        self.max_iterations = 10  # CHANGED: Giảm số lần lặp để tăng tốc
        self.update_factor_free = 0.4
        self.update_factor_occupied = 0.6
        self.scan_match_threshold = 0.00005  # CHANGED: Tăng ngưỡng để hội tụ nhanh hơn
        self.max_accumulated_points = 1000  # CHANGED: Giảm số điểm tích lũy

    def world_to_map(self, wx, wy):
        mx = int(round((wx - self.origin_x) / self.resolution))
        my = int(round((wy - self.origin_y) / self.resolution))
        return mx, my

    def map_to_world(self, mx, my):
        wx = mx * self.resolution + self.origin_x
        wy = my * self.resolution + self.origin_y
        return wx, wy

    def lidar_callback(self, scan_msg):
        try:  # CHANGED: Thêm try-except để bắt lỗi
            start_time = rospy.Time.now()

            # Lấy dữ liệu từ LaserScan
            angle_min = scan_msg.angle_min
            angle_increment = scan_msg.angle_increment
            ranges = np.array(scan_msg.ranges)
            range_min = scan_msg.range_min
            range_max = scan_msg.range_max

            # Lọc dữ liệu không hợp lệ
            angles = angle_min + np.arange(len(ranges)) * angle_increment
            valid = (ranges > range_min) & (ranges < range_max)
            ranges = ranges[valid]
            angles = angles[valid]

            # Lọc nhiễu
            if len(ranges) > 7:
                ranges = medfilt(ranges, kernel_size=7)

            # Chuyển đổi sang tọa độ Cartesian
            x = ranges * np.cos(angles)
            y = ranges * np.sin(angles)

            # CHANGED: Tạm thời không tích lũy quét để kiểm tra lỗi
            combined_x, combined_y = x, y
            self.accumulated_scan = None  # Reset để tránh lỗi tích lũy

            # Ước lượng vị trí mới
            self.estimate_pose_hector(combined_x, combined_y)

            # Cập nhật bản đồ
            self.update_grid_hector(combined_x, combined_y)

            # Xuất bản bản đồ
            self.publish_map()
            self.save_map_image()

            duration = (rospy.Time.now() - start_time).to_sec()
            rospy.loginfo("Xử lý %d điểm trong %.3f giây", len(x), duration)

        except Exception as e:
            rospy.logerr("Lỗi trong lidar_callback: %s", str(e))

    def estimate_pose_hector(self, x_coords, y_coords):
        try:  # CHANGED: Thêm try-except
            grad_x, grad_y = self.calculate_gradients()
            dx, dy, dtheta = 0.0, 0.0, 0.0
            last_error = float('inf')

            for iteration in range(self.max_iterations):
                error = 0.0
                sum_dx, sum_dy, sum_dtheta = 0.0, 0.0, 0.0
                valid_points = 0

                cos_theta = np.cos(self.robot_theta + dtheta)
                sin_theta = np.sin(self.robot_theta + dtheta)
                
                for x, y in zip(x_coords, y_coords):
                    wx = x * cos_theta - y * sin_theta + (self.robot_x + dx - self.grid_width // 2) * self.resolution
                    wy = x * sin_theta + y * cos_theta + (self.robot_y + dy - self.grid_height // 2) * self.resolution
                    mx, my = self.world_to_map(wx, wy)
                    
                    if 0 <= mx < self.grid_width and 0 <= my < self.grid_height:
                        gx = grad_x[my, mx]
                        gy = grad_y[my, mx]
                        
                        if not (np.isnan(gx) or np.isnan(gy)):  # CHANGED: Kiểm tra NaN
                            J = np.array([
                                [1, 0, -x * sin_theta - y * cos_theta],
                                [0, 1, x * cos_theta - y * sin_theta]
                            ])
                            residual = np.array([gx, gy])
                            update = J.T @ residual
                            sum_dx += update[0]
                            sum_dy += update[1]
                            sum_dtheta += update[2]
                            error += residual.T @ residual
                            valid_points += 1

                if valid_points > 0:
                    norm_factor = 1.0 / valid_points
                    sum_dx *= norm_factor
                    sum_dy *= norm_factor
                    sum_dtheta *= norm_factor
                    error *= norm_factor

                    dx += sum_dx * 0.1
                    dy += sum_dy * 0.1
                    dtheta += sum_dtheta * 0.1

                    if abs(error - last_error) < self.scan_match_threshold:
                        break
                    last_error = error

            self.robot_x += dx / self.resolution
            self.robot_y += dy / self.resolution
            self.robot_theta += dtheta

        except Exception as e:
            rospy.logerr("Lỗi trong estimate_pose_hector: %s", str(e))

    def calculate_gradients(self):
        try:  # CHANGED: Thêm try-except
            # CHANGED: Tính gradient cho vùng lân cận
            padding = 50
            x_min = max(0, int(self.robot_x) - padding)
            x_max = min(self.grid_width, int(self.robot_x) + padding)
            y_min = max(0, int(self.robot_y) - padding)
            y_max = min(self.grid_height, int(self.robot_y) + padding)

            local_grid = self.grid[y_min:y_max, x_min:x_max]
            smoothed_grid = gaussian_filter(local_grid.astype(float), sigma=1.0)
            grad_y, grad_x = np.gradient(smoothed_grid)

            full_grad_x = np.zeros_like(self.grid, dtype=float)
            full_grad_y = np.zeros_like(self.grid, dtype=float)
            full_grad_x[y_min:y_max, x_min:x_max] = grad_x
            full_grad_y[y_min:y_max, x_min:x_max] = grad_y

            norm = np.sqrt(full_grad_x**2 + full_grad_y**2) + 1e-6
            full_grad_x /= norm
            full_grad_y /= norm

            return full_grad_x, full_grad_y

        except Exception as e:
            rospy.logerr("Lỗi trong calculate_gradients: %s", str(e))
            return np.zeros_like(self.grid), np.zeros_like(self.grid)

    def update_grid_hector(self, x_coords, y_coords):
        try:  # CHANGED: Thêm try-except
            cos_theta = np.cos(self.robot_theta)
            sin_theta = np.sin(self.robot_theta)
            robot_wx, robot_wy = self.map_to_world(int(round(self.robot_x)), int(round(self.robot_y)))

            # CHANGED: Lấy mẫu ngẫu nhiên nếu quá nhiều điểm
            if len(x_coords) > 500:
                indices = np.random.choice(len(x_coords), 500, replace=False)
                x_coords = x_coords[indices]
                y_coords = y_coords[indices]

            for x, y in zip(x_coords, y_coords):
                wx = x * cos_theta - y * sin_theta + robot_wx
                wy = x * sin_theta + y * cos_theta + robot_wy
                gx, gy = self.world_to_map(wx, wy)
                robot_gx, robot_gy = int(round(self.robot_x)), int(round(self.robot_y))
                
                if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
                    for px, py in bresenham(robot_gx, robot_gy, gx, gy):
                        if 0 <= px < self.grid_width and 0 <= py < self.grid_height:
                            self.grid[py, px] = max(0, min(100, self.grid[py, px] + self.update_factor_free * (0 - self.grid[py, px])))
                    self.grid[gy, gx] = max(0, min(100, self.grid[gy, gx] + self.update_factor_occupied * (100 - self.grid[gy, gx])))

        except Exception as e:
            rospy.logerr("Lỗi trong update_grid_hector: %s", str(e))

    def publish_map(self):
        try:  # CHANGED: Thêm try-except
            self.map_msg.header.stamp = rospy.Time.now()
            self.map_msg.data = self.grid.flatten().tolist()
            self.map_pub.publish(self.map_msg)
        except Exception as e:
            rospy.logerr("Lỗi trong publish_map: %s", str(e))

    def save_map_image(self):
        try:  # CHANGED: Thêm try-except
            image = np.zeros((self.grid_height, self.grid_width), dtype=np.uint8)
            image[self.grid == 0] = 200
            image[self.grid == 100] = 0
            image[self.grid == -1] = 50
            cv2.imwrite('/home/duc/Downloads/App_MIR100/static/build_map.png', image)
        except Exception as e:
            rospy.logerr("Lỗi trong save_map_image: %s", str(e))

    def run(self):
        rospy.spin()

if __name__ == '__main__':
    try:
        mapper = HectorMapper()
        mapper.run()
    except rospy.ROSInterruptException:
        pass