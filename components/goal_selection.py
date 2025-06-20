import rospy
from geometry_msgs.msg import PoseStamped

class GoalSelector:
    def __init__(self, goal_topic="/move_base_simple/goal"):
        self.goal_topic = goal_topic
        try:
            self.goal_pub = rospy.Publisher(self.goal_topic, PoseStamped, queue_size=10)
        except rospy.exceptions.ROSException as e:
            print(f"Error connecting to ROS: {e}")
            self.goal_pub = None
        self.map_info = None

    def set_map_info(self, map_info):
        self.map_info = map_info

    def publish_goal(self, x, y, z, w):
        if self.goal_pub and self.map_info:
            try:
                pose = PoseStamped()
                pose.header.stamp = rospy.Time.now()
                pose.header.frame_id = "map"

                pose.pose.position.x = float(x)
                pose.pose.position.y = float(y)
                pose.pose.position.z = float(z)

                pose.pose.orientation.w = float(w)

                self.goal_pub.publish(pose)
                return "Goal published succezssfully!"
            except Exception as e:
                return f"Error publishing goal: {e}"
        else:
            return "Goal publisher not initialized or map info not available."

    def pixel_to_map_coordinates(self, pixel_x, pixel_y):
        if self.map_info is None:
            print("Map information not available for coordinate transform.")
            return None, None

        map_x = pixel_x * self.map_info.resolution + self.map_info.origin.position.x
        map_y = (self.map_info.height - pixel_y) * self.map_info.resolution + self.map_info.origin.position.y

        return map_x, map_y