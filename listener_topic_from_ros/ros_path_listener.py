import rospy
from nav_msgs.msg import Path
from PIL import Image, ImageDraw
from nav_msgs.msg import OccupancyGrid

OUTPUT_IMAGE_PATH = "static/path_image.png"
image_path = "static/map_image.png"
img = Image.open(image_path)
IMAGE_WIDTH, IMAGE_HEIGHT = img.size
POINT_SIZE = 0.01  
PATH_COLOR = (0, 255, 255) 
MAP_ORIGIN_X = None
MAP_ORIGIN_Y = None
MAP_RESOLUTION = None
img = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
img.save(OUTPUT_IMAGE_PATH)

def world_to_image(x, y):
    global IMAGE_WIDTH, IMAGE_HEIGHT, MAP_ORIGIN_X, MAP_ORIGIN_Y, MAP_RESOLUTION
    if MAP_ORIGIN_X is None or MAP_ORIGIN_Y is None or MAP_RESOLUTION is None:
      rospy.logwarn("Map origin or resolution is not initialized. Cannot transform coordinates.")
      return None, None
    px = int((x - MAP_ORIGIN_X) / MAP_RESOLUTION)
    py = int((y - MAP_ORIGIN_Y) / MAP_RESOLUTION)
    py = IMAGE_HEIGHT - py
    return px, py

def path_callback(msg):
    global IMAGE_WIDTH, IMAGE_HEIGHT
    try:
        img = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        path_points = [(pose.pose.position.x, pose.pose.position.y) for pose in msg.poses]
        image_points = []
        for world_x, world_y in path_points:
            px, py = world_to_image(world_x, world_y)
            if px is not None and py is not None:
              image_points.append((px, py))
        for px, py in image_points:
            draw.ellipse((px - POINT_SIZE, py - POINT_SIZE, px + POINT_SIZE, py + POINT_SIZE), fill=PATH_COLOR)  
        img.save(OUTPUT_IMAGE_PATH)
        rospy.loginfo(f"Path image saved to {OUTPUT_IMAGE_PATH}")
    except Exception as e:
        rospy.logerr(f"Error processing path data: {e}")

def map_info_callback(map_data):
    global MAP_ORIGIN_X, MAP_ORIGIN_Y, MAP_RESOLUTION
    MAP_ORIGIN_X = map_data.info.origin.position.x
    MAP_ORIGIN_Y = map_data.info.origin.position.y
    MAP_RESOLUTION = map_data.info.resolution
    rospy.loginfo("Received map info")

def listener():
    rospy.init_node('path_to_image', anonymous=True)
    rospy.Subscriber("/map", OccupancyGrid, map_info_callback)
    rospy.Subscriber("/move_base_node/SBPLLatticePlanner/plan", Path, path_callback)
    rospy.spin()

if __name__ == '__main__':
    try:
        listener()
    except rospy.ROSInterruptException:
        pass