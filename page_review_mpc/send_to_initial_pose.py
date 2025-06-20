#!/usr/bin/env python

import rospy
import actionlib
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from nav_msgs.msg import OccupancyGrid, Path
from geometry_msgs.msg import PoseStamped
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import tf
import threading

class MapDisplay:
    def __init__(self, master):
        self.master = master
        self.map_data = None
        self.resolution = 0.0
        self.origin = (0.0, 0.0)
        self.robot_position = (0.0, 0.0)
        self.goal_position = None
        self.is_moving = False
        self.drag_start = None  # Biến lưu trữ vị trí bắt đầu kéo chuột

        # Khai báo subscriber cho bản đồ
        self.map_subscriber = rospy.Subscriber("/map", OccupancyGrid, self.map_callback)

        # Khai báo subscriber cho điểm đích từ RViz
        self.goal_subscriber = rospy.Subscriber("/move_base_simple/goal", PoseStamped, self.rviz_goal_callback)

        # Khai báo subscriber cho đường đi từ robot tới đích
        self.path_subscriber = rospy.Subscriber("/move_base_node/SBPLLatticePlanner/plan", Path, self.path_callback)

        # Tạo TF listener để lấy vị trí của robot
        self.tf_listener = tf.TransformListener()

        # Tạo không gian hiển thị bản đồ
        self.fig = Figure(figsize=(5, 5))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.get_tk_widget().grid(row=5, column=0, columnspan=2)

        # Kết nối các sự kiện nhấp chuột và kéo chuột
        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.canvas.mpl_connect("motion_notify_event", self.on_drag)
        self.canvas.mpl_connect("button_release_event", self.on_release)

        self.create_widgets()
        self.update_position_continuously()

    def create_widgets(self):
        tk.Label(self.master, text="X:").grid(row=0, column=0)
        self.entry_x = tk.Entry(self.master)
        self.entry_x.grid(row=0, column=1)

        tk.Label(self.master, text="Y:").grid(row=1, column=0)
        self.entry_y = tk.Entry(self.master)
        self.entry_y.grid(row=1, column=1)

        tk.Label(self.master, text="Z:").grid(row=2, column=0)
        self.entry_z = tk.Entry(self.master)
        self.entry_z.grid(row=2, column=1)

        tk.Label(self.master, text="W:").grid(row=3, column=0)
        self.entry_w = tk.Entry(self.master)
        self.entry_w.grid(row=3, column=1)

        send_button = tk.Button(self.master, text="Send Goal", command=self.send_goal_thread)
        send_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.position_label = tk.Label(self.master, text="Robot Position: (0.00, 0.00)")
        self.position_label.grid(row=6, column=0, columnspan=2)

    def on_click(self, event):
        # Lưu vị trí bắt đầu kéo chuột
        if event.inaxes == self.ax:
            self.drag_start = (event.xdata, event.ydata)

    def on_drag(self, event):
        # Cập nhật vị trí kéo chuột
        if self.drag_start is not None and event.inaxes == self.ax:
            x_start, y_start = self.drag_start
            x_end, y_end = event.xdata, event.ydata
            
            # Vẽ lại bản đồ và đường kéo chuột
            self.ax.clear()
            self.display_map()
            self.ax.plot([x_start, x_end], [y_start, y_end], 'r--', label='Dragging')
            self.canvas.draw()

    def on_release(self, event):
        # Khi thả chuột, gửi vị trí đến robot
        if self.drag_start is not None and event.inaxes == self.ax:
            x_start, y_start = self.drag_start
            x_end, y_end = event.xdata, event.ydata
            
            # Cập nhật tọa độ vào các ô nhập liệu
            self.entry_x.delete(0, tk.END)
            self.entry_x.insert(0, str(x_end))
            self.entry_y.delete(0, tk.END)
            self.entry_y.insert(0, str(y_end))

            # Tính toán z và w từ góc giữa hai điểm
            orientation = np.arctan2(y_end - y_start, x_end - x_start)
            z = np.sin(orientation / 2)
            w = np.cos(orientation / 2)

            # Cập nhật các ô nhập liệu cho z và w
            self.entry_z.delete(0, tk.END)
            self.entry_z.insert(0, str(z))
            self.entry_w.delete(0, tk.END)
            self.entry_w.insert(0, str(w))

            # Gọi hàm để gửi điểm đến robot
            self.send_goal_thread()

        # Reset vị trí kéo
        self.drag_start = None

    def send_goal_thread(self):
        threading.Thread(target=self.send_goal).start()

    def send_goal(self):
        x = float(self.entry_x.get())
        y = float(self.entry_y.get())
        z = float(self.entry_z.get())
        w = float(self.entry_w.get())
        self.goal_position = (x, y)
        self.movebase_client(x, y, z, w)

    def movebase_client(self, x, y, z, w):
        client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        client.wait_for_server()

        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()

        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        goal.target_pose.pose.orientation.z = z
        goal.target_pose.pose.orientation.w = w

        self.is_moving = True
        client.send_goal(goal)

        client.wait_for_result()
        self.is_moving = False
        self.goal_position = None

    def rviz_goal_callback(self, goal_msg):
        x = goal_msg.pose.position.x
        y = goal_msg.pose.position.y
        z = goal_msg.pose.orientation.z
        w = goal_msg.pose.orientation.w
        self.goal_position = (x, y)

        self.entry_x.delete(0, tk.END)
        self.entry_x.insert(0, str(x))
        self.entry_y.delete(0, tk.END)
        self.entry_y.insert(0, str(y))
        self.entry_z.delete(0, tk.END)
        self.entry_z.insert(0, str(z))
        self.entry_w.delete(0, tk.END)
        self.entry_w.insert(0, str(w))

        self.movebase_client(x, y, z, w)

    def map_callback(self, data):
        self.map_data = data
        self.resolution = data.info.resolution
        self.origin = (data.info.origin.position.x, data.info.origin.position.y)
        self.display_map()

    def path_callback(self, path_msg):
        self.path_points = [(pose.pose.position.x, pose.pose.position.y) for pose in path_msg.poses]
        self.display_map()

    def display_map(self):
        if self.map_data is not None:
            data_array = np.array(self.map_data.data).reshape((self.map_data.info.height, self.map_data.info.width))
            data_array = np.where(data_array == -1, np.nan, data_array)
            self.ax.clear()
            self.ax.imshow(data_array, cmap='gray', origin='lower', extent=[
                self.origin[0], self.origin[0] + self.map_data.info.width * self.resolution,
                self.origin[1], self.origin[1] + self.map_data.info.height * self.resolution
            ])
            self.ax.set_title('Map')

            # Hiển thị vị trí robot
            self.ax.plot(self.robot_position[0], self.robot_position[1], 'ro', label='Robot Position')

            # Hiển thị vị trí đích (nếu có)
            if self.goal_position:
                self.ax.plot(self.goal_position[0], self.goal_position[1], 'go', label='Goal Position')

            # Hiển thị đường đi từ robot tới đích
            if hasattr(self, 'path_points') and self.path_points:
                path_x, path_y = zip(*self.path_points)
                self.ax.plot(path_x, path_y, 'b--', label='Path')

            self.ax.legend()
            self.canvas.draw()

    def update_position_continuously(self):
        self.update_position()
        self.master.after(100, self.update_position_continuously)

    def update_position(self):
        try:
            self.tf_listener.waitForTransform('/map', '/base_link', rospy.Time(0), rospy.Duration(2.0))
            (trans, rot) = self.tf_listener.lookupTransform('/map', '/base_link', rospy.Time(0))
            self.robot_position = (trans[0], trans[1])
            self.position_label.config(text=f"Robot Position: ({trans[0]:.2f}, {trans[1]:.2f})")
            self.display_map()
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            pass

if __name__ == '__main__':
    rospy.init_node('map_display_node', anonymous=True)
    root = tk.Tk()
    app = MapDisplay(root)
    root.mainloop()