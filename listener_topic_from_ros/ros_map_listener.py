import rospy
from nav_msgs.msg import OccupancyGrid
import numpy as np
from PIL import Image
import io
import yaml
import json

def map_callback(map_data):
    try:
        width = map_data.info.width
        height = map_data.info.height
        resolution = map_data.info.resolution
        resolution_x = resolution
        resolution_y = resolution
        origin_x = map_data.info.origin.position.x
        origin_y = map_data.info.origin.position.y
        map_array = np.array(map_data.data).reshape((height, width))
        map_array = np.flipud(map_array)
        map_array = np.rot90(map_array, k=4)

        # Gán màu dựa trên giá trị
        for i in range(height):
            for j in range(width):
                if map_array[i, j] == 96:
                    map_array[i, j] = 20  # Tường (đen)
                elif map_array[i, j] == 0:
                    map_array[i, j] = 0  # Free (trắng)
                else:
                    map_array[i, j] = 100  # Không xác định (xám)

        map_array = (map_array * 255 / 100).astype(np.uint8)
        map_array = 255 - map_array
        img = Image.fromarray(map_array, mode='L')
        buffer = io.BytesIO()
        img.save(buffer, format="png")
        encoded_image = buffer.getvalue()

        image_path = "static/map_image.png"
        yaml_path = "static/map_image.yaml"
        info_path = "static/map_image.info"
        json_path = "static/map_image.json"
        with open(image_path, "wb") as fh:
            fh.write(encoded_image)
        rospy.loginfo(f"Saved rotated map image to {image_path}")
        map_yaml = {
            'image': 'map_image.png',
            'resolution': resolution,
            'origin': [origin_x, origin_y, 0.0],
            'negate': 0,
            'occupied_thresh': 0.65,
            'free_thresh': 0.196
        }
        with open(yaml_path, 'w') as yaml_file:
            yaml.dump(map_yaml, yaml_file)
        rospy.loginfo(f"Saved map YAML data to {yaml_path}")
        map_info = {
            'width': width,
            'height': height,
            'resolution': resolution,
            'resolution_x': resolution_x,
            'resolution_y': resolution_y,
            'origin_x': origin_x,
            'origin_y': origin_y
        }
        with open(info_path, 'w') as info_file:
            yaml.dump(map_info, info_file)
        rospy.loginfo(f"Saved map info data to {info_path}")
        map_json = {
            'width': width,
            'height': height,
            'resolution': resolution,
            'resolution_x': resolution_x,
            'resolution_y': resolution_y,
            'origin_x': origin_x,
            'origin_y': origin_y
        }

        with open(json_path, 'w') as json_file:
            json.dump(map_json, json_file)
        rospy.loginfo(f"Saved map info data to {json_path}")
    except Exception as e:
        rospy.logerr(f"Error processing map data: {e}")


def listener():
    rospy.init_node('map_to_image', anonymous=True)
    rospy.Subscriber("/map", OccupancyGrid, map_callback)
    rospy.spin()


if __name__ == '__main__':
    listener()