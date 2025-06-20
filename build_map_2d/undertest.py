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
import tf

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
        self.log_odds_min = -5.0
        self.log_odds_max = 5.0
        self.log_odds_occupied = 0.6  # Adjust
        self.log_odds_free = -0.4  # Adjust
        self.grid = 0.01* np.ones((self.grid_height, self.grid_width), dtype=np.float64) #log odds

        # Lưu trữ scan trước đó để so sánh
        self.prev_scan_points = None

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
        self.robot_theta = 0.0  # Góc theo radian

        # Tham số ICP
        self.icp_max_iterations = 200
        self.icp_threshold = 0.00001
        self.icp_min_points = 50
        self.icp_distance_threshold = 0.5

        # Giới hạn chuyển động
        self.max_angular_change = 0.5

        # IMU (giả định) - Nếu không có IMU, bỏ qua phần này
        self.imu_sub = None  # rospy.Subscriber('/imu_topic', Imu, self.imu_callback)
        self.imu_data = None
        self.use_imu = False  # Set to True if you have IMU

        # Lọc vận tốc góc (ví dụ: trung bình trượt)
        self.angular_velocity_history = []
        self.angular_velocity_window = 10
        self.filtered_angular_velocity = 0.0

        # Occupancy parameters
        self.occ_threshold = 0.65 #threshold to draw obstacle
        self.free_threshold = 0.35 #threshold to clear obstacle

    def imu_callback(self, msg):
        # Giả định bạn có một topic IMU publish sensor_msgs/Imu
        self.imu_data = msg
        # self.imu_data.angular_velocity.z  <-- Lấy vận tốc góc trục Z

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

            # Nếu là scan đầu tiên, đặt ở giữa bản đồ
            if self.prev_scan_points is None:
                self.prev_scan_points = np.column_stack((x, y))
                self.update_grid(x, y)
                self.last_scan_time = rospy.Time.now()
            else:
                # Thực hiện ICP để tìm độ dịch chuyển
                current_points = np.column_stack((x, y))
                dt = (rospy.Time.now() - self.last_scan_time).to_sec()
                dx, dy, dtheta = self.icp_scan_matching(self.prev_scan_points, current_points, dt)

                # Cập nhật vị trí robot (Chỉ cập nhật góc quay)
                self.robot_theta += dtheta

                # Lưu ý: chuẩn hóa góc để tránh tràn số
                self.robot_theta = tf.transformations.euler_from_quaternion([0, 0, np.sin(self.robot_theta/2), np.cos(self.robot_theta/2)])[2]

                # Kiểm tra chất lượng ICP (ví dụ: số điểm hợp lệ)
                if len(current_points) > self.icp_min_points: # or other quality metric
                    self.update_grid(x, y) # Chỉ update khi ICP tốt
                else:
                    rospy.logwarn("ICP không hội tụ tốt, bỏ qua cập nhật grid")

                self.prev_scan_points = current_points
                self.last_scan_time = rospy.Time.now()

            # Xuất bản bản đồ
            self.publish_map()
            self.save_map_image()

            duration = (rospy.Time.now() - start_time).to_sec()
            rospy.loginfo(f"Xử lý {len(x)} điểm trong {duration:.3f} giây")

        except Exception as e:
            rospy.logerr(f"Lỗi trong lidar_callback: {str(e)}")

    def icp_scan_matching(self, prev_points, current_points, dt):
        """Thực hiện ICP để tìm độ dịch chuyển giữa 2 scan"""
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
            valid = distances.flatten() < self.icp_distance_threshold
            if np.sum(valid) < self.icp_min_points:
                rospy.logwarn("Không đủ điểm hợp lệ cho ICP")
                break

            valid_current = transformed_points[valid]
            valid_prev = prev_points_2d[indices[valid, 0]]

            # 3. Tính toán transform mới
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

        # 4.  Sử dụng thông tin IMU (nếu có) để cải thiện dtheta
        if self.use_imu and self.imu_data is not None:
            imu_angular_velocity = self.imu_data.angular_velocity.z
            # Lọc vận tốc góc
            self.angular_velocity_history.append(imu_angular_velocity)
            if len(self.angular_velocity_history) > self.angular_velocity_window:
                self.angular_velocity_history.pop(0)
            self.filtered_angular_velocity = np.mean(self.angular_velocity_history)

            # Thay thế dtheta từ ICP bằng dtheta từ IMU
            best_transform[2] = self.filtered_angular_velocity * dt
            rospy.loginfo("Sử dụng thông tin IMU để hiệu chỉnh dtheta")

        # Giới hạn thay đổi góc (quan trọng để tránh sai số lớn)
        if abs(best_transform[2]) > self.max_angular_change:
            best_transform[2] = max(min(best_transform[2], self.max_angular_change), -self.max_angular_change)
            rospy.logwarn("Giới hạn thay đổi góc")

        return best_transform[0], best_transform[1], best_transform[2]

    def update_grid(self, x_coords, y_coords):
        """Cập nhật bản đồ với các điểm scan mới"""
        try:
            cos_theta = np.cos(self.robot_theta)
            sin_theta = np.sin(self.robot_theta)
            robot_wx, robot_wy = self.map_to_world(int(round(self.robot_x)), int(round(self.robot_y)))

            # Giới hạn số điểm để tăng tốc độ xử lý
            if len(x_coords) > 1000:
                indices = np.random.choice(len(x_coords), 1000, replace=False)
                x_coords = x_coords[indices]
                y_coords = y_coords[indices]

            for x, y in zip(x_coords, y_coords):
                # Chuyển đổi sang tọa độ bản đồ
                wx = x * cos_theta - y * sin_theta + robot_wx
                wy = x * sin_theta + y * cos_theta + robot_wy
                gx, gy = self.world_to_map(wx, wy)
                robot_gx, robot_gy = int(round(self.robot_x)), int(round(self.robot_y))

                # Cập nhật bản đồ theo log odds
                if 0 <= gx < self.grid_width and 0 <= gy < self.grid_height:
                  # Cập nhật log-odds cho các ô trống dọc theo tia laser
                  for px, py in bresenham(robot_gx, robot_gy, gx, gy):
                    if 0 <= px < self.grid_width and 0 <= py < self.grid_height:
                      self.grid[py, px] += self.log_odds_free
                      self.grid[py, px] = max(min(self.grid[py, px], self.log_odds_max), self.log_odds_min)

                  # Cập nhật log-odds cho ô chứa chướng ngại vật
                  self.grid[gy, gx] += self.log_odds_occupied
                  self.grid[gy, gx] = max(min(self.grid[gy, gx], self.log_odds_max), self.log_odds_min)

        except Exception as e:
            rospy.logerr(f"Lỗi trong update_grid: {str(e)}")

    def publish_map(self):
        try:
            self.map_msg.header.stamp = rospy.Time.now()
            # Chuyển đổi log-odds về giá trị occupancy grid (0-100)
            occupancy_grid = np.zeros_like(self.grid, dtype=np.int8)
            occupancy_grid[self.grid > self.occ_threshold] = 100
            occupancy_grid[self.grid < self.free_threshold] = 0
            occupancy_grid[np.logical_and(self.grid >= self.free_threshold, self.grid <= self.occ_threshold)] = 50

            self.map_msg.data = occupancy_grid.flatten().tolist()
            self.map_pub.publish(self.map_msg)
        except Exception as e:
            rospy.logerr(f"Lỗi trong publish_map: {str(e)}")

    def save_map_image(self):
        try:
            # Tạo ảnh từ grid data
            image = np.zeros((self.grid_height, self.grid_width), dtype=np.uint8)

            # Đảm bảo self.grid nằm trong khoảng từ log_odds_min đến log_odds_max
            grid_normalized = np.clip(self.grid, self.log_odds_min, self.log_odds_max)

            # Chuyển đổi log-odds về khoảng 0-100 để hiển thị
            grid_display = ((grid_normalized - self.log_odds_min) / (self.log_odds_max - self.log_odds_min) * 100).astype(np.uint8)

            # Thay đổi ánh xạ giá trị để tăng độ tương phản
            image[grid_display < self.free_threshold] = 200  # Free space (light gray)
            image[grid_display > self.occ_threshold] = 0  # Occupied (black)
            image[np.logical_and(grid_display >= self.free_threshold, grid_display <= self.occ_threshold)] = 100  # Unknown (dark gray)

            # Thêm vị trí robot vào ảnh (điểm đen)
            robot_x = int(round(self.robot_x))
            robot_y = int(round(self.robot_y))
            cv2.circle(image, (robot_x, robot_y), 3, 0, -1)  # Điểm đen

            # Lấy timestamp hiện tại
            timestamp = rospy.Time.now().to_sec()

            # Tạo thư mục nếu chưa tồn tại
            import os
            output_dir = '/home/duc/Downloads/App_MIR100/static/Build_Map_2D'
            os.makedirs(output_dir, exist_ok=True)

            # Lưu ảnh với timestamp trong tên file
            filename = f'{output_dir}/hector_map_{timestamp:.3f}.png'
            cv2.imwrite(filename, image)

            rospy.loginfo(f"Đã lưu ảnh bản đồ: {filename}")
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