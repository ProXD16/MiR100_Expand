import rospy
from nav_msgs.msg import OccupancyGrid
import numpy as np
from PIL import Image
import os

def global_costmap_callback(map_data):
    try:
        width = map_data.info.width
        height = map_data.info.height
        resolution = map_data.info.resolution
        origin_x = map_data.info.origin.position.x
        origin_y = map_data.info.origin.position.y

        data = np.array(map_data.data).reshape((height, width))
        data = np.flipud(data)  # lật ảnh theo chiều dọc cho đúng tọa độ

        # Tạo ảnh RGBA
        rgba_img = np.zeros((height, width, 4), dtype=np.uint8)

        for y in range(height):
            for x in range(width):
                val = data[y, x]
                if val == -1:
                    rgba_img[y, x] = [0, 0, 0, 0]  # vùng không rõ → trong suốt hoàn toàn
                elif val >= 50:  # vùng bị chiếm chỗ (occupied)
                    rgba_img[y, x] = [255, 150, 255, 40]  # màu hồng nhạt, alpha = 100
                else:  # vùng free
                    rgba_img[y, x] = [255, 255, 255, 0]  # trắng, nhưng trong suốt

        img = Image.fromarray(rgba_img, mode="RGBA")

        image_path = "static/global_costmap_image.png"
        img.save(image_path)
        rospy.loginfo(f"✅ Saved pink transparent costmap to {image_path}")

    except Exception as e:
        rospy.logerr(f"[GlobalCostmap] ❌ Error processing map: {e}")

def listener():
    rospy.init_node('global_costmap_to_image', anonymous=True)
    rospy.Subscriber("/move_base_node/global_costmap/costmap", OccupancyGrid, global_costmap_callback)
    rospy.loginfo("🟢 Listening to /move_base_node/global_costmap/costmap ...")
    rospy.spin()

if __name__ == '__main__':
    listener()
