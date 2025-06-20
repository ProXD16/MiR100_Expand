# ros_lidar_listener.py
import rospy
from sensor_msgs.msg import LaserScan
from PIL import Image, ImageDraw
import numpy as np
import tf
from geometry_msgs.msg import PointStamped

image_path = "static/map_image.png"
try:
    img = Image.open(image_path)
    IMAGE_WIDTH, IMAGE_HEIGHT = img.size
    print("Map image successfully loaded.")
except FileNotFoundError:
    print(f"Error: Could not open image file at {image_path}")
    IMAGE_WIDTH, IMAGE_HEIGHT = 500, 500  
    img = Image.new('RGBA', (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
except Exception as e:
    print(f"Error opening image {image_path}: {e}")
    IMAGE_WIDTH, IMAGE_HEIGHT = 500, 500
    img = Image.new('RGBA', (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))

LIDAR_RANGE = 50  # Maximum range of the LiDAR to consider
POINT_SIZE = 1   # Size of the point to draw on the image
MANUAL_SCALE_FACTOR = 0.9  # Tweak this value to fine-tune scaling

def process_lidar_data(msg, tf_listener, is_back):
    points = []
    frame_id = "back_laser_link" if is_back else "front_laser_link"

    for i in range(len(msg.ranges)):
        r = msg.ranges[i]
        angle = i * msg.angle_increment + msg.angle_min

        if msg.range_min < r < msg.range_max and r < LIDAR_RANGE:
            x = r * np.cos(angle)
            y = r * np.sin(angle)

            point_stamped = PointStamped()
            point_stamped.header.frame_id = frame_id
            point_stamped.header.stamp = msg.header.stamp
            point_stamped.point.x = x
            point_stamped.point.y = y

            try:
                tf_listener.waitForTransform("map", frame_id, msg.header.stamp, rospy.Duration(1))
                if tf_listener.canTransform("map", frame_id, msg.header.stamp):
                    transformed_point = tf_listener.transformPoint("map", point_stamped)
                    points.append((transformed_point.point.x, transformed_point.point.y))
                else:
                    rospy.logwarn("Cannot transform point: Transformation not available.")
            except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException) as e:
                rospy.logwarn(f"TF error: {e}")
                continue
    return points

def create_lidar_image(points):
    img = Image.new('RGBA', (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if not points:
        return img

    # Map metadata (replace these with actual values from your map's YAML file)
    map_resolution = 0.05000000074505806  # meters per pixel
    map_origin_x = 0   # x-coordinate of the map's origin in meters
    map_origin_y = 0   # y-coordinate of the map's origin in meters

    for point_x, point_y in points:
        # Convert from meters to pixels
        px = int((point_x - map_origin_x) / map_resolution)
        py = int(IMAGE_HEIGHT - (point_y - map_origin_y) / map_resolution)

        # Draw the point
        draw.ellipse((px - POINT_SIZE, py - POINT_SIZE, px + POINT_SIZE, py + POINT_SIZE), fill=(255, 0, 0))

    return img

def scan_callback(msg, tf_listener, topic_name):
    try:
        if topic_name == "/f_scan":
            points_f = process_lidar_data(msg, tf_listener, is_back=False)
            img_f = create_lidar_image(points_f)
            img_f.save(f"static/f_scan_image.png")
            rospy.loginfo("Lidar image for /f_scan created")

        elif topic_name == "/b_scan":
            points_b = process_lidar_data(msg, tf_listener, is_back=True)
            img_b = create_lidar_image(points_b)
            img_b.save(f"static/b_scan_image.png")
            rospy.loginfo("Lidar image for /b_scan created")

    except Exception as e:
        rospy.logerr(f"Error processing {topic_name} data: {e}")
def listener():
    rospy.init_node('lidar_to_image', anonymous=True)
    tf_listener = tf.TransformListener()
    rospy.Subscriber("/f_scan", LaserScan, lambda msg: scan_callback(msg, tf_listener, "/f_scan"))
    rospy.Subscriber("/b_scan", LaserScan, lambda msg: scan_callback(msg, tf_listener, "/b_scan"))
    rospy.spin()

if __name__ == '__main__':
    listener()