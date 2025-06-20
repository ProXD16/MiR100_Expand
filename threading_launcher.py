import dash, rospy, subprocess, os
from dash import dcc, html
import dash_bootstrap_components as dbc
from flask import request, jsonify
import base64, json, rosnode
import threading 
from page_options import *
from page_draw_mode import *
from make_marker_with_json import *
from page_mission.missions.callbacks import register_callbacks
from page_map.map_api import MapAPI
from page_home.callbacks import *
from page_path_guides import *
from main import main as main_ros_node
from main import *
from listener_topic_from_ros.ros_map_listener import *
from page_options.state_manager import StateManager  # Import StateManager
from page_programming.callbacks import *
from get_ip_address import load_ip_from_json

# Khởi tạo StateManager
state_manager = StateManager()

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
    ],
    prevent_initial_callbacks='initial_duplicate'
)
app.title = "MiR100 Smart Equipment and Robot Lab"
server = app.server  

app.clientside_callback(
    """
    function(pathname) {
        console.log('URL changed to:', pathname);
        return pathname;
    }
    """,
    Output('dummy-output', 'data'),
    Input('url', 'pathname')
)

def run_ros_node():
    try:
        rospy.loginfo("Starting ROS node in a separate thread...")
        main_ros_node()
    except rospy.ROSInterruptException:
        rospy.loginfo("ROS node shutdown requested.")
    except Exception as e:
        rospy.logerr(f"Error in ROS node: {e}")

def run_map_listener():
    try:
        rospy.loginfo("Starting map listener in a separate thread...")
        listener() 
    except rospy.ROSInterruptException:
        rospy.loginfo("Map listener shutdown requested.")
    except Exception as e:
        rospy.logerr(f"Error in map listener: {e}")

# Function để kiểm tra và tạo layout phù hợp
def create_initial_layout():
    """Tạo layout ban đầu dựa trên trạng thái simulation"""
    if state_manager.should_redirect_to_home():
        # Nếu simulation đang chạy, tạo layout home
        from components import Sidebar, StatusBar
        sidebar = Sidebar()
        status_bar = StatusBar()
        return html.Div([
            dcc.Location(id='url', refresh=False),
            html.Div(id="app-container", children=[
                status_bar.create_status_bar(),
                sidebar.create_sidebar(),
                html.Div(id="page-content", style={"marginLeft": "250px"}),
            ], style={"background": "#BDC3C7", "height": "100vh", "overflow": "hidden"}),
            dcc.Store(id='dummy-output')
        ])
    else:
        # Nếu chưa chạy simulation, hiển thị trang options
        return html.Div([
            dcc.Location(id='url', refresh=False),
            html.Div(id="app-container", children=[get_layout()]),
            dcc.Store(id='dummy-output')
        ])

# Register callbacks for other pages
map_api = MapAPI()
map_api.register_callbacks(app)
register_callbacks(app)

# Set the layout - kiểm tra trạng thái simulation
app.layout = create_initial_layout()

@server.route('/save_path_image', methods=['POST'])
def save_path_image():
    data = request.get_json()
    image_data = data['image'].split(',')[1]
    os.makedirs('static', exist_ok=True)
    with open('static/path_img.png', 'wb') as f:
        f.write(base64.b64decode(image_data))
    return jsonify({'status': 'success'})

@server.route('/save_path_json', methods=['POST'])
def save_path_json():
    data = request.get_json()
    os.makedirs('database_json', exist_ok=True)
    with open('database_json/path_drawn.json', 'w') as f:
        json.dump(data['paths'], f, indent=2)
    return jsonify({'status': 'success'})

@server.route('/check_simulation_status', methods=['GET'])
def check_simulation_status():
    """API endpoint để kiểm tra trạng thái simulation"""
    status = state_manager.should_redirect_to_home()
    return jsonify({'simulation_running': status})

@server.route('/clear_simulation_state', methods=['POST'])
def clear_simulation_state():
    """API endpoint để xóa trạng thái simulation (dùng khi tắt terminal)"""
    start_time = time.time()
    try:
        # Check and stop ROS nodes
        if rospy.core.is_initialized():
            try:
                active_nodes = rosnode.get_node_names()
                logger.info(f"Active ROS nodes before shutdown: {active_nodes}")
                if active_nodes:
                    rospy.signal_shutdown("Clear simulation state")
                    time.sleep(0.1)  # Minimal wait
                    active_nodes_after = rosnode.get_node_names()
                    logger.info(f"Active ROS nodes after shutdown: {active_nodes_after}")
                    if not active_nodes_after:
                        logger.info("All ROS nodes shut down")
                    else:
                        logger.warning(f"Some nodes still active: {active_nodes_after}")
                else:
                    logger.info("No active ROS nodes found")
            except rosnode.ROSNodeIOException:
                logger.info("ROS master not running, assuming no nodes")
        else:
            logger.info("ROS not initialized, no nodes to shut down")

        # Clear state manager and reset JSON
        state_manager.clear_state()
        os.makedirs('database_json', exist_ok=True)
        state_file = 'database_json/simulation_state.json'
        with open(state_file, 'w') as f:
            json.dump({"state": "null", "status": "false"}, f, indent=2)
        with open(state_file, 'r') as f:
            content = json.load(f)
        logger.info(f"Simulation state JSON reset: {json.dumps(content, indent=2)}")

        elapsed_time = (time.time() - start_time) * 1000  # ms
        logger.info(f"Clear simulation state completed in {elapsed_time:.2f} ms")
        return jsonify({'status': 'cleared'})
    except Exception as e:
        logger.error(f"Error clearing simulation state: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    ros_thread = threading.Thread(target=run_ros_node, daemon=True)
    ros_thread.start()
    map_listener_thread = threading.Thread(target=run_map_listener, daemon=True)
    map_listener_thread.start()
    app.run(debug=True, host='127.0.0.1', port=8050)