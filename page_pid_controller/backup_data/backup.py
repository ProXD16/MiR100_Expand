import rospy
import dash
from dash import dcc, html
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
import tf
import math
import threading
import numpy as np

rospy.init_node("position_control_dashboard", anonymous=True)

# Biến toàn cục
robot_x = 0.0
robot_y = 0.0
robot_yaw = 0.0
target_x = None
target_y = None
has_target = False
paused = True
control_state = "IDLE"  # IDLE/ROTATE/MOVE/STOP

# Tham số PID
Kp_angle = 2.5
Ki_angle = 0.03
Kd_angle = 0.4
Kp_distance = 1.5

# Biến PID
integral_angle = 0.0
prev_angle_error = 0.0

# Lịch sử
time_series = []
distance_series = []
angle_series = []

cmd_vel_pub = rospy.Publisher("/cmd_vel", Twist, queue_size=10)

def get_robot_position():
    tf_listener = tf.TransformListener()
    try:
        tf_listener.waitForTransform('/map', '/base_link', rospy.Time(0), rospy.Duration(1))
        (trans, rot) = tf_listener.lookupTransform('/map', '/base_link', rospy.Time(0))
        return trans[0], trans[1], tf.transformations.euler_from_quaternion(rot)[2]
    except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
        rospy.logwarn("TF error when getting robot position.")
        return None, None, None

def calculate_control():
    global robot_x, robot_y, robot_yaw, integral_angle, prev_angle_error, control_state
    
    # Lấy vị trí hiện tại
    robot_x, robot_y, robot_yaw = get_robot_position()
    if robot_x is None or not has_target or paused:
        publish_zero_velocity()
        return 0, 0
    
    # Tính toán sai số
    dx = target_x - robot_x
    dy = target_y - robot_y
    distance = math.sqrt(dx**2 + dy**2)
    target_angle = math.atan2(dy, dx)
    angle_error = target_angle - robot_yaw
    angle_error = math.atan2(math.sin(angle_error), math.cos(angle_error))
    
    twist_msg = Twist()
    
    if control_state == "ROTATE":
        if abs(angle_error) > 0.0001:  # Ngưỡng sai số góc (rad)
            integral_angle += angle_error
            derivative = angle_error - prev_angle_error
            prev_angle_error = angle_error
            
            twist_msg.angular.z = Kp_angle * angle_error + Ki_angle * integral_angle + Kd_angle * derivative
            twist_msg.angular.z = max(min(twist_msg.angular.z, 1.0), -1.0)
        else:
            control_state = "MOVE"
    
    elif control_state == "MOVE":
        if distance > 0.05:  # Ngưỡng khoảng cách (m)
            twist_msg.linear.x = min(Kp_distance * distance, 0.5)
            
            # Kiểm tra lại góc khi di chuyển
            if abs(angle_error) > 0.2:  # Nếu lệch góc nhiều thì quay lại
                control_state = "ROTATE"
        else:
            # Đã đến đích - THÊM ĐIỀU KIỆN DỪNG CHẶT CHẼ HƠN
            if distance < 0.01 and abs(angle_error) < 0.0001:
                twist_msg.linear.x = 0.0
                twist_msg.angular.z = 0.0
                control_state = "STOP"
                publish_zero_velocity()
                return distance, angle_error
    
    cmd_vel_pub.publish(twist_msg)
    return distance, angle_error

def publish_zero_velocity():
    twist_msg = Twist()
    twist_msg.linear.x = 0.0
    twist_msg.angular.z = 0.0
    cmd_vel_pub.publish(twist_msg)

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("Điều khiển vị trí Robot", style={'textAlign': 'center'}),
    
    html.Div([
        html.Label("Target X (m):"),
        dcc.Input(id='target-x', type='number', value=0.0, step=0.0000001),
        
        html.Label("Target Y (m):"),
        dcc.Input(id='target-y', type='number', value=0.0, step=0.0000001),
    ], style={'margin-bottom': '20px'}),
    
    html.Div([
        html.Label("Kp (angle):"), 
        dcc.Slider(id="kp-angle-slider", min=0, max=5, step=0.1, value=Kp_angle),
        
        html.Label("Ki (angle):"), 
        dcc.Slider(id="ki-angle-slider", min=0, max=0.1, step=0.01, value=Ki_angle),
        
        html.Label("Kd (angle):"), 
        dcc.Slider(id="kd-angle-slider", min=0, max=1, step=0.05, value=Kd_angle),
        
        html.Label("Kp (distance):"), 
        dcc.Slider(id="kp-distance-slider", min=0, max=2, step=0.1, value=Kp_distance),
    ], style={'margin-bottom': '20px'}),
    
    html.Div([
        html.Button("Start", id="start-btn", n_clicks=0, style={'margin-right': '10px'}),
        html.Button("Pause", id="pause-btn", n_clicks=0, disabled=True),
        html.Button("Reset", id="reset-btn", n_clicks=0, style={'margin-left': '10px'}),
    ], style={'margin-bottom': '20px'}),
    
    dcc.Graph(id="distance-plot", config={'scrollZoom': True}),
    dcc.Graph(id="angle-plot", config={'scrollZoom': True}),
    
    html.Div(id="control-state", style={
        'margin-top': '20px',
        'padding': '15px',
        'border': '1px solid #ddd',
        'border-radius': '5px',
        'background-color': '#f9f9f9'
    }),
    
    dcc.Interval(id="interval-update", interval=100, n_intervals=0)
])

