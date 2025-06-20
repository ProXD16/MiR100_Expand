import time
import threading
from dash import html, Input, Output, State
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
import os
import json
from dash_iconify import DashIconify
import subprocess

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

def status_callback(msg):
    global last_status_time, status_succeeded

    if not msg.status_list:
        return
    
    # Check if the last status is 3 (SUCCEEDED)
    last_status = msg.status_list[-1]
    if last_status.status == 3:  # SUCCEEDED
        if not status_succeeded:
            last_status_time = time.time()
            status_succeeded = True
    else:
        status_succeeded = False
        last_status_time = None

rospy.Subscriber("/move_base/status", GoalStatusArray, status_callback)

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
        cancel_pub = rospy.Publisher("/move_base/cancel", GoalID, queue_size=10)
        cancel_pub.publish(GoalID())
        print("📍 Sent cancel signal to /move_base/cancel")
        if mission_running and pub is not None:
            twist = Twist()
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            pub.publish(twist)
            print("🛑 Published cmd_vel = (0, 0) to stop robot.")

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

    if status_succeeded and time.time() - last_status_time > 3:
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
                twist = Twist()
                pub.publish(twist)
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
        twist = Twist()
        pub.publish(twist)
        return "🛑 Emergency Stop Activated!"

    angle = data["angle"]
    force = data["force"]

    if force == 0:
        twist = Twist()
        pub.publish(twist)
        return "⏹ Robot Stopped"
    angle = angle % 360
    linear, angular = 0.0, 0.0

    linear = math.sin(math.radians(angle)) * force * speed_scale
    angular = math.cos(math.radians(angle)) * force * speed_scale * 2.0

    linear = max(min(linear, 1.0), -1.0)
    angular = max(min(angular, 2.0), -2.0)

    twist = Twist()
    twist.linear.x = linear
    twist.angular.z = angular
    pub.publish(twist)

    return f"🚀 Moving: Linear = {linear:.2f} m/s, Angular = {angular:.2f} rad/s"

process = None

@callback(
    [Output("play-programming-btn", "children"),
     Output("play-programming-btn", "style")],
    [Input("play-programming-btn", "n_clicks"),
     Input("check-status-interval", "n_intervals")],
    [State("play-programming-btn", "children")],
    prevent_initial_call=True
)
def toggle_play_program(n_clicks, n_intervals, current_children):
    """Callback to toggle play/pause, run main_executor.py, and handle status 3"""
    global process, status_succeeded, last_status_time

    # Path to the main_executor.py script
    script_path = "page_programming/ultis/main_executor.py"
    
    # Default style for the button
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

    # Determine which input triggered the callback
    ctx = callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Check current button state
    is_playing = current_children[1]['props']['children'] == "Pause"

    if triggered_id == "check-status-interval":
        # Handle status 3 (SUCCEEDED) persisting for 3 seconds
        if status_succeeded and last_status_time and time.time() - last_status_time > 3:
            status_succeeded = False
            last_status_time = None
            if process is not None:
                process.terminate()
                process = None
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
                        "fontFamily": "Arial, sans-serif",
                        "fontSize": "13px",
                        "fontWeight": "600"
                    }
                )
            ], {
                **base_style,
                "backgroundColor": "#007bff",
                "boxShadow": "0 2px 6px rgba(0,123,255,0.3)"
            }
        return no_update, no_update

    elif triggered_id == "play-programming-btn":
        if is_playing:
            # Stop the program
            if process is not None:
                process.terminate()
                process = None
            # Publish cancel message to /move_base/cancel
            cancel_pub.publish(GoalID())
            print("📍 Sent cancel signal to /move_base/cancel")
            # Publish zero velocity to /cmd_vel
            if pub is not None:
                twist = Twist()
                twist.linear.x = 0.0
                twist.angular.z = 0.0
                pub.publish(twist)
                print("🛑 Published cmd_vel = (0, 0) to stop robot.")
            # Change to Play state
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
                        "fontFamily": "Arial, sans-serif",
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
            # Start the program in a separate thread
            def run_script():
                global process
                try:
                    process = subprocess.Popen(["python3", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    process.communicate()
                except Exception as e:
                    print(f"Error running main_executor.py: {e}")

            threading.Thread(target=run_script, daemon=True).start()
            
            # Change to Pause state
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
                        "fontFamily": "Arial, sans-serif",
                        "fontSize": "13px",
                        "fontWeight": "600"
                    }
                )
            ], {
                **base_style,
                "backgroundColor": "#dc3545",
                "boxShadow": "0 2px 6px rgba(220,53,69,0.3)"
            }