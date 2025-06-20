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

rospy.init_node("pid_dashboard", anonymous=True)
theta_current = 0  
theta_desired = 0  
time_series = []
theta_series = []
paused = False
oscillation_period = None  # Chu kỳ dao động
stability_time = None  # Thời gian ổn định
last_crossing_time = None  # Thời gian lần cuối vượt qua giá trị mong muốn
crossing_times = []  # Danh sách các thời điểm vượt qua giá trị mong muốn

Kp, Ki, Kd = 0, 0, 0
integral, prev_error = 0, 0

def odom_callback(msg):
    global theta_current
    orientation_q = msg.pose.pose.orientation
    (_, _, yaw) = tf.transformations.euler_from_quaternion(
        [orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w])
    theta_current = yaw

rospy.Subscriber("/odom", Odometry, odom_callback)

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("Điều chỉnh PID cho Robot MiR100", style={'textAlign': 'center'}),
    html.Label("Góc mong muốn (radians):"),
    dcc.Input(id='theta-desired', type='number', value=0, step=0.0000001),
    html.Label("Kp:"), dcc.Slider(id="kp-slider", min=0, max=5, step=0.1, value=Kp),
    html.Label("Ki:"), dcc.Slider(id="ki-slider", min=0, max=1, step=0.01, value=Ki),
    html.Label("Kd:"), dcc.Slider(id="kd-slider", min=0, max=2, step=0.1, value=Kd),
    dcc.Graph(id="theta-plot", config={'scrollZoom': True}),
    html.Div(id="stability-info", style={'margin-top': '20px'}),
    html.Button("Reset", id="reset-btn", n_clicks=0),
    html.Button("Pause", id="pause-btn", n_clicks=0),
    dcc.Interval(id="interval-update", interval=100, n_intervals=0)
])

def compute_pid():
    global integral, prev_error
    error = theta_desired - theta_current
    error = math.atan2(math.sin(error), math.cos(error))

    integral += error
    derivative = error - prev_error
    omega = Kp * error + Ki * integral + Kd * derivative
    omega = max(min(omega, 1.0), -1.0)

    twist_msg = rospy.Publisher("/cmd_vel", Twist, queue_size=10)
    twist = Twist()
    twist.angular.z = omega
    twist_msg.publish(twist)
    prev_error = error

def calculate_stability_metrics():
    global oscillation_period, stability_time, last_crossing_time, crossing_times
    
    # Kiểm tra nếu có đủ dữ liệu
    if len(time_series) < 2 or len(theta_series) < 2:
        return None, None
    
    current_time = rospy.get_time()
    current_theta = theta_current
    
    # Kiểm tra khi vượt qua giá trị mong muốn
    if (theta_series[-2] < theta_desired and current_theta >= theta_desired) or \
       (theta_series[-2] > theta_desired and current_theta <= theta_desired):
        
        if last_crossing_time is not None:
            crossing_times.append(current_time - last_crossing_time)
            
            # Tính chu kỳ dao động trung bình
            if len(crossing_times) >= 2:
                oscillation_period = np.mean(crossing_times)
        
        last_crossing_time = current_time
    
    # Kiểm tra điều kiện ổn định (sai số < 0.05 radian trong 2 giây)
    if abs(current_theta - theta_desired) < 0.05:
        if stability_time is None:
            stability_time = current_time
        elif current_time - stability_time >= 2.0:
            return oscillation_period, stability_time
    else:
        stability_time = None
    
    return oscillation_period, None

@app.callback(
    [Output("theta-plot", "figure"),
     Output("stability-info", "children")],
    [Input("kp-slider", "value"),
     Input("ki-slider", "value"),
     Input("kd-slider", "value"),
     Input("theta-desired", "value"),
     Input("interval-update", "n_intervals"),
     Input("reset-btn", "n_clicks"),
     Input("pause-btn", "n_clicks")],
    [State("theta-plot", "relayoutData")]
)
def update_pid(kp, ki, kd, theta, n, reset, pause, relayout_data):
    global Kp, Ki, Kd, theta_desired, theta_series, time_series, paused
    global oscillation_period, stability_time, last_crossing_time, crossing_times

    if reset > 0:
        theta_series, time_series = [], []
        oscillation_period = None
        stability_time = None
        last_crossing_time = None
        crossing_times = []
    
    if pause % 2 == 1:
        paused = True
    else:
        paused = False
    
    if not paused:
        Kp, Ki, Kd = kp, ki, kd
        theta_desired = theta * math.pi / 180
        compute_pid()

        time_series.append(rospy.get_time())
        theta_series.append(theta_current)

        if len(time_series) > 50:
            time_series = time_series[-50:]
            theta_series = theta_series[-50:]

    # Tính toán các thông số ổn định
    current_period, stable_time = calculate_stability_metrics()
    
    # Tạo thông tin hiển thị
    stability_info = []
    if current_period is not None:
        stability_info.append(html.P(f"Chu kỳ dao động: {current_period:.2f} giây"))
    if stable_time is not None:
        stability_info.append(html.P(f"Hệ thống ổn định sau: {stable_time:.2f} giây"))
    
    if not stability_info:
        stability_info = html.P("Hệ thống chưa ổn định")

    # Tạo figure
    figure = {
        "data": [
            go.Scatter(x=time_series, y=theta_series, mode="lines", name="Góc robot (radians)"),
            go.Scatter(x=time_series, y=[theta_desired]*len(time_series), mode="lines", name="Góc mong muốn", line=dict(dash="dash"))
        ],
        "layout": go.Layout(
            title="Phản hồi góc của Robot",
            xaxis={"title": "Thời gian"},
            yaxis={"title": "Góc (radians)", "range": [-math.pi, math.pi]}
        )
    }

    if relayout_data and 'xaxis.range[0]' in relayout_data:
        figure['layout']['xaxis']['range'] = [relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']]
    if relayout_data and 'yaxis.range[0]' in relayout_data:
        figure['layout']['yaxis']['range'] = [relayout_data['yaxis.range[0]'], relayout_data['yaxis.range[1]']]

    return figure, stability_info

def run_dash():
    app.run_server(debug=False, port=8050, host="0.0.0.0")

threading.Thread(target=run_dash).start()
rospy.spin()