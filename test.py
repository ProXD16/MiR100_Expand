import dash, rospy
from dash import dcc, html
import dash_bootstrap_components as dbc
from components import LoginPage, ChangePasswordPage, Sidebar, StatusBar, MapSection
from geometry_msgs.msg import Twist
from page_draw_mode import *
from function_teleop_control import TeleopControl
from make_marker_with_json import *
from page_mission.missions.callbacks import register_callbacks
from page_map.map_api import MapAPI
from page_home.callbacks import *
from get_ip_address import load_ip_from_json

stop_requested = False 
ip = load_ip_from_json("database_json/ip_address.json")
host = 'http://' + ip + '/api/v2.0.0/'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='
}

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

if not rospy.core.is_initialized():
    try:
        rospy.init_node('dash_app', anonymous=True)
        print("ROS node 'dash_app' initialized successfully.")
    except rospy.exceptions.ROSException as e:
        print(f"Error initializing ROS node: {e}")

if rospy.core.is_initialized():
    pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
else:
    pub = None
    print("ROS not properly initialized, publisher not created.")

linear_speed = 0.5
angular_speed = 0.3

if pub:
    joystick_control = TeleopControl(pub, linear_speed, angular_speed)
    joystick_control.stop()  

else:
    class DummyTeleopControl:
        def __init__(self):
            pass
        def create_joystick_popup(self):
            return html.Div("ROS not available, TeleopControl is disabled.")

    joystick_control = DummyTeleopControl()

login_page = LoginPage()
change_password_page = ChangePasswordPage()
sidebar = Sidebar()
status_bar = StatusBar()
map_section = MapSection()
map_api = MapAPI()
map_api.register_callbacks(app)

app.layout = html.Div(
    [
        dcc.Location(id='url', refresh=False),
        html.Div(id="app-container", children=[login_page.layout]),
        html.Div(id="joystick-output", style={"margin": "20px", "fontSize": "0px"}),
    ]
)
register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8000)