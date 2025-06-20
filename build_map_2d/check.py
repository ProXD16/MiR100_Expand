#!/usr/bin/env python
import rospy
import numpy as np
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid
import cv2
from bresenham import bresenham
import math
from scipy.signal import medfilt
from sklearn.neighbors import NearestNeighbors

class HectorMapper:
    def __init__(self):
        rospy.init_node('hector_mapper', anonymous=True)

        # Thông số bản đồ
        self.map_width = 50.0  # meters
        self.map_height = 50.0  # meters
        self.resolution = 0.05  # meters/pixel
        self.grid_width = int(self.map_width / self.resolution)
        self.grid_height = int(self.map_height / self.resolution)
        self.origin_x = -self.map_width / 2
        self.origin_y = -self.map_height / 2

        # Occupancy grid
        self.grid = -1 * np.ones((self.grid_height, self.grid_width), dtype=np.int8)
        self.quality_grid = np.zeros((self.grid_height, self.grid_width))

        # Lưu trữ scan trước đó để so sánh
        self.prev_scan_points = None
        self.prev_robot_pose = None  # (x, y, theta) in map coordinates

        # Publisher và Subscriber
        self.map_pub = rospy.Publisher('/simple_map', OccupancyGrid, queue_size=10)
        self.lidar_sub = rospy.Subscriber('/f_scan', LaserScan, self.lidar_callback, queue_size=1)

        # Map message
        self.map_msg = OccupancyGrid()
        self.map_msg.header.frame_id = "map"
        self.map_msg.info.resolution = self.resolution
        self.map_msg.info.width = self.grid_width
        self.map_msg.info.height = self.grid_height
        self.map_msg.info.origin.position.x = self.origin_x
        self.map_msg.info.origin.position.y = self.origin_y
        self.map_msg.info.origin.orientation.w = 1.0

        # Pose robot bắt đầu ở giữa bản đồ (pixel coordinates)
        self.robot_x = self.grid_width // 2
        self.robot_y = self.grid_height // 2
        self.robot_theta = 0.0

        # Tham số ICP
        self.icp_max_iterations = 50 # Tăng số lượng iterations
        self.icp_threshold = 0.0001 # Giảm ngưỡng hội tụ
        self.icp_min_points = 20 # Tăng số lượng điểm tối thiểu
        self.icp_distance_threshold = 0.8 # Tăng ngưỡng khoảng cách cho điểm tương ứng

        # Giới hạn chuyển động
        self.max_translation = 1.0 # mét
        self.max_angular_change = 0.5  # radian (giới hạn thay đổi góc tối đa giữa các lần quét)
        self.max_angular_velocity = 1.0 # radian/s (giới hạn tốc độ góc)
        self.last_scan_time = rospy.Time.now()

    def world_to_map(self, wx, wy):
        mx = int(round((wx - self.origin_x) / self.resolution))
        my = int(round((wy - self.origin_y) / self.resolution))
        return mx, my

    def map_to_world(self, mx, my):
        wx = mx * self.resolution + self.origin_x
        wy = my * self.resolution + self.origin_y
        return wx, wy

    def lidar_callback(self, scan_msg):
        try:
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

            # Chuyển đổi sang tọa độ Cartesian (robot frame)
            x = ranges * np.cos(angles)
            y = ranges * np.sin(angles)

            current_time = rospy.Time.now()
            dt = (current_time - self.last_scan_time).to_sec()

            # Nếu là scan đầu tiên, đặt ở giữa bản đồ
            if self.prev_scan_points is None:
                self.prev_scan_points = np.column_stack((x, y))
                self.prev_robot_pose = (self.robot_x, self.robot_y, self.robot_theta)
                self.update_grid(x, y)
            else:
                # Thực hiện ICP để tìm độ dịch chuyển
                current_points = np.column_stack((x, y))
                dx, dy, dtheta = self.icp_scan_matching(self.prev_scan_points, current_points)

                #Giới hạn chuyển động
                translation = np.sqrt(dx**2 + dy**2)
                if translation > self.max_translation:
                  scale = self.max_translation / translation
                  dx *= scale
                  dy *= scale
                  rospy.logwarn("Giới hạn chuyển động tịnh tiến")

                #Giới hạn thay đổi góc
                if abs(dtheta) > self.max_angular_change:
                  dtheta = max(min(dtheta, self.max_angular_change), -self.max_angular_change)
                  rospy.logwarn("Giới hạn thay đổi góc")
                #Giới hạn vận tốc góc
                angular_velocity = dtheta / dt
                if abs(angular_velocity) > self.max_angular_velocity:
                  dtheta = max(min(angular_velocity, self.max_angular_velocity), -self.max_angular_velocity) * dt
                  rospy.logwarn("Giới hạn vận tốc góc")

                # Cập nhật vị trí robot
                self.robot_x += dx / self.resolution
                self.robot_y += dy / self.resolution
                self.robot_theta += dtheta

                # Lưu scan hiện tại thành scan trước đó
                self.prev_scan_points = current_points
                self.prev_robot_pose = (self.robot_x, self.robot_y, self.robot_theta)

                # Cập nhật bản đồ với vị trí mới
                self.update_grid(x, y)

            self.last_scan_time = current_time
            # Xuất bản bản đồ
            self.publish_map()
            self.save_map_image()

            duration = (rospy.Time.now() - start_time).to_sec()
            rospy.loginfo(f"Xử lý {len(x)} điểm trong {duration:.3f} giây")

        except Exception as e:
            rospy.logerr(f"Lỗi trong lidar_callback: {str(e)}")

    def icp_scan_matching(self, prev_points, current_points):
        """
        Thực hiện ICP để tìm độ dịch chuyển giữa 2 scan
        Trả về (dx, dy, dtheta) trong đơn vị mét và radian
        """
        best_transform = np.zeros(3)  # (dx, dy, dtheta)
        prev_points_2d = prev_points.copy()
        current_points_2d = current_points.copy()

        # Chuẩn bị KD-tree cho tìm kiếm lân cận
        nbrs = NearestNeighbors(n_neighbors=1, algorithm='kd_tree').fit(prev_points_2d)

        for iteration in range(self.icp_max_iterations):
            # 1. Biến đổi current points theo transform hiện tại
            cos_theta = np.cos(best_transform[2])
            sin_theta = np.sin(best_transform[2])

            transformed_points = current_points_2d.copy()
            transformed_points[:, 0] = (cos_theta * current_points_2d[:, 0] -
                                      sin_theta * current_points_2d[:, 1] + best_transform[0])
            transformed_points[:, 1] = (sin_theta * current_points_2d[:, 0] +
                                      cos_theta * current_points_2d[:, 1] + best_transform[1])

            # 2. Tìm điểm tương ứng
            distances, indices = nbrs.kneighbors(transformed_points)

            # Lọc các điểm có khoảng cách quá xa
            valid = distances.flatten() < self.icp_distance_threshold  # Ngưỡng khoảng cách lớn hơn
            if np.sum(valid) < self.icp_min_points:
                break

            valid_current = transformed_points[valid]
            valid_prev = prev_points_2d[indices[valid, 0]]

            # 3. Tính toán transform mới
            # Tính trung bình của các điểm
            mean_current = np.mean(valid_current, axis=0)
            mean_prev = np.mean(valid_prev, axis=0)

            # Tính covariance matrix
            cov = (valid_current - mean_current).T @ (valid_prev - mean_prev)

            # SVD để tìm rotation
            U, _, Vt = np.linalg.svd(cov)
            R = Vt.T @ U.T

            # Đảm bảo ma trận xoay hợp lệ
            if np.linalg.det(R) < 0:
                R[:, -1] *= -1

            # Tính các thành phần của transform
            dtheta = np.arctan2(R[1, 0], R[0, 0])
            dx = mean_prev[0] - (mean_current[0] * np.cos(dtheta) - mean_current[1] * np.sin(dtheta))
            dy = mean_prev[1] - (mean_current[0] * np.sin(dtheta) + mean_current[1] * np.cos(dtheta))

            # Cập nhật transform
            best_transform[0] += dx
            best_transform[1] += dy
            best_transform[2] += dtheta

            # Kiểm tra điều kiện dừng
            if np.abs(dx) < self.icp_threshold and \
               np.abs(dy) < self.icp_threshold and \
               np.abs(dtheta) < self.icp_threshold:
                break

        return best_transform[0], best_transform[1], best_transform[2]

    def update_grid(self, x_coords, y_coords):
        """Cập nhật bản đồ với các điểm scan mới"""
        try:
            cos_theta = np.cos(self.robot_theta)
            sin_theta = np.sin(self.robot_theta)
            robot_wx, robot_wy = self.map_to_world(int(round(self.robot_x)), int(round(self.robot_y)))

            # Giới hạn số điểm để tăng tốc độ xử lý
            if len(x_coords) > 500:
                indices = np.random.choice(len(x_coords), 500, replace=False)
                x_coords = x_coords[indices]
                y_coords = y_coords[indices]

            for x, y in zip(x_coords, y_coords):
                # Chuyển đổi sang tọa độ bản đồ
                wx = x * cos_theta - y * sin_theta + robot_wx
                wy = x * sin_theta + y * cos_theta + robot_wy
                gx, gy = self.world_to_map(wx, wy)
                robot_gx, robot_gy = int(round(self.robot_x)), int(round(self.robot_y))

                # Cập nhật các ô dọc theo tia laser
                if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
                    for px, py in bresenham(robot_gx, robot_gy, gx, gy):
                        if 0 <= px < self.grid_width and 0 <= py < self.grid_height:
                            self.grid[py, px] = max(0, min(100, self.grid[py, px] + 0.4 * (0 - self.grid[py, px])))

                    # Cập nhật ô chứa chướng ngại vật
                    self.grid[gy, gx] = max(0, min(100, self.grid[gy, gx] + 0.6 * (100 - self.grid[gy, gx])))

        except Exception as e:
            rospy.logerr(f"Lỗi trong update_grid: {str(e)}")

    def publish_map(self):
        try:
            self.map_msg.header.stamp = rospy.Time.now()
            self.map_msg.data = self.grid.flatten().tolist()
            self.map_pub.publish(self.map_msg)
        except Exception as e:
            rospy.logerr(f"Lỗi trong publish_map: {str(e)}")

    def save_map_image(self):
        try:
            image = np.zeros((self.grid_height, self.grid_width), dtype=np.uint8)
            image[self.grid == 0] = 200  # Free space
            image[self.grid == 100] = 0  # Occupied
            image[self.grid == -1] = 50  # Unknown
            cv2.imwrite('/home/duc/Downloads/App_MIR100/static/hector_map.png', image)
        except Exception as e:
            rospy.logerr(f"Lỗi trong save_map_image: {str(e)}")

    def run(self):
        rospy.spin()

if __name__ == '__main__':
    try:
        mapper = HectorMapper()
        mapper.run()
    except rospy.ROSInterruptException:
        pass