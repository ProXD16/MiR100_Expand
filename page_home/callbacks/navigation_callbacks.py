import time
import threading
from dash import html, Input, Output, State, no_update
from components import RVizSection
from page_draw_mode.function_draw_mode import *
from dash import callback_context
import numpy as np
from make_marker_with_json.process_with_json import *
from make_marker_with_json.generate_image_from_json import *
from components import button_default_manual_style, button_active_manual_style
from geometry_msgs.msg import Twist
import math
import rospy
from actionlib_msgs.msg import GoalID, GoalStatusArray
from nav_msgs.msg import Odometry
import os
import json
from dash_iconify import DashIconify
import subprocess
import queue
import psutil

# Initialize publisher without node initialization
try:
    rospy.init_node('mir_joystick_interface', anonymous=True)
    pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    cancel_pub = rospy.Publisher("/move_base/cancel", GoalID, queue_size=10)
    cancel_msg = GoalID()
    cancel_pub.publish(cancel_msg)
except Exception as e:
    print(f"ROS initialization failed: {e}")
    pub = None

stop_requested = None
mission_running = None
last_status_time = None
status_succeeded = False
linear_vel = 0.0
angular_vel = 0.0
process_completed = False

def status_callback(msg):
    global last_status_time, status_succeeded
    if not msg.status_list:
        return
    last_status = msg.status_list[-1]
    if last_status.status == 3:  # SUCCEEDED
        if not status_succeeded:
            last_status_time = time.time()
            status_succeeded = True
    else:
        status_succeeded = False
        last_status_time = None

def odom_callback(msg):
    global linear_vel, angular_vel
    linear_vel = msg.twist.twist.linear.x
    angular_vel = msg.twist.twist.angular.z

rospy.Subscriber("/move_base/status", GoalStatusArray, status_callback)
rospy.Subscriber("/odom", Odometry, odom_callback)

PAUSE_BUTTON_1_STYLE = {
    "width": "100%",
    "height": "100px",
    "display": "flex",
    "justifyContent": "center",
    "alignItems": "center",
    "fontSize": "4em",
    "borderRadius": "10px",
    "marginBottom": "10px",
    "marginTop": "10px",
    "backgroundColor": "#003049"
}

def run_mission_in_thread(mission_list, rviz_section):
    global stop_requested, mission_running
    mission_running = True
    
    for mission in mission_list:
        if stop_requested:
            break
        rviz_section.publish_goal(mission["x"], mission["y"], np.arctan2(mission["z"], mission["w"]))
        start_time = time.time()
        while not check_goal_status():
            if time.time() - start_time > 3:
                print("Timeout: Goal not completed!")
                break
            if stop_requested:
                break
            time.sleep(1)
        
        if not stop_requested:
            print(f"Completed mission: {mission['id']}")
            remove_completed_mission(mission['id'])
    
    mission_running = False

@callback(
    [Output("pause-button", "children", allow_duplicate=True),
     Output("pause-button", "className", allow_duplicate=True),
     Output("pause-button-1", "children", allow_duplicate=True),
     Output("pause-button-1", "style", allow_duplicate=True)],
    [Input("pause-button", "n_clicks"),
     Input("pause-button-1", "n_clicks")],
    [State("pause-button", "children"),
     State("pause-button-1", "children")],
    prevent_initial_call=True
)
def toggle_pause(pause_n_clicks, pause_1_n_clicks, current_icon, current_icon_1):
    global stop_requested, mission_running
    stop_requested = False
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update
    
    mission_list = load_mission_data()
    if not mission_list and 'fa-pause' in current_icon['props']['className']:
        pause_button_1_style = PAUSE_BUTTON_1_STYLE.copy()
        pause_button_1_style.update({"color": "#08702B"})  
        return (html.I(className="fas fa-play"), "btn btn-success btn-sm me-2",
                html.I(className="fas fa-play"), pause_button_1_style)
    
    if 'fa-play' in current_icon['props']['className']:
        if not mission_list:
            print("No missions in marker_mission.json!")
            pause_button_1_style = PAUSE_BUTTON_1_STYLE.copy()
            pause_button_1_style.update({"color": "#08702B"})  
            return (html.I(className="fas fa-play"), "btn btn-success btn-sm me-2",
                    html.I(className="fas fa-play"), pause_button_1_style)
        
        stop_requested = False
        rviz_section = RVizSection()
        mission_thread = threading.Thread(target=run_mission_in_thread, args=(mission_list, rviz_section))
        mission_thread.daemon = True  
        mission_thread.start()
        pause_button_1_style = PAUSE_BUTTON_1_STYLE.copy()
        pause_button_1_style.update({"color": "#FFC107"}) 
        return (html.I(className="fas fa-pause"), "btn btn-warning btn-sm me-2",
                html.I(className="fas fa-pause"), pause_button_1_style)
    else:
        stop_requested = True
        try:
            cancel_pub = rospy.Publisher("/move_base/cancel", GoalID, queue_size=10)
            cancel_pub.publish(GoalID())
            print("📍 Sent cancel signal to /move_base/cancel")
        except Exception as e:
            print(f"Error publishing cancel: {e}")
        if mission_running and pub is not None:
            try:
                twist = Twist()
                twist.linear.x = 0.0
                twist.angular.z = 0.0
                pub.publish(twist)
                print("🛑 Published cmd_vel = (0, 0) to stop robot.")
            except Exception as e:
                print(f"Error publishing cmd_vel: {e}")

        pause_button_1_style = PAUSE_BUTTON_1_STYLE.copy()
        pause_button_1_style.update({"color": "#08702B"}) 
        return (html.I(className="fas fa-play"), "btn btn-success btn-sm me-2",
                html.I(className="fas fa-play"), pause_button_1_style)

