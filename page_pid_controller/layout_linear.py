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
Kp_distance = 1.0

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
        # Giai đoạn quay về hướng mục tiêu
        if abs(angle_error) > 0.1:  # Ngưỡng sai số góc (rad)
            integral_angle += angle_error
            derivative = angle_error - prev_angle_error
            prev_angle_error = angle_error
            
            twist_msg.angular.z = Kp_angle * angle_error + Ki_angle * integral_angle + Kd_angle * derivative
            twist_msg.angular.z = max(min(twist_msg.angular.z, 1.0), -1.0)
        else:
            control_state = "MOVE"  # Chuyển sang giai đoạn di chuyển
    
    elif control_state == "MOVE":
        # Giai đoạn di chuyển thẳng 
        if distance > 0.05:  # Ngưỡng khoảng cách (m)
            twist_msg.linear.x = min(Kp_distance * distance, 0.5)
        else:
            # Đã đến đích
            twist_msg.linear.x = 0.0
            control_state = "STOP"
    
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
        dcc.Input(id='target-x', type='number', value=0.0, step=0.000001),
        
        html.Label("Target Y (m):"),
        dcc.Input(id='target-y', type='number', value=0.0, step=0.000001),
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