@app.callback(
    [Output("distance-plot", "figure"),
     Output("angle-plot", "figure"),
     Output("control-state", "children"),
     Output("pause-btn", "disabled"),
     Output("start-btn", "disabled")],
    [Input("target-x", "value"),
     Input("target-y", "value"),
     Input("start-btn", "n_clicks"),
     Input("pause-btn", "n_clicks"),
     Input("reset-btn", "n_clicks"),
     Input("kp-angle-slider", "value"),
     Input("ki-angle-slider", "value"),
     Input("kd-angle-slider", "value"),
     Input("kp-distance-slider", "value"),
     Input("interval-update", "n_intervals")],
    [State("distance-plot", "relayoutData"),
     State("angle-plot", "relayoutData")]
)
def update_control(x, y, start_clicks, pause_clicks, reset_clicks, 
                  kp_a, ki_a, kd_a, kp_d, n, dist_layout, angle_layout):
    global target_x, target_y, has_target, paused, control_state
    global Kp_angle, Ki_angle, Kd_angle, Kp_distance
    global time_series, distance_series, angle_series
    
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = None
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Xử lý nút Start
    if button_id == "start-btn" and x is not None and y is not None:
        target_x = x
        target_y = y
        has_target = True
        paused = False
        control_state = "ROTATE"
        integral_angle = 0.0
        prev_angle_error = 0.0
    
    # Xử lý nút Pause
    elif button_id == "pause-btn":
        paused = not paused
        if paused:
            publish_zero_velocity()
    
    # Xử lý nút Reset
    elif button_id == "reset-btn":
        target_x = None
        target_y = None
        has_target = False
        paused = True
        control_state = "IDLE"
        time_series, distance_series, angle_series = [], [], []
        publish_zero_velocity()
    
    # Cập nhật tham số PID
    Kp_angle, Ki_angle, Kd_angle = kp_a, ki_a, kd_a
    Kp_distance = kp_d
    
    # Tính toán điều khiển và cập nhật dữ liệu
    if has_target and not paused:
        distance, angle_error = calculate_control()
        
        current_time = rospy.get_time()
        time_series.append(current_time)
        distance_series.append(distance)
        angle_series.append(angle_error)
        
        if len(time_series) > 100:
            time_series = time_series[-100:]
            distance_series = distance_series[-100:]
            angle_series = angle_series[-100:]
    else:
        distance, angle_error = 0, 0
    
    # Tạo đồ thị khoảng cách
    distance_fig = {
        "data": [go.Scatter(x=time_series, y=distance_series, mode="lines", name="Khoảng cách (m)")],
        "layout": go.Layout(
            title="Khoảng cách đến mục tiêu",
            xaxis={"title": "Thời gian"},
            yaxis={"title": "Khoảng cách (m)"}
        )
    }
    
    # Tạo đồ thị góc
    angle_fig = {
        "data": [go.Scatter(x=time_series, y=angle_series, mode="lines", name="Sai số góc (rad)")],
        "layout": go.Layout(
            title="Sai số góc",
            xaxis={"title": "Thời gian"},
            yaxis={"title": "Góc (rad)", "range": [-math.pi, math.pi]}
        )
    }
    
    # Hiển thị trạng thái
    state_info = []
    if not has_target:
        state_info.append(html.P("TRẠNG THÁI: CHỜ NHẬP MỤC TIÊU", style={'color': 'gray'}))
    else:
        status_colors = {
            "IDLE": "gray",
            "ROTATE": "orange",
            "MOVE": "blue",
            "STOP": "green"
        }
        state_info.append(html.P(f"TRẠNG THÁI: {control_state}", 
                               style={'color': status_colors.get(control_state, 'black')}))
        
        state_info.append(html.P(f"Vị trí hiện tại: X={robot_x:.6f}m, Y={robot_y:.6f}m"))
        state_info.append(html.P(f"Hướng hiện tại: {math.degrees(robot_yaw):.6f}°"))
        
        if distance_series:
            state_info.append(html.P(f"Khoảng cách đến mục tiêu: {distance_series[-1]:.6f}m"))
        if angle_series:
            state_info.append(html.P(f"Sai số góc: {math.degrees(angle_series[-1]):.6f}°"))
    
    # Áp dụng lại zoom
    if dist_layout and 'xaxis.range[0]' in dist_layout:
        distance_fig['layout']['xaxis']['range'] = [dist_layout['xaxis.range[0]'], dist_layout['xaxis.range[1]']]
    if angle_layout and 'xaxis.range[0]' in angle_layout:
        angle_fig['layout']['xaxis']['range'] = [angle_layout['xaxis.range[0]'], angle_layout['xaxis.range[1]']]
    
    # Điều khiển trạng thái nút
    pause_disabled = not has_target
    start_disabled = has_target and not paused
    
    return distance_fig, angle_fig, state_info, pause_disabled, start_disabled