@callback(
    [Output("pause-button", "children", allow_duplicate=True),
     Output("pause-button", "className", allow_duplicate=True),
     Output("pause-button-1", "children", allow_duplicate=True),
     Output("pause-button-1", "style", allow_duplicate=True)],
    Input("check-status-interval", "n_intervals"),
    prevent_initial_call="initial_duplicate"
)
def reset_button_when_done(n):
    global status_succeeded, last_status_time

    if status_succeeded and last_status_time and time.time() - last_status_time > 3:
        status_succeeded = False
        last_status_time = None
        pause_button_1_style = PAUSE_BUTTON_1_STYLE.copy()
        pause_button_1_style.update({"color": "#08702B"})  
        return (html.I(className="fas fa-play"), "btn btn-success btn-sm me-2",
                html.I(className="fas fa-play"), pause_button_1_style)
    
    return no_update, no_update, no_update, no_update

@callback(
    Output("joystick-modal", "is_open"),
    Input("close-joystick-btn", "n_clicks"),
    State("joystick-modal", "is_open"),
    prevent_initial_call=True
)
def close_joystick(n_clicks, is_open):
    return not is_open
    
@callback(
    [Output("joystick-container", "style"),
     Output("manual-control", "style"),
     Output("interval-joystick", "disabled")],
    Input("manual-control", "n_clicks"),
    State("joystick-container", "style"),
    prevent_initial_call=True
)
def toggle_joystick(n_clicks, current_style):
    if n_clicks and current_style:
        if current_style.get("display") == "none":
            return {"display": "block"}, button_active_manual_style, False
        else:
            if pub is not None:
                try:
                    twist = Twist()
                    pub.publish(twist)
                except Exception as e:
                    print(f"Error publishing twist: {e}")
            return {"display": "none"}, button_default_manual_style, True
    return {"display": "none"}, button_default_manual_style, True

@callback(
    Output("joystick-data", "data"),
    Input("joystick", "angle"),
    Input("joystick", "force"),
    prevent_initial_call=True
)
def update_joystick_data(angle, force):
    MAX_FORCE_THRESHOLD = 0.5
    if force is not None and force > MAX_FORCE_THRESHOLD:
        return {"angle": angle or 0, "force": force or 0}
    return {"angle": 0, "force": 0}  

@callback(
    Output("status-joystick-data", "data"),
    Input("status-joystick", "angle"),
    Input("status-joystick", "force"),
    prevent_initial_call=True
)
def update_status_joystick_data(angle, force):
    MAX_FORCE_THRESHOLD = 0.5
    if force is not None and force > MAX_FORCE_THRESHOLD:
        return {"angle": angle or 0, "force": force or 0}
    return {"angle": 0, "force": 0}

