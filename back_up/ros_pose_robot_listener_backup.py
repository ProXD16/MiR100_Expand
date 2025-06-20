#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped
from PIL import Image, ImageDraw
from nav_msgs.msg import OccupancyGrid
import math
import tf
import tf.transformations

OUTPUT_IMAGE_PATH = "App_MIR100/static/robot_image.png"
MAP_IMAGE_PATH = "App_MIR100/static/map_image.png"
IMAGE_WIDTH = None
IMAGE_HEIGHT = None

def world_to_image(x, y):
    """Chuyển đổi tọa độ thế giới sang tọa độ ảnh."""
    global IMAGE_WIDTH, IMAGE_HEIGHT, MAP_ORIGIN_X, MAP_ORIGIN_Y, MAP_RESOLUTION
    if MAP_ORIGIN_X is None or MAP_ORIGIN_Y is None or MAP_RESOLUTION is None or IMAGE_WIDTH is None or IMAGE_HEIGHT is None:
        rospy.logwarn("Map information or image dimensions are not initialized.")
        return None, None

    px = int((x - MAP_ORIGIN_X) / MAP_RESOLUTION)
    py = int((y - MAP_ORIGIN_Y) / MAP_RESOLUTION)
    py = IMAGE_HEIGHT - py  # Lật hệ tọa độ
    rospy.loginfo(f"World to Image: World X:{x}, World Y:{y}, Image X:{px}, Image Y:{py}, OriginX:{MAP_ORIGIN_X}, OriginY:{MAP_ORIGIN_Y}, Resolution:{MAP_RESOLUTION}")
    return px, py


def pose_callback(msg, tf_listener):
    global IMAGE_WIDTH, IMAGE_HEIGHT
    try:
        if IMAGE_WIDTH is None or IMAGE_HEIGHT is None:
            rospy.logwarn("Map info not yet received. Skipping pose update.")
            return
        img = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        (trans, rot) = tf_listener.lookupTransform('/map', '/base_link', rospy.Time(0))
        x, y = trans[0], trans[1]
        _, _, yaw = tf.transformations.euler_from_quaternion(rot)
        px, py = world_to_image(x, y)
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
        corners_image = [world_to_image(corner[0], corner[1]) for corner in corners_world]
        draw.polygon(corners_image, fill=(128, 128, 128, 102)) 

        triangle_points_world = [
            (x + tri_side * math.cos(yaw), y + tri_side * math.sin(yaw)),
            (x - tri_side / 2 * math.cos(yaw) + (tri_side * math.sqrt(3) / 2) * math.sin(yaw),
             y - tri_side / 2 * math.sin(yaw) - (tri_side * math.sqrt(3) / 2) * math.cos(yaw)),
            (x - tri_side / 2 * math.cos(yaw) - (tri_side * math.sqrt(3) / 2) * math.sin(yaw),
             y - tri_side / 2 * math.sin(yaw) + (tri_side * math.sqrt(3) / 2) * math.cos(yaw))
        ]
        triangle_points_image = [world_to_image(point[0], point[1]) for point in triangle_points_world]
        draw.polygon(triangle_points_image, fill=(0, 0, 255, 178))  
        img.save(OUTPUT_IMAGE_PATH)
        rospy.loginfo(f"Robot location image updated: {OUTPUT_IMAGE_PATH}")

    except Exception as e:
        rospy.logerr(f"There was an error in displaying path or transformation to img {e}")

def map_info_callback(map_data):
    """Callback function xử lý thông tin bản đồ."""
    global MAP_ORIGIN_X, MAP_ORIGIN_Y, MAP_RESOLUTION, IMAGE_WIDTH, IMAGE_HEIGHT

    MAP_ORIGIN_X = map_data.info.origin.position.x
    MAP_ORIGIN_Y = map_data.info.origin.position.y
    MAP_RESOLUTION = map_data.info.resolution
    IMAGE_WIDTH = map_data.info.width
    IMAGE_HEIGHT = map_data.info.height

    rospy.loginfo("Received map info")

    try:
        img = Image.open(MAP_IMAGE_PATH)
        img.close()

    except Exception as e:
        rospy.logerr(f"validate image loading on /map exception, potential IO with source{e}")

def listener():
    rospy.init_node('robot_location_to_image', anonymous=True)
    tf_listener = tf.TransformListener()
    rospy.Subscriber("/map", OccupancyGrid, map_info_callback)
    rospy.Subscriber("/amcl_pose", PoseWithCovarianceStamped, pose_callback, tf_listener)
    while not rospy.is_shutdown():
        rospy.sleep(0)

if __name__ == '__main__':
    try:
        listener()
    except rospy.ROSInterruptException:
        pass
    except Exception as e:
        print(e)