def run_dash():
    app.run_server(debug=False, port=8050, host="0.0.0.0")

if __name__ == '__main__':
    threading.Thread(target=run_dash).start()
    rospy.spin()


######################################################################################
import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
import numpy as np
import tkinter as tk
import threading
import tf.transformations
import matplotlib
matplotlib.use("TkAgg")  # Sử dụng backend TkAgg (tương thích tốt với Tkinter)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class MPCController:
    def __init__(self, dt, v_max, v_min, omega_max, omega_min):
        """
        dt:  Thời gian lấy mẫu
        v_max, v_min, omega_max, omega_min: Giới hạn điều khiển
        """
        self.dt = dt
        self.v_max = v_max
        self.v_min = v_min
        self.omega_max = omega_max
        self.omega_min = omega_min
        self.current_pose = None
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.trajectory_x = []
        self.trajectory_y = []

    def pose_callback(self, msg):
        """Callback function to update the current pose from /amcl_pose."""
        quat = msg.pose.pose.orientation
        if quat.w == 0.0 and quat.x == 0.0 and quat.y == 0.0 and quat.z == 0.0:
            rospy.logwarn("Invalid quaternion received, skipping pose update.")
            return

        try:
            euler = tf.transformations.euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
            roll, pitch, yaw = euler[0], euler[1], euler[2]
        except Exception as e:
            rospy.logerr(f"Error converting quaternion to Euler: {e}")
            return

        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        self.theta = yaw
        self.current_pose = np.array([self.x, self.y, self.theta])
        self.trajectory_x.append(self.x)
        self.trajectory_y.append(self.y)

    def mpc_control(self, x, y, theta, x_goal, y_goal):
        """
        Điều khiển tỷ lệ đơn giản để điều chỉnh vận tốc, với quay tại chỗ trước khi di chuyển.
        """
        # Tính toán sai số vị trí và hướng
        x_error = x_goal - x
        y_error = y_goal - y
        distance_to_goal = np.sqrt(x_error**2 + y_error**2)
        angle_to_goal = np.arctan2(y_error, x_error)
        heading_error = angle_to_goal - theta

        # Điều chỉnh sai số hướng để nằm trong khoảng -pi đến pi
        heading_error = np.arctan2(np.sin(heading_error), np.cos(heading_error))

        # Ngưỡng sai số hướng (điều chỉnh giá trị này)
        heading_threshold = 0.1  # Radian

        # Các hệ số tỷ lệ (điều chỉnh các giá trị này để có hiệu suất tốt nhất)
        linear_speed_kp = 0.3
        angular_speed_kp = 0.5

        # Kiểm tra sai số hướng
        if abs(heading_error) > heading_threshold:
            # Quay tại chỗ
            v = 0.0
            omega = angular_speed_kp * heading_error
        else:
            # Di chuyển đến mục tiêu
            v = linear_speed_kp * distance_to_goal
            omega = angular_speed_kp * heading_error

        # Giới hạn vận tốc
        v = np.clip(v, self.v_min, self.v_max)
        omega = np.clip(omega, self.omega_min, self.omega_max)

        return v, omega

class GUI:
    def __init__(self, master, mpc_controller):
        self.master = master
        master.title("MiR100 MPC Control")

        self.mpc_controller = mpc_controller

        self.label_x = tk.Label(master, text="X Goal:")
        self.label_y = tk.Label(master, text="Y Goal:")
        self.entry_x = tk.Entry(master)
        self.entry_y = tk.Entry(master)

        self.label_x.grid(row=0, column=0)
        self.entry_x.grid(row=0, column=1)
        self.label_y.grid(row=1, column=0)
        self.entry_y.grid(row=1, column=1)

        self.start_button = tk.Button(master, text="Start", command=self.start_control_loop)
        self.start_button.grid(row=2, column=0)
        self.stop_button = tk.Button(master, text="Stop", command=self.stop_control_loop, state=tk.DISABLED)
        self.stop_button.grid(row=2, column=1)

        self.result_label = tk.Label(master, text="")
        self.result_label.grid(row=3, column=0, columnspan=2)

        # Publisher cho cmd_vel
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

        self.control_loop_running = False
        self.goal_x = 0.0
        self.goal_y = 0.0
        self.distance_threshold = 0.1

        # Khởi tạo đồ thị matplotlib và nhúng vào Tkinter
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim([-5, 5])
        self.ax.set_ylim([-5, 5])
        self.ax.set_xlabel("X (m)")
        self.ax.set_ylabel("Y (m)")
        self.ax.set_title("Robot Trajectory")
        self.line, = self.ax.plot([], [], label="Robot Path")
        self.goal_marker, = self.ax.plot([], [], 'ro', label="Goal")
        self.ax.legend()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)  # A tk.DrawingArea.
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=4, column=0, columnspan=2) # đặt canvas vào grid

    def start_control_loop(self):
        """Bắt đầu vòng lặp điều khiển."""
        try:
            self.goal_x = float(self.entry_x.get())
            self.goal_y = float(self.entry_y.get())
        except ValueError:
            self.result_label.config(text="Lỗi: Vui lòng nhập giá trị số hợp lệ cho tọa độ mục tiêu")
            return

        self.entry_x.config(state=tk.DISABLED)
        self.entry_y.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        self.mpc_controller.trajectory_x = []
        self.mpc_controller.trajectory_y = []
        self.control_loop_running = True

        self.goal_marker.set_data([self.goal_x], [self.goal_y])

        # Bắt đầu vòng lặp điều khiển và cập nhật đồ thị bằng Tkinter's `after` method
        self.master.after(0, self.update_plot)

    def stop_control_loop(self):
        """Dừng vòng lặp điều khiển."""
        self.control_loop_running = False
        self.entry_x.config(state=tk.NORMAL)
        self.entry_y.config(state=tk.NORMAL)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def update_plot(self):
        """Cập nhật đồ thị (chạy trong main thread)."""
        if not self.control_loop_running:
            return

        if self.mpc_controller.current_pose is None:
            self.result_label.config(text="Waiting for initial pose from /amcl_pose...")
            self.master.after(50, self.update_plot)  # Thử lại sau 50ms
            return

        x = self.mpc_controller.x
        y = self.mpc_controller.y
        theta = self.mpc_controller.theta

        v, omega = self.mpc_controller.mpc_control(x, y, theta, self.goal_x, self.goal_y)
        self.send_command(v, omega)

        distance_to_goal = np.sqrt((self.goal_x - x)**2 + (self.goal_y - y)**2)

        # Update plot data
        self.line.set_data(self.mpc_controller.trajectory_x, self.mpc_controller.trajectory_y)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle() # Vẽ lại canvas

        if distance_to_goal < self.distance_threshold:
            self.result_label.config(text="Đã đến mục tiêu!")
            self.send_command(0.0, 0.0)
            self.stop_control_loop()
            return

        # Lên lịch cho lần cập nhật tiếp theo
        self.master.after(50, self.update_plot)  # Cập nhật mỗi 50ms (20Hz)


    def send_command(self, v, omega):
        """Gửi vận tốc (v, omega) tới robot MiR100 qua topic /cmd_vel."""
        twist_msg = Twist()
        twist_msg.linear.x = v
        twist_msg.angular.z = omega
        self.cmd_vel_pub.publish(twist_msg)
        print(f"Published to /cmd_vel: linear.x = {v:.2f}, angular.z = {omega:.2f}")


def ros_spin():
    """Function to run ROS spin in a separate thread."""
    rospy.spin()


if __name__ == '__main__':
    # ROS Initialization
    rospy.init_node('mpc_controller_node')

    # MPC Parameters
    dt = 0.1
    v_max = 0.5
    v_min = -0.5
    omega_max = 0.4
    omega_min = -0.4

    # Initialize MPC controller
    controller = MPCController(dt, v_max, v_min, omega_max, omega_min)

    # Subscribe to /amcl_pose to get robot's pose
    rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, controller.pose_callback)

    root = tk.Tk()
    gui = GUI(root, controller)

    threading.Thread(target=ros_spin, daemon=True).start()
    root.mainloop()