@callback(
    Output("joystick-output", "children", allow_duplicate=True),
    Input("interval-joystick", "n_intervals"),
    State("joystick-data", "data"),
    State("speed-scale", "value"),
    State("emergency-stop", "on"),
    prevent_initial_call=True
)
def send_twist(n, data, speed_scale, emergency_stop):
    if pub is None:
        return "⚠️ ROS not initialized!"

    if emergency_stop:
        try:
            twist = Twist()
            pub.publish(twist)
        except Exception as e:
            print(f"Error publishing twist: {e}")
        return "🛑 Emergency Stop Activated!"

    angle = data["angle"]
    force = data["force"]

    if force == 0:
        try:
            twist = Twist()
            pub.publish(twist)
        except Exception as e:
            print(f"Error publishing twist: {e}")
        return "⏹ Robot Stopped"
    
    angle = angle % 360
    linear = math.sin(math.radians(angle)) * force * speed_scale
    angular = math.cos(math.radians(angle)) * force * speed_scale * 2.0

    linear = max(min(linear, 1.0), -1.0)
    angular = max(min(angular, 2.0), -2.0)

    try:
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        pub.publish(twist)
    except Exception as e:
        print(f"Error publishing twist: {e}")

    return f"🚀 Moving: Linear = {linear:.2f} m/s, Angular = {angular:.2f} rad/s"

@callback(
    Output("status-joystick-output", "children", allow_duplicate=True),
    Input("status-interval-joystick", "n_intervals"),
    State("status-joystick-data", "data"),
    State("status-speed-scale", "value"),
    State("status-emergency-stop", "on"),
    prevent_initial_call=True
)
def send_status_twist(n, data, speed_scale, emergency_stop):
    if pub is None:
        return "⚠️ ROS not initialized!"

    if emergency_stop:
        try:
            twist = Twist()
            pub.publish(twist)
        except Exception as e:
            print(f"Error publishing twist: {e}")
        return "🛑 Emergency Stop Activated!"

    angle = data["angle"]
    force = data["force"]

    if force == 0:
        try:
            twist = Twist()
            pub.publish(twist)
        except Exception as e:
            print(f"Error publishing twist: {e}")
        return "⏹ Robot Stopped"
    
    angle = angle % 360
    linear = math.sin(math.radians(angle)) * force * speed_scale
    angular = math.cos(math.radians(angle)) * force * speed_scale * 2.0

    linear = max(min(linear, 1.0), -1.0)
    angular = max(min(angular, 2.0), -2.0)

    try:
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        pub.publish(twist)
    except Exception as e:
        print(f"Error publishing twist: {e}")

    return f"🚀 Moving: Linear = {linear:.2f} m/s, Angular = {angular:.2f} rad/s"

process = None
output_queue = queue.Queue()
process_completed = False

def read_output(process, output_type):
    """Read stdout or stderr from process and put into queue."""
    stream = process.stdout if output_type == "stdout" else process.stderr
    try:
        for line in iter(stream.readline, b''):
            output_queue.put((output_type, line.decode().strip()))
    except Exception as e:
        output_queue.put(("error", f"Error reading {output_type}: {e}"))

def log_output():
    """Log output from queue in a separate thread."""
    while True:
        try:
            output_type, line = output_queue.get_nowait()
            print(f"main_executor.py {output_type}: {line}")
        except queue.Empty:
            time.sleep(0.1)
            continue

# Start logging thread
threading.Thread(target=log_output, daemon=True).start()

@callback(
    [Output("play-programming-btn", "children"),
     Output("play-programming-btn", "style")],
    [Input("play-programming-btn", "n_clicks"),
     Input("check-status-interval", "n_intervals")],
    [State("play-programming-btn", "children")],
    prevent_initial_call=True
)
def toggle_play_program(n_clicks, n_intervals, current_children):
    """Callback to start/stop main_executor.py, save/read button state in JSON, and handle abrupt kills."""
    global process

    script_path = "page_programming/ultis/main_executor.py"
    status_file_path = "database_json/btn_program_status.json"
    
    base_style = {
        "border": "none",
        "borderRadius": "8px",
        "padding": "8px 14px",
        "boxShadow": "0 2px 6px rgba(0,123,255,0.3)",
        "transition": "all 0.3s ease",
        "fontSize": "13px",
        "display": "flex",
        "alignItems": "center"
    }

    def _initialize_status_file():
        """Create status JSON file if it doesn't exist."""
        try:
            if not os.path.exists(status_file_path):
                os.makedirs(os.path.dirname(status_file_path), exist_ok=True)
                with open(status_file_path, 'w') as f:
                    json.dump({"status": "off"}, f, indent=2)
                print(f"Initialized {status_file_path} with status: off")
        except Exception as e:
            print(f"Error initializing {status_file_path}: {e}")

    def _load_status():
        """Load status from JSON file, default to 'off' on error."""
        try:
            with open(status_file_path, 'r') as f:
                data = json.load(f)
                return data.get("status", "off")
        except Exception as e:
            print(f"Error loading {status_file_path}: {e}. Defaulting to 'off'.")
            return "off"

    def _save_status(status):
        """Save status to JSON file."""
        try:
            with open(status_file_path, 'w') as f:
                json.dump({"status": status}, f, indent=2)
            print(f"Saved status '{status}' to {status_file_path}")
        except Exception as e:
            print(f"Error saving status to {status_file_path}: {e}")

    def _kill_stale_process():
        """Kill any running main_executor.py processes if state is 'on' but process is stale."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = proc.info['cmdline'] or []
                if 'python3' in cmdline and script_path in cmdline:
                    print(f"Killing stale main_executor.py process (PID: {proc.pid})")
                    proc.kill()
        except Exception as e:
            print(f"Error killing stale processes: {e}")

    # Initialize JSON file if it doesn't exist
    _initialize_status_file()

    # Load current status from JSON
    json_status = _load_status()

    # Check if button is in "pause" state (playing) based on UI
    is_playing = any(
        isinstance(child, dict) and child.get('props', {}).get('icon') == 'mdi:pause'
        for child in current_children
    )
    print(f"is_playing: {is_playing}, json_status: {json_status}")

    # Handle stale process: if JSON says "on" but no valid process, kill any running main_executor.py
    if json_status == "on" and (process is None or process.poll() is not None):
        _kill_stale_process()
        _save_status("off")
        json_status = "off"

    ctx = callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print(f"Callback triggered by: {triggered_id}")

    if triggered_id == "check-status-interval":
        # Check if process has finished
        if process is not None and process.poll() is not None:
            print(f"Process completed with return code: {process.poll()}")
            process = None
            _save_status("off")
            return [
                DashIconify(
                    icon="mdi:play",
                    width=18,
                    height=18,
                    style={"color": "white", "marginRight": "6px"}
                ),
                html.Span(
                    "Programs",
                    style={
                        "color": "white",
                        "fontFamily": "Arial",
                        "fontSize": "13px",
                        "fontWeight": "600"
                    }
                )
            ], {
                **base_style,
                "backgroundColor": "#007bff",
                "boxShadow": "0 2px 6px rgba(0,123,255,0.3)"
            }
        # If process is still running, ensure JSON is "on"
        if process is not None and process.poll() is None and json_status != "on":
            _save_status("on")
        return no_update, no_update

    elif triggered_id == "play-programming-btn":
        if is_playing:
            # Stop program
            if process is not None:
                try:
                    process.kill()
                    print("🛑 Process main_executor.py killed")
                except Exception as e:
                    print(f"Error killing process: {e}")
                process = None
            _save_status("off")
            return [
                DashIconify(
                    icon="mdi:play",
                    width=18,
                    height=18,
                    style={"color": "white", "marginRight": "6px"}
                ),
                html.Span(
                    "Programs",
                    style={
                        "color": "white",
                        "fontFamily": "Arial",
                        "fontSize": "13px",
                        "fontWeight": "600"
                    }
                )
            ], {
                **base_style,
                "backgroundColor": "#007bff",
                "boxShadow": "0 2px 6px rgba(0,123,255,0.3)"
            }
        else:
            # Start program
            def run_script():
                global process
                try:
                    process = subprocess.Popen(
                        ["python3", script_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=False
                    )
                    print(f"Started main_executor.py with PID: {process.pid}")
                    process.wait()
                    print("main_executor.py process completed")
                except Exception as e:
                    print(f"Error running main_executor.py: {e}")
                    process = None
                    _save_status("off")

            threading.Thread(target=run_script, daemon=True).start()
            _save_status("on")
            return [
                DashIconify(
                    icon="mdi:pause",
                    width=18,
                    height=18,
                    style={"color": "white", "marginRight": "6px"}
                ),
                html.Span(
                    "Programs",
                    style={
                        "color": "white",
                        "fontFamily": "Arial",
                        "fontSize": "13px",
                        "fontWeight": "600"
                    }
                )
            ], {
                **base_style,
                "backgroundColor": "#dc3545",
                "boxShadow": "0 2px 6px rgba(220,53,69,0.3)"
            }