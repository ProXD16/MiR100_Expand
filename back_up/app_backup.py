import dash, rospy
from dash import dcc, html
import dash_bootstrap_components as dbc
from flask import request, jsonify
import base64, os, json

# Component nội bộ
from components import LoginPage, ChangePasswordPage, Sidebar, StatusBar, MapSection
from geometry_msgs.msg import Twist
from page_draw_mode import *
from function_teleop_control import TeleopControl
from make_marker_with_json import *
from page_mission.missions.callbacks import register_callbacks
from page_map.map_api import MapAPI
from page_home.callbacks import *
from page_path_guides import *

# ROS setup
stop_requested = False 
ip = '192.168.0.173'
host = 'http://' + ip + '/api/v2.0.0/'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='
}

# Khởi tạo Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css",
    ],
    suppress_callback_exceptions=True,
    external_scripts=[
        "https://cdnjs.cloudflare.com/ajax/libs/nipplejs/0.10.0/nipplejs.min.js",
        "assets/script.js"
    ]
)
app.title = "MiR100 Smart Equipment and Robot Lab"
server = app.server  # ✅ Lấy Flask server để dùng cho route riêng

# ROS init
if not rospy.core.is_initialized():
    try:
        rospy.init_node('dash_app', anonymous=True)
        print("ROS node 'dash_app' initialized successfully.")
    except rospy.exceptions.ROSException as e:
        print(f"Error initializing ROS node: {e}")

# ROS publisher
if rospy.core.is_initialized():
    pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
else:
    pub = None
    print("ROS not properly initialized, publisher not created.")

# Teleop
if pub:
    joystick_control = TeleopControl(pub, 0.5, 0.3)
    joystick_control.stop()
else:
    class DummyTeleopControl:
        def __init__(self): pass
        def create_joystick_popup(self):
            return html.Div("ROS not available.")
    joystick_control = DummyTeleopControl()

# Component layout
login_page = LoginPage()
map_api = MapAPI()
map_api.register_callbacks(app)
register_callbacks(app)

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id="app-container", children=[login_page.layout]),
    html.Div(id="joystick-output", style={"margin": "20px", "fontSize": "0px"}),
])

# ✅ API lưu ảnh canvas
@server.route('/save_path_image', methods=['POST'])
def save_path_image():
    data = request.get_json()
    image_data = data['image'].split(',')[1]
    os.makedirs('static', exist_ok=True)
    with open('static/path_img.png', 'wb') as f:
        f.write(base64.b64decode(image_data))
    return jsonify({'status': 'success'})

# ✅ API lưu JSON đường vẽ
@server.route('/save_path_json', methods=['POST'])
def save_path_json():
    data = request.get_json()
    os.makedirs('database_json', exist_ok=True)
    with open('database_json/path_drawn.json', 'w') as f:
        json.dump(data['paths'], f, indent=2)
    return jsonify({'status': 'success'})

# Khởi chạy
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8000)
