import rospy
import tf2_ros
from nav_msgs.msg import Path, OccupancyGrid, GridCells
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import PoseWithCovarianceStamped
from PIL import Image, ImageDraw
import math, datetime, os, json
import numpy as np
import tf2_geometry_msgs 
from tf.transformations import euler_from_quaternion
import geometry_msgs.msg
from scipy.interpolate import CubicSpline, splrep, splev

OUTPUT_IMAGE_PATH = "static/combined_image.png"
OUTPUT_FIGURE_PATH = "static/map_for_figure.png"
MAP_IMAGE_PATH = "static/map_image.png"
ROBOT_IMAGE_PATH = "static/robot_image.png"
PATH_IMAGE_PATH = "static/path_image.png"
F_SCAN_IMAGE_PATH = "static/f_scan_image.png"
B_SCAN_IMAGE_PATH = "static/b_scan_image.png"
LINE_IMAGE_PATH = "static/line_image.png"  
COST_MAP_IMAGE_PATH = "static/cost_map_image.png"
GLOBAL_COSTMAP_IMAGE_PATH = "static/global_costmap_image.png"
IMAGE_WIDTH = None
IMAGE_HEIGHT = None
MAP_ORIGIN_X = None
MAP_ORIGIN_Y = None
MAP_RESOLUTION = None
LIDAR_RANGE = 50
POINT_SIZE = 1
JSON_FILE_PATH ="database_json/line_drawn.json"
DATA_DIR = "database_json"
STATUS_FILE = os.path.join(DATA_DIR, "mir_status.json")

def world_to_image(x, y):
    global IMAGE_WIDTH, IMAGE_HEIGHT, MAP_ORIGIN_X, MAP_ORIGIN_Y, MAP_RESOLUTION
    if MAP_ORIGIN_X is None or MAP_ORIGIN_Y is None or MAP_RESOLUTION is None or IMAGE_WIDTH is None or IMAGE_HEIGHT is None:
        # rospy.logwarn("Map information not yet received. Cannot transform coordinates.")
        return None, None
    px = int((x - MAP_ORIGIN_X) / MAP_RESOLUTION)
    py = int(IMAGE_HEIGHT - (y - MAP_ORIGIN_Y) / MAP_RESOLUTION)
    return px, py


def process_lidar_data(msg, tf_buffer, frame_id):
    points = []
    for i in range(len(msg.ranges)):
        r = msg.ranges[i]
        angle = i * msg.angle_increment + msg.angle_min
        if msg.range_min < r < msg.range_max and r < LIDAR_RANGE:
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            point_stamped = geometry_msgs.msg.PointStamped()
            point_stamped.header.frame_id = frame_id
            # point_stamped.header.stamp = rospy.Time(0) 
            point_stamped.header.stamp = msg.header.stamp
            point_stamped.point.x = x
            point_stamped.point.y = y
            point_stamped.point.z = 0  
            try:
                if tf_buffer.can_transform("map", frame_id, rospy.Time(0)):
                    transform = tf_buffer.lookup_transform("map", frame_id, msg.header.stamp)
                    transformed_point = tf2_geometry_msgs.do_transform_point(point_stamped, transform)
                    points.append((transformed_point.point.x, transformed_point.point.y))
                else:
                    # rospy.logwarn(f"Không thể transform {frame_id} sang map. Bỏ qua điểm này.")
                    pass
            except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
                # rospy.logwarn(f"Lỗi TF: {e}")
                pass
    return points

def create_lidar_image(points):
    img = Image.new('RGBA', (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if not points:
        return img
    for point_x, point_y in points:
        px, py = world_to_image(point_x, point_y)
        if px is not None and py is not None:
            draw.ellipse((px - POINT_SIZE, py - POINT_SIZE, px + POINT_SIZE, py + POINT_SIZE), fill=(255, 0, 0))
    return img


def path_callback(msg):
    global IMAGE_WIDTH, IMAGE_HEIGHT
    try:
        path_points = [(pose.pose.position.x, pose.pose.position.y) for pose in msg.poses]
        img = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for world_x, world_y in path_points:
            px, py = world_to_image(world_x, world_y)
            if px is not None and py is not None:
                draw.ellipse((px - 0.5, py - 0.5, px + 0.5, py + 0.5), fill=(0, 255, 255))
        img.save(PATH_IMAGE_PATH)
        # rospy.loginfo(f"Path image saved to {PATH_IMAGE_PATH}")
        combine_images()  
    except Exception as e:
        # rospy.logerr(f"Error processing path data: {e}")
        pass

def pose_callback(msg, tf_buffer):
    global IMAGE_WIDTH, IMAGE_HEIGHT
    if IMAGE_WIDTH is None or IMAGE_HEIGHT is None:
        # rospy.logwarn("Image dimensions not yet initialized. Skipping pose callback.")
        return
    try:
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        quaternion = (
            msg.pose.pose.orientation.x,
            msg.pose.pose.orientation.y,
            msg.pose.pose.orientation.z,
            msg.pose.pose.orientation.w
        )
        _, _, yaw = euler_from_quaternion(quaternion)
        img = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        px, py = world_to_image(x, y)
        if px is None or py is None:
            # rospy.logwarn(f"Could not convert robot pose ({x}, {y}) to image coordinates.  Map origin/resolution may be incorrect. px={px}, py={py}")
            return 
        rect_length = 0.8
        rect_width = 0.6
        tri_side = 0.3
        corners_world = [
            (x + rect_length / 2 * math.cos(yaw) - rect_width / 2 * math.sin(yaw),
             y + rect_length / 2 * math.sin(yaw) + rect_width / 2 * math.cos(yaw)),
            (x + rect_length / 2 * math.cos(yaw) + rect_width / 2 * math.sin(yaw),
             y + rect_length / 2 * math.sin(yaw) - rect_width / 2 * math.cos(yaw)),
            (x - rect_length / 2 * math.cos(yaw) + rect_width / 2 * math.sin(yaw),
             y - rect_length / 2 * math.sin(yaw) - rect_width / 2 * math.cos(yaw)),
            (x - rect_length / 2 * math.cos(yaw) - rect_width / 2 * math.sin(yaw),
             y - rect_length / 2 * math.sin(yaw) + rect_width / 2 * math.cos(yaw))
        ]
        corners_image = []
        all_corners_valid = True  
        for corner in corners_world:
            px_c, py_c = world_to_image(corner[0], corner[1])
            if px_c is None or py_c is None:
                # rospy.logwarn(f"Could not convert rectangle corner ({corner[0]}, {corner[1]}) to image coordinates.")
                all_corners_valid = False
                break 
            corners_image.append((px_c, py_c))
        if all_corners_valid:
            draw.polygon(corners_image, fill=(128, 128, 0, 102))
        else:
            # rospy.logwarn("Not all rectangle corners could be converted; skipping rectangle drawing.")
            pass
        triangle_points_world = [
            (x + tri_side * math.cos(yaw), y + tri_side * math.sin(yaw)),
            (x - tri_side / 2 * math.cos(yaw) + (tri_side * math.sqrt(3) / 2) * math.sin(yaw),
             y - tri_side / 2 * math.sin(yaw) - (tri_side * math.sqrt(3) / 2) * math.cos(yaw)),
            (x - tri_side / 2 * math.cos(yaw) - (tri_side * math.sqrt(3) / 2) * math.sin(yaw),
             y - tri_side / 2 * math.sin(yaw) + (tri_side * math.sqrt(3) / 2) * math.cos(yaw))
        ]
        triangle_points_image = []
        all_triangle_points_valid = True 
        for point in triangle_points_world:
            px_t, py_t = world_to_image(point[0], point[1])
            if px_t is None or py_t is None:
                # rospy.logwarn(f"Could not convert triangle point ({point[0]}, {point[1]}) to image coordinates.")
                all_triangle_points_valid = False
                break
            triangle_points_image.append((px_t, py_t))
        if all_triangle_points_valid:
            draw.polygon(triangle_points_image, fill=(0, 0, 255, 178))
        else:
            # rospy.logwarn("Not all triangle points could be converted; skipping triangle drawing.")
            pass
        img.save(ROBOT_IMAGE_PATH)
        # rospy.loginfo(f"Robot location image updated: {ROBOT_IMAGE_PATH}")
        combine_images()
    except Exception as e:
        # rospy.logerr(f"Error updating robot pose image: {e}")
        pass

def map_info_callback(map_data):
    global MAP_ORIGIN_X, MAP_ORIGIN_Y, MAP_RESOLUTION, IMAGE_WIDTH, IMAGE_HEIGHT
    MAP_ORIGIN_X = map_data.info.origin.position.x
    MAP_ORIGIN_Y = map_data.info.origin.position.y
    MAP_RESOLUTION = map_data.info.resolution
    IMAGE_WIDTH = map_data.info.width
    IMAGE_HEIGHT = map_data.info.height
    # rospy.loginfo("Received map info")
    combine_images() 

def lidar_callback(msg, tf_buffer, topic_name):
    try:
        frame_id = "back_laser_link" if topic_name == "/b_scan" else "front_laser_link"
        points = process_lidar_data(msg, tf_buffer, frame_id)
        if points:
            img_output = create_lidar_image(points)
            output_path = f"static/{topic_name.split('/')[-1]}_image.png"
            img_output.save(output_path)
            # rospy.loginfo(f"Lidar image for {topic_name} saved to {output_path}")
            combine_images() 
        else:
            # rospy.logwarn(f"No valid Lidar points for {topic_name}, skipping image save.")
            pass

    except Exception as e:
        # rospy.logerr(f"Error processing {topic_name} data: {e}")
        pass

def costmap_callback(msg, tf_buffer):
    global IMAGE_WIDTH, IMAGE_HEIGHT, MAP_ORIGIN_X, MAP_ORIGIN_Y, MAP_RESOLUTION
    try:
        if IMAGE_WIDTH is None or IMAGE_HEIGHT is None:
            # rospy.logwarn("Image dimensions not yet initialized. Skipping costmap callback.")
            return
        if not msg.cells:
            # rospy.logwarn("No costmap cells received, returning transparent background.")
            img = Image.new('RGBA', (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
            img.save(COST_MAP_IMAGE_PATH)
            # rospy.loginfo(f"Costmap image saved (transparent) to {COST_MAP_IMAGE_PATH}")
            combine_images()
            return
        img = Image.new('RGBA', (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for cell in msg.cells:
            point_stamped = geometry_msgs.msg.PointStamped()
            point_stamped.header = msg.header
            point_stamped.point.x = cell.x
            point_stamped.point.y = cell.y
            point_stamped.point.z = 0
            try:
                transform = tf_buffer.lookup_transform("map", msg.header.frame_id, msg.header.stamp,rospy.Duration(1.0))
                transformed_point = tf2_geometry_msgs.do_transform_point(point_stamped, transform)
                px, py = world_to_image(transformed_point.point.x, transformed_point.point.y)
                if px is not None and py is not None:
                    draw.ellipse((px - 0.5, py - 0.5, px + 0.5, py + 0.5), fill=(150, 111, 214, 128))
            except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
                # rospy.logwarn(f"TF error: {e}")
                continue
        img.save(COST_MAP_IMAGE_PATH)
        # rospy.loginfo(f"Costmap image saved to {COST_MAP_IMAGE_PATH}")
        combine_images()
    except Exception as e:
        # rospy.logerr(f"Error processing costmap data: {e}")
        pass

def combine_images():
    try:
        map_img = Image.open(MAP_IMAGE_PATH).convert("RGBA")
        robot_img = Image.open(ROBOT_IMAGE_PATH).convert("RGBA")
        path_img = Image.open(PATH_IMAGE_PATH).convert("RGBA")
        f_scan_img = Image.open(F_SCAN_IMAGE_PATH).convert("RGBA")
        b_scan_img = Image.open(B_SCAN_IMAGE_PATH).convert("RGBA")
        create_map_for_figure()
        map_img.paste(path_img, (0, 0), path_img)
        map_img.paste(robot_img, (0, 0), robot_img)
        map_img.paste(f_scan_img, (0, 0), f_scan_img)
        map_img.paste(b_scan_img, (0, 0), b_scan_img)
        map_img.save(OUTPUT_IMAGE_PATH)
        # rospy.loginfo(f"Combined image saved to {OUTPUT_IMAGE_PATH}")
    except FileNotFoundError as e:
        pass
    except Exception as e:
        pass

def create_map_for_figure():
    map_img = Image.open(MAP_IMAGE_PATH).convert("RGBA")
    global_costmap_img = Image.open(GLOBAL_COSTMAP_IMAGE_PATH).convert("RGBA")
    map_img.paste(global_costmap_img, (0, 0), global_costmap_img)
    map_img.save(OUTPUT_FIGURE_PATH)
    # rospy.loginfo(f"Figure for draw mode saved to {OUTPUT_FIGURE_PATH}")

def mir_status_callback(msg):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)  
        with open(STATUS_FILE, 'w') as f:
            data = {
                "timestamp": datetime.now().isoformat(),
                "data": json.loads(msg.data) 
            }
            json.dump(data, f, indent=2)
        rospy.loginfo(f"Updated status in {STATUS_FILE}")
    except json.JSONDecodeError:
        rospy.logerr(f"Invalid JSON format in message: {msg.data}")
    except Exception as e:
        rospy.logerr(f"Error processing message: {e}")

def main():
    if not rospy.core.is_initialized():
        rospy.init_node('image_combiner_node', anonymous=True)
    
    tf_buffer = tf2_ros.Buffer(cache_time=rospy.Duration(50.0)) 
    tf_listener = tf2_ros.TransformListener(tf_buffer)
    rospy.Subscriber("/map", OccupancyGrid, map_info_callback)
    rospy.Subscriber("/move_base_node/SBPLLatticePlanner/plan", Path, path_callback)
    rospy.Subscriber("/f_scan", LaserScan, lambda msg: lidar_callback(msg, tf_buffer, "/f_scan"))
    rospy.Subscriber("/b_scan", LaserScan, lambda msg: lidar_callback(msg, tf_buffer, "/b_scan"))
    rospy.Subscriber("/amcl_pose", PoseWithCovarianceStamped, lambda msg: pose_callback(msg, tf_buffer))
    rospy.Subscriber("/move_base_node/traffic_costmap/inflated_obstacles", GridCells, lambda msg: costmap_callback(msg, tf_buffer))
    rospy.spin() 

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass