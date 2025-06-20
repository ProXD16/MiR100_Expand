#!/usr/bin/env python

import rospy
import numpy as np
import math
import cv2
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import Header
from geometry_msgs.msg import Pose
from scipy.signal import medfilt # Import the median filter

# Simple utility function for applying transformation
def apply_transform(points, dx, dy, dtheta):
    """Applies a 2D transformation (dx, dy, dtheta) to a set of points."""
    # Create rotation matrix
    rotation = np.array([
        [np.cos(dtheta), -np.sin(dtheta)],
        [np.sin(dtheta), np.cos(dtheta)]
    ])
    # Apply rotation and translation
    transformed_points = (rotation @ points.T).T + np.array([dx, dy])
    return transformed_points

# Bresenham-like raycasting (simplified)
def get_line_cells(x0, y0, x1, y1):
    """Generates cells along a line using a simplified DDA algorithm."""
    cells = []
    dx = x1 - x0
    dy = y1 - y0
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        return cells

    x_inc = dx / steps
    y_inc = dy / steps

    x = x0
    y = y0
    for _ in range(int(steps)):
        cells.append((int(round(x)), int(round(y))))
        x += x_inc
        y += y_inc
    return cells

class HectorMapping:
    def __init__(self):
        rospy.init_node('hector_mapping', anonymous=True)

        # --- Map Parameters ---
        self.map_resolution = 0.05  # meters per cell
        self.map_size = 500        # cells (500*0.05 = 25 meters)
        self.map_center = self.map_size / 2  # Map center in cells
        self.map_half_size_m = (self.map_size * self.map_resolution) / 2
        
        # Map data (log-odds)
        # Initialize map with neutral value (e.g., 0 or a small value for unknown)
        # Let's use 0 for unknown/unobserved initially
        self.map = np.zeros((self.map_size, self.map_size), dtype=np.float32)
        self.log_odds_min = -5.0  # Lower bound for log odds (more free)
        self.log_odds_max = 5.0   # Upper bound for log odds (more occupied)
        self.log_odds_occupied = 1.0  # Log odds to add for occupied
        self.log_odds_free = -0.5    # Log odds to subtract for free

        # --- Robot Pose Estimation ---
        # Initial pose (centered in the map frame)
        self.robot_pose_x = 0.0
        self.robot_pose_y = 0.0
        self.robot_pose_theta = 0.0

        # --- Scan Matching Parameters (Simple Search) ---
        self.scan_match_search_range_x = 0.2   # meters
        self.scan_match_search_range_y = 0.2   # meters
        self.scan_match_search_range_theta = 0.1 # radians
        self.scan_match_search_step_x = 0.05   # meters
        self.scan_match_search_step_y = 0.05   # meters
        self.scan_match_search_step_theta = 0.01 # radians  !!! REDUCED STEP SIZE FOR THETA !!!

        # --- Median Filter Parameters ---
        self.median_filter_window = 5 # Adjust as needed

        # --- ROS Interfaces ---
        self.scan_subscriber = rospy.Subscriber('/f_scan', LaserScan, self.lidar_callback)
        self.map_publisher = rospy.Publisher('/simple_map', OccupancyGrid, queue_size=1)

        # --- Saving ---
        self.save_path = '/home/duc/Downloads/App_MIR100/static/hector_map.png'
        self.save_counter = 0
        self.save_frequency = 20 # Save every 20 scans

    def world_to_map_coords(self, x, y):
        """Converts world coordinates (meters) to map grid coordinates (cells)."""
        map_x = int(round(x / self.map_resolution + self.map_center))
        map_y = int(round(y / self.map_resolution + self.map_center))
        return map_x, map_y

    def map_to_world_coords(self, map_x, map_y):
        """Converts map grid coordinates (cells) to world coordinates (meters)."""
        x = (map_x - self.map_center) * self.map_resolution
        y = (map_y - self.map_center) * self.map_resolution
        return x, y

    def get_map_value(self, map_x, map_y):
        """Safely gets the map value at a given cell coordinate."""
        if 0 <= map_x < self.map_size and 0 <= map_y < self.map_size:
            return self.map[map_y, map_x] # Note: NumPy uses (row, col) -> (y, x)
        return self.log_odds_min # Return minimum log odds for out-of-bounds

    def lidar_callback(self, scan_msg):
        
        # Convert laser scan points to robot frame Cartesian coordinates
        ranges = np.array(scan_msg.ranges)

        # Apply median filter to the ranges
        ranges = medfilt(ranges, kernel_size=self.median_filter_window)

        angles = np.linspace(scan_msg.angle_min, scan_msg.angle_max, len(ranges))
        
        # Filter invalid points
        valid_idx = np.isfinite(ranges) & (ranges > scan_msg.range_min) & (ranges < scan_msg.range_max)
        points = np.array([ranges[valid_idx] * np.cos(angles[valid_idx]),
                           ranges[valid_idx] * np.sin(angles[valid_idx])]).T

        if len(points) == 0:
             rospy.logwarn("Received empty scan after filtering.")
             return

        # --- Scan-to-Map Matching (Simplified Hector) ---
        # Search for the best pose shift (dx, dy, dtheta) relative to the *previous* pose
        best_score = -float('inf')
        best_dx = 0.0
        best_dy = 0.0
        best_dtheta = 0.0

        # Iterate through potential pose changes
        for dx in np.arange(-self.scan_match_search_range_x, self.scan_match_search_range_x + self.scan_match_search_step_x, self.scan_match_search_step_x):
            for dy in np.arange(-self.scan_match_search_range_y, self.scan_match_search_range_y + self.scan_match_search_step_y, self.scan_match_search_step_y):
                 for dtheta in np.arange(-self.scan_match_search_range_theta, self.scan_match_search_range_theta + self.scan_match_search_step_theta, self.scan_match_search_step_theta):
                    # Calculate the hypothetical new pose
                    test_pose_x = self.robot_pose_x + dx * math.cos(self.robot_pose_theta) - dy * math.sin(self.robot_pose_theta)
                    test_pose_y = self.robot_pose_y + dx * math.sin(self.robot_pose_theta) + dy * math.cos(self.robot_pose_theta)
                    test_pose_theta = self.robot_pose_theta + dtheta

                    # Project current scan points into the map using the test pose
                    rotated_points = apply_transform(points, 0, 0, test_pose_theta - self.robot_pose_theta)
                    translated_points = rotated_points + np.array([test_pose_x, test_pose_y])

                    # Calculate score based on map alignment (higher score = better fit)
                    current_score = 0
                    for p_x, p_y in translated_points:
                        map_x, map_y = self.world_to_map_coords(p_x, p_y)
                        current_score += self.get_map_value(map_x, map_y) # Sum up log-odds values

                    if current_score > best_score:
                         best_score = current_score
                         best_dx = dx
                         best_dy = dy
                         best_dtheta = dtheta

        # Update robot pose based on best found delta
        self.robot_pose_x += best_dx * math.cos(self.robot_pose_theta) - best_dy * math.sin(self.robot_pose_theta)
        self.robot_pose_y += best_dy * math.sin(self.robot_pose_theta) + best_dy * math.cos(self.robot_pose_theta)
        self.robot_pose_theta += best_dtheta

        rospy.loginfo(f"Estimated Pose: ({self.robot_pose_x:.2f}, {self.robot_pose_y:.2f}, {math.degrees(self.robot_pose_theta):.2f} deg)")

        # --- Update Map (using Log-Odds) ---
        # Robot's position in map coordinates
        robot_map_x, robot_map_y = self.world_to_map_coords(self.robot_pose_x, self.robot_pose_y)

        # Transform points to global coordinates using updated pose
        rotated_points = apply_transform(points, 0, 0, self.robot_pose_theta)
        global_points = rotated_points + np.array([self.robot_pose_x, self.robot_pose_y])

        # Update occupied cells
        for p_x, p_y in global_points:
            map_x, map_y = self.world_to_map_coords(p_x, p_y)
            if 0 <= map_x < self.map_size and 0 <= map_y < self.map_size:
                self.map[map_y, map_x] += self.log_odds_occupied
                self.map[map_y, map_x] = np.clip(self.map[map_y, map_x], self.log_odds_min, self.log_odds_max)

        # Update free cells using simplified raycasting
        for p_x, p_y in global_points:
            map_x, map_y = self.world_to_map_coords(p_x, p_y)
            
            # Get cells along the ray from robot to the point
            ray_cells = get_line_cells(robot_map_x, robot_map_y, map_x, map_y)
            
            # Update cells along the ray (excluding the endpoint itself)
            for cell_x, cell_y in ray_cells[:-1]: # Exclude the last cell (occupied cell)
                if 0 <= cell_x < self.map_size and 0 <= cell_y < self.map_size:
                    self.map[cell_y, cell_x] += self.log_odds_free
                    self.map[cell_y, cell_x] = np.clip(self.map[cell_y, cell_x], self.log_odds_min, self.log_odds_max)


        # --- Publish Map ---
        self.publish_map()

        # --- Save Map (periodically) ---
        self.save_counter += 1
        if self.save_counter >= self.save_frequency:
            self.save_map()
            self.save_counter = 0


    def publish_map(self):
        """Publishes the OccupancyGrid message."""
        map_msg = OccupancyGrid()
        map_msg.header = Header()
        map_msg.header.stamp = rospy.Time.now()
        map_msg.header.frame_id = "map"

        map_msg.info.resolution = self.map_resolution
        map_msg.info.width = self.map_size
        map_msg.info.height = self.map_size
        
        # Origin based on map center and resolution
        map_msg.info.origin.position.x = -self.map_half_size_m
        map_msg.info.origin.position.y = -self.map_half_size_m
        map_msg.info.origin.position.z = 0.0
        map_msg.info.origin.orientation.w = 1.0

        # Convert log-odds map to OccupancyGrid data format (-1, 0, 100)
        data = np.full_like(self.map, -1, dtype=np.int8) # Default to unknown
        # Thresholds for classification
        threshold_occupied = 0.5 # Log-odds value corresponding to P > 0.5
        threshold_free = -0.5    # Log-odds value corresponding to P < 0.5

        # Convert log-odds to probability for thresholding (simple sign check is also fine)
        # prob = 1 / (1 + np.exp(-self.map))
        # occupied_mask = prob > 0.65 # Threshold for occupied
        # free_mask = prob < 0.35     # Threshold for free

        occupied_mask = self.map > 0.5 # Use simple log-odds threshold
        free_mask = self.map < -0.5    # Use simple log-odds threshold

        data[occupied_mask] = 100
        data[free_mask] = 0

        # Flatten and reverse y-axis for ROS OccupancyGrid format
        map_msg.data = data.flatten().tolist()
        
        self.map_publisher.publish(map_msg)

    def save_map(self):
        """Saves the current map as a PNG image."""
        # Convert log-odds map to a 0-255 grayscale image
        # Map: min_log_odds -> max_log_odds
        # Image: 0 (black) -> 255 (white)
        
        # Normalize log-odds to 0-1 range
        normalized_map = (self.map - self.log_odds_min) / (self.log_odds_max - self.log_odds_min)
        normalized_map = np.clip(normalized_map, 0.0, 1.0) # Ensure values are within 0-1

        # Scale to 0-255 for grayscale
        image = (normalized_map * 255).astype(np.uint8)

        # Convert to BGR for OpenCV (or keep as grayscale)
        # image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        # Flip vertically because OpenCV origin is top-left, ROS map is bottom-left
        image = cv2.flip(image, 0)

        cv2.imwrite(self.save_path, image)
        rospy.loginfo(f"Map saved to: {self.save_path}")

    def run(self):
        rospy.spin()

if __name__ == '__main__':
    try:
        hector_mapping = HectorMapping()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass