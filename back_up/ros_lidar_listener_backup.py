# ros_lidar_listener.py
import rospy
from sensor_msgs.msg import LaserScan
from PIL import Image, ImageDraw
import numpy as np
import tf
from geometry_msgs.msg import PointStamped

image_path = "App_MIR100/static/map_image.png"
img = Image.open(image_path)
IMAGE_WIDTH, IMAGE_HEIGHT = img.size
LIDAR_RANGE = 50 
POINT_SIZE = 1  

def process_lidar_data(msg, tf_listener, is_back):
    points = []
    if is_back:
        frame_id = "back_laser_link"
    else:
        frame_id = "front_laser_link"

    for i in range(len(msg.ranges)):
        r = msg.ranges[i]
        angle = i * msg.angle_increment + msg.angle_min

        if r < msg.range_max and r > msg.range_min and r < LIDAR_RANGE:
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

    all_x = [p[0] for p in points]
    all_y = [p[1] for p in points]
    min_x = min(all_x)
    max_x = max(all_x)
    min_y = min(all_y)
    max_y = max(all_y)

    width = max_x - min_x
    height = max_y - min_y

    if width == 0 or height == 0:
        return img 

    aspect_ratio = width / height
    image_aspect_ratio = IMAGE_WIDTH / IMAGE_HEIGHT

    if aspect_ratio > image_aspect_ratio:
        scale = IMAGE_WIDTH / width
    else:
        scale = IMAGE_HEIGHT / height
    for point_x, point_y in points:
        px = int((point_x - min_x) * scale) 
        py = IMAGE_HEIGHT - (int((point_y - min_y) * scale))
        draw.ellipse((px - POINT_SIZE, py - POINT_SIZE, px + POINT_SIZE, py + POINT_SIZE), fill=(255, 0, 0)) 

    return img

def scan_callback(msg, tf_listener, topic_name):
    try:
        if topic_name == "/f_scan":
            points_f = process_lidar_data(msg, tf_listener, is_back=False)
            img_f = create_lidar_image(points_f)
            img_f.save(f"App_MIR100/static/f_scan_image.png")
            rospy.loginfo("Lidar image for /f_scan created")

        elif topic_name == "/b_scan":
            points_b = process_lidar_data(msg, tf_listener, is_back=True)
            img_b = create_lidar_image(points_b)
            img_b.save(f"App_MIR100/static/b_scan_image.png")
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