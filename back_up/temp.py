import dash, rospy, tf, requests
from dash import dcc, html, Input, Output, State, callback, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from components import LoginPage, ChangePasswordPage, Sidebar, StatusBar, MapSection
from utils_function.data import authenticate, user_credentials, update_password
from components.draw_mode import create_draw_mode_layout
from page_draw_mode.function_draw_mode import *
from components.rviz_section import create_rviz_section
from make_marker_with_json import *
from page_map.map_api import MapAPI
from page_mission.missions.layout import mission_queue_layout
from page_path_guides import PathGuideLayout
from page_options.callbacks import *

# Import for Programming Page
from page_programming.layout import LayoutManager as ProgrammingLayoutManager
import page_programming.callbacks # This import registers the callbacks from page_programming

login_page = LoginPage()
change_password_page = ChangePasswordPage()
sidebar = Sidebar()
status_bar = StatusBar()
map_section = MapSection()
map_api = MapAPI()
path_guides = PathGuideLayout()

# Instantiate the programming layout manager
programming_layout_manager = ProgrammingLayoutManager()


ip = '192.168.0.172'
host = 'http://' + ip + '/api/v2.0.0/'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='
}

@callback(
    Output("app-container", "children"),
    Input("login-button", "n_clicks"),
    State("username", "value"),
    State("password", "value"),
    prevent_initial_call=True
)
def login(n_clicks, username, password):
    if authenticate(username, password):
        # MODIFIED: Added paddingTop and adjusted height for page-content
        status_bar_height = "60px" # Estimate; adjust if your status bar is different
        return html.Div(
            [
                dcc.Location(id='url', refresh=False),
                status_bar.create_status_bar(),
                sidebar.create_sidebar(),
                html.Div(id="page-content", style={
                    "marginLeft": "250px", # For the main sidebar
                    "paddingTop": status_bar_height,
                    "height": f"calc(100vh - {status_bar_height})",
                    "overflowY": "auto" # Allow page content to scroll
                }),
            ],
            style={"background": "#BDC3C7", "height": "100vh", "overflow": "hidden"}, # Main app container
        )
    else:
        return html.Div([login_page.layout, html.Div("Login Failed", style={"color": "red"})])

@callback(
    [
        Output("position-modal", "is_open"),
        Output("name-position", "value"),
        Output("x-input", "value"),
        Output("y-input", "value"),
        Output("z-input", "value"),
        Output("w-input", "value"),
        Output("content-area", "children"),
    ],
    [
        Input("add-positions-btn", "n_clicks"),
        Input("use-robot-btn", "n_clicks"),
        Input("add-position-btn", "n_clicks"),
        Input("cancel-btn", "n_clicks"),
    ],
    [
        State("name-position", "value"),
        State("x-input", "value"),
        State("y-input", "value"),
        State("z-input", "value"),
        State("w-input", "value"),
        State("position-modal", "is_open"),
    ],
    prevent_initial_call=True
)
def manage_position_modal(add_pos_clicks, use_robot_clicks, add_clicks, cancel_clicks,
                         name_position, x_val, y_val, z_val, w_val, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "add-positions-btn":
        return True, "", None, None, None, None, no_update

    elif button_id == "use-robot-btn":
        try:
            listener = tf.TransformListener()
            listener.waitForTransform("/map", "/base_link", rospy.Time(0), rospy.Duration(1.0))
            (trans, rot) = listener.lookupTransform("/map", "/base_link", rospy.Time(0))
            robot_x, robot_y, _ = trans
            _, _, yaw = tf.transformations.euler_from_quaternion(rot)
            import math
            robot_z_orientation, robot_w_orientation = math.sin(yaw), math.cos(yaw)
            return True, no_update, robot_x, robot_y, robot_z_orientation, robot_w_orientation, no_update
        except (tf.Exception, tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException) as e:
            return True, no_update, no_update, no_update, no_update, no_update, "Không thể lấy vị trí robot"

    elif button_id == "add-position-btn":
        if x_val is not None and y_val is not None and name_position is not None:
            save_position_to_json(name_position, x_val, y_val, z_val, w_val)
            generate_marker_image()
            return False, "", None, None, None, None, f"Đã thêm điểm {name_position} ({x_val}, {y_val})"
        return True, no_update, x_val, y_val, z_val, w_val, "Vui lòng nhập X hoặc Y hoặc Tên vị trí"

    elif button_id == "cancel-btn":
        return False, "", None, None, None, None, no_update

    return no_update, no_update, no_update, no_update, no_update, no_update, no_update

@callback(
    Output("docker-modal", "is_open", allow_duplicate=True),
    Input("add-dockers-btn", "n_clicks"),
    State("docker-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_docker_modal(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return no_update

@callback(
    [
        Output("docker-modal", "is_open"), # Output for opening/closing based on actions inside
        Output("name-docker", "value"),
        Output("docker-x", "value"),
        Output("docker-y", "value"),
        Output("docker-z", "value"),
        Output("docker-w", "value"),
        Output("content-area", "children", allow_duplicate=True),
    ],
    [
        Input("use-robot-docker-btn", "n_clicks"),
        Input("add-docker-btn", "n_clicks"),
        # Ensure you have a distinct cancel button ID for this modal in its layout
        Input("cancel-docker-btn", "n_clicks"), # Assuming 'cancel-docker-btn'
    ],
    [
        State("name-docker", "value"),
        State("docker-x", "value"),
        State("docker-y", "value"),
        State("docker-z", "value"),
        State("docker-w", "value"),
        # No need for State("docker-modal", "is_open") if toggle is separate
    ],
    prevent_initial_call=True
)
def manage_docker_modal_actions(use_robot_clicks, add_clicks, cancel_clicks,
                         name_docker, x_val, y_val, z_val, w_val):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "use-robot-docker-btn":
        try:
            listener = tf.TransformListener()
            listener.waitForTransform("/map", "/base_link", rospy.Time(0), rospy.Duration(1.0))
            (trans, rot) = listener.lookupTransform("/map", "/base_link", rospy.Time(0))
            robot_x, robot_y, _ = trans
            _, _, yaw = tf.transformations.euler_from_quaternion(rot)
            import math
            robot_z_orientation, robot_w_orientation = math.sin(yaw), math.cos(yaw)
            # Keep modal open (no_update), update fields, no message change
            return no_update, name_docker, robot_x, robot_y, robot_z_orientation, robot_w_orientation, no_update
        except (tf.Exception, tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            # Keep modal open, clear robot coords, update message
            return no_update, name_docker, None, None, None, None, "Không thể lấy vị trí robot"

    elif button_id == "add-docker-btn":
        if x_val is not None and y_val is not None and name_docker is not None:
            save_docker_to_json(name_docker, x_val, y_val, z_val, w_val)
            generate_docker_image()
            return False, "", None, None, None, None, f"Đã thêm điểm Docker" # Close modal, clear fields
        # Keep modal open, retain current values, show error message
        return no_update, name_docker, x_val, y_val, z_val, w_val, "Vui lòng nhập X hoặc Y hoặc Tên trạm sạc"

    elif button_id == "cancel-docker-btn": # Use the correct ID for your cancel button
        return False, "", None, None, None, None, no_update # Close modal, clear fields

    return no_update, no_update, no_update, no_update, no_update, no_update, no_update


@callback(
    [Output("pause-button", "children"), Output("pause-button", "className")],
    Input("pause-button", "n_clicks"),
    State("pause-button", "children"), # Children is html.I(...)
    prevent_initial_call=True
)
def toggle_pause(n_clicks, current_icon_children):
    if n_clicks:
        # current_icon_children is a dictionary like {'type': 'I', 'props': {'className': 'fas fa-play'}, 'namespace': 'dash_html_components'}
        # Or it could be a list if multiple children, but here it's expected to be one html.I
        is_playing = False
        if isinstance(current_icon_children, dict) and 'props' in current_icon_children:
            if 'className' in current_icon_children['props'] and 'fa-play' in current_icon_children['props']['className']:
                is_playing = True
        
        if is_playing: # If current icon is play, switch to pause
            return html.I(className="fas fa-pause"), "btn btn-warning btn-sm me-2"
        else: # If current icon is pause (or unknown), switch to play
            return html.I(className="fas fa-play"), "btn btn-success btn-sm me-2"
    return no_update, no_update 


@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    # The status_bar is now part of the main app layout after login,
    # so it doesn't need to be repeatedly added in each page's content.
    # The page-content div itself will have padding to account for the status bar.

    shared_interval = dcc.Interval( # Only if specific pages need their own interval different from global
                    id='page-specific-interval-component', # Use a different ID if truly page-specific
                    interval=1*1000,
                    n_intervals=0
                )

    if pathname == '/draw-mode':
        return html.Div(
            [
                html.Iframe(
                    src="/assets/drawing_tool.html",
                    style={"width": "100%", "height": "100%", "border": "none"} # Takes full height of parent (page-content)
                ),
                # shared_interval # if needed
            ], style={"height": "100%"} # Ensure div takes full height of page-content
        )
    elif pathname == '/maps':
        return map_section.create_map_section() # This component should fill the space
    elif pathname == '/change-password':
        return change_password_page.layout
    elif pathname == '/rviz':
        return create_rviz_section()
    elif pathname == '/missions':
        return mission_queue_layout()
    elif pathname == '/map-api':
        return map_api.create_map_api()
    elif pathname == '/path-guides':
        return path_guides.create_layout()
    elif pathname == '/programming':
        # The shell for the programming page.
        # `page-content-program` will be filled by programming_callbacks.py
        # The dcc.Stores and dbc.Modals are part of this shell.
        # Toast container's `top` style is relative to the viewport.
        # Since page-content has paddingTop, the toast will appear correctly below the status bar.
        status_bar_height = "60px" # Consistent with login callback
        return html.Div(
            [
                dcc.Location(id="url_program", refresh=False),
                html.Div(id="page-content-program", style={"height": "100%"}), # Allow programming content to fill
                dcc.Store(id="page-state", data={"current_page": "main"}),
                dcc.Store(id="program-commands-store", data=[]),
                dcc.Store(id="editing-program-name-store", data=None),
                dcc.Store(id="save-status-store"),
                html.Div(id="toast-container", style={"position": "fixed", "top": f"calc({status_bar_height} + 10px)", "right": "20px", "zIndex": 1050}),
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle("Confirm Deletion")),
                        dbc.ModalBody(id="delete-modal-body-content"),
                        dbc.ModalFooter([
                            dbc.Button("Cancel", id="cancel-delete-modal-btn", color="secondary", className="ms-auto"),
                            dbc.Button("Confirm Delete", id="confirm-delete-modal-btn", color="danger"),
                        ]),
                    ],
                    id="delete-program-confirm-modal", is_open=False,
                ),
                dcc.Store(id="program-to-delete-store", data=None),
                dcc.Store(id="programs-list-refresh-flag", data=0),
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle("Queue Program Action")),
                        dbc.ModalBody(id="play-modal-body-content"),
                        dbc.ModalFooter([
                            dbc.Button("Cancel", id="cancel-play-modal-btn", color="secondary", outline=True),
                            dbc.Button("Append to Queue", id="append-to-queue-btn", color="primary", className="ms-auto"),
                            dbc.Button("Clear & Append to Queue", id="clear-and-append-to-queue-btn", color="warning"),
                        ]),
                    ],
                    id="play-program-action-modal", is_open=False,
                ),
                dcc.Store(id="program-to-play-store", data=None),
                dcc.Store(id="queue-refresh-flag", data=0),
            ], style={"height": "100%"} # This div should also fill its parent (page-content)
        )
    else: # Default page (e.g., Home or /)
        return map_section.create_map_section() # Default to map section

@callback(
    Output("password-status", "children"),
    Input("update-password-button", "n_clicks"),
    State("new-password", "value"),
    State("confirm-password", "value"),
    prevent_initial_call=True
)
def update_password_callback(n_clicks, new_password, confirm_password):
    if n_clicks:
        if not new_password or not confirm_password:
            return html.Div("Please fill in both password fields.", style={"color": "orange"})
        if new_password == confirm_password:
            global user_credentials
            if user_credentials:
                username = list(user_credentials.keys())[0]
                if update_password(username, new_password):
                    return html.Div("Password updated successfully!", style={"color": "green"})
                else:
                    return html.Div("Failed to update password.", style={"color": "red"})
            else:
                return html.Div("User credentials not found.", style={"color": "red"})
        else:
            return html.Div("Passwords do not match.", style={"color": "red"})
    return no_update

@callback(
    Output('map_section', 'children'),
    Input('language-dropdown', 'value')
)
def change_language(language):
    translations = {
        'en': {'title': 'Main Floor', 'map': 'Edit and draw the map', 'ready': 'The map is ready for your work.'},
        'vi': {'title': 'Tầng Chính', 'map': 'Chỉnh sửa và vẽ bản đồ', 'ready': 'Bản đồ đã sẵn sàng cho công việc của bạn.'},
        'es': {'title': 'Piso Principal', 'map': 'Editar y dibujar el mapa', 'ready': 'El mapa está listo para tu trabajo.'},
    }
    translation = translations.get(language, translations['en'])
    return html.Div(
        [
            html.H3(translation['title'], className="mb-3", style={"color": "#2C3E50"}),
            html.P(translation['map'], className="text-muted"),
            html.Img(src="/assets/map_image.png", style={"width": "100%", "border": "2px solid #34495E"}), # Ensure this path is correct
            html.P(translation['ready'], className="text-info mt-2"),
            html.Div(id="content-area"), # This ID is also used by manage_position_modal.
        ],
        style={
            "padding": "20px", # Padding inside the map_section
            "flex": "1",       # If map_section is a flex item
            "background": "#ECF0F1",
            # No margin needed here as parent `page-content` handles it
        },
    )

layout = html.Div(
    [
        dcc.Location(id='url', refresh=False),
        html.Div(id="app-container", children=[login_page.layout]),
        html.Div(id="joystick-output", style={"margin": "20px", "fontSize": "0px"}),
        dcc.Interval(
            id='interval-component',
            interval=1000,
            n_intervals=0
        )
    ]
)

@callback(
    Output("sidebar-nav", "children"),
    Input('url', 'pathname'),
    prevent_initial_call=True
)
def update_active_link(pathname):
    nav_links = [
        {"href": "/", "id": "index-link", "label": "Home"},
        {"href": "/draw-mode", "id": "draw-mode-link", "label": "Draw Mode"},
        {"href": "/rviz", "id": "rviz-link", "label": "RViz"},
        {"href": "/missions", "id": "mission-link", "label": "Missions"},
        {"href": "/map-api", "id": "map-api-link", "label": "Maps"},
        {"href": "/path-guides", "id": "path-guides-link", "label": "Path Guides"},
        {"href": "/programming", "id": "programming-link", "label": "Programming"}, # Updated link
        {"href": "#", "id": "users-link", "label": "Users"},
        {"href": "#", "id": "user-groups-link", "label": "User Groups"},
        {"href": "#", "id": "paths-link", "label": "Paths"},
        {"href": "#", "id": "marker-types-link", "label": "Marker Types"},
        {"href": "#", "id": "footprints-link", "label": "Footprints"},
        {"href": "/change-password", "id": "change-password-link", "label": "Change Password"},
    ]

    updated_links = []
    for link_info in nav_links:
        active = (pathname == link_info["href"])
        # If on a sub-route of programming, keep "Programming" active
        if link_info["href"] == "/programming" and pathname.startswith("/programming"):
            active = True
        # Ensure "Home" is not active if on a specific programming sub-route
        elif link_info["href"] == "/" and pathname.startswith("/programming") and pathname != "/":
             active = False

        updated_links.append(
            dbc.NavLink(
                link_info["label"],
                href=link_info["href"],
                id=link_info["id"],
                className="text-white",
                active=active
            )
        )
    return updated_links

@callback(
    Output("battery-percen", "children"),
    Input("interval-component", "n_intervals")
)
def update_battery_status(n):
    try:
        response = requests.get(host + '/status', headers=headers, timeout=2)
        response.raise_for_status()
        data = response.json()
        battery_level = data.get("battery_percentage", "--")
        if isinstance(battery_level, float):
            battery_level = round(battery_level)
        return f"{battery_level}%"
    except requests.exceptions.RequestException as e:
        # print(f"⚠️ Lỗi khi gọi API (battery status): {e}")
        return "--%"
    except Exception as e:
        # print(f"⚠️ Lỗi không xác định (battery status): {e}")
        return "--%"

@callback(
    [Output('status-text', 'children'),
     Output('status-icon', 'className'),
     Output('status-badge', 'children'),
     Output('status-badge', 'color')],
    [Input('interval-component', 'n_intervals')]
)
def update_charging_status(n):
    json_path = os.path.join("database_json", "mir_status.json")
    latest_status = {"message": "N/A", "args": {}}

    try:
        if os.path.exists(json_path):
            with open(json_path, "r", encoding='utf-8') as f:
                content = json.load(f)
                latest_status = content.get("data", {"message": "No data field", "args": {}})
        else:
            latest_status = {"message": "Status file missing.", "args": {}}

    except json.JSONDecodeError:
        latest_status = {"message": "Invalid JSON format.", "args": {}}
    except Exception as e:
        latest_status = {"message": f"File error: {type(e).__name__}", "args": {}}

    message_template = latest_status.get("message", "Status unavailable")
    args = latest_status.get("args", {})
    try:
        message = message_template % args
    except (TypeError, ValueError): # Catch formatting errors
        message = message_template

    icon_class = "fas fa-question-circle me-2" # Default for unknown
    badge_text = "UNKNOWN"
    badge_color = "secondary"

    msg_lower = str(message).lower()
    if "error" in msg_lower or "lỗi" in msg_lower:
        icon_class = "fas fa-exclamation-triangle me-2"
        badge_color = "danger"
        badge_text = "ERROR"
    elif "executing" in msg_lower or "đang chạy" in msg_lower:
        icon_class = "fas fa-spinner fa-spin me-2"
        badge_text = "EXECUTING"
        badge_color = "success"
    elif "complete" in msg_lower or "hoàn thành" in msg_lower:
        icon_class = "fas fa-check-circle me-2"
        badge_text = "COMPLETED"
        badge_color = "primary" # Changed from default success to distinguish
    elif "waiting" in msg_lower or "đang chờ" in msg_lower:
        icon_class = "fas fa-clock me-2"
        badge_text = "WAITING"
        badge_color = "info"
    elif "ready" in msg_lower or "sẵn sàng" in msg_lower:
        icon_class = "fas fa-thumbs-up me-2"
        badge_text = "READY"
        badge_color = "success"


    return (
        message,
        icon_class,
        badge_text,
        badge_color
    )

import subprocess
import psutil
# import signal # Not explicitly used, psutil handles signals
import os
import time
import json

def update_simulation_state():
    try:
        simulation_data = {
            "mode": "null",
            "simulation_running": False
        }
        json_path = "simulation_state.json"
        # Ensure directory exists if path includes one (e.g., "data/simulation_state.json")
        dir_name = os.path.dirname(json_path)
        if dir_name: # If dirname is not empty, it means there's a directory part
            os.makedirs(dir_name, exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(simulation_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Đã cập nhật simulation state: {simulation_data}")
    except Exception as e:
        print(f"⚠️ Lỗi khi cập nhật simulation state: {e}")
        try:
            backup_dir = "database_json"
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, "simulation_state.json") # Corrected typo "simulate_state"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(simulation_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Đã cập nhật simulation state tại backup path: {backup_path}")
        except Exception as backup_error:
            print(f"⚠️ Lỗi cả backup path: {backup_error}")

@callback(
    [Output("url", "pathname", allow_duplicate=True),
     Output("url", "refresh", allow_duplicate=True),
     Output("admin-popover", "is_open", allow_duplicate=True)], # Popover might be part of logged-in UI
    Input("logout-button", "n_clicks"),
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    if n_clicks:
        try:
            print("🔄 Đang thực hiện logout...")
            terminate_ros_processes()
            update_simulation_state()
            print("✅ Logout thành công!")
            # Redirect to login page (which is typically "/")
            # Refresh the page to ensure clean state, close admin popover
            return "/", True, False
        except Exception as e:
            print(f"⚠️ Lỗi khi logout: {e}")
            return "/", True, False # Still attempt to redirect and refresh on error
    raise PreventUpdate

def terminate_ros_processes():
    ros_process_names = [
        'roslaunch', 'rosrun', 'rviz', 'roscore', 'rosmaster',
        'rosout', 'rosnode', 'rostopic', 'rosservice',
        'rosparam', 'rosbag'
    ]
    terminated_summary = []

    print("🔄 Đang tắt các ROS processes...")
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_info = proc.info # Cache info
                p_name = proc_info['name']
                p_cmdline = proc_info['cmdline'] if proc_info['cmdline'] else []
                
                should_terminate = False
                if p_name in ros_process_names:
                    should_terminate = True
                else: # Check cmdline for ros commands
                    cmd_str = ' '.join(p_cmdline).lower()
                    if any(ros_name in cmd_str for ros_name in ros_process_names):
                        should_terminate = True
                
                if should_terminate:
                    print(f"🎯 Terminating: {p_name} (PID: {proc_info['pid']})")
                    proc.terminate()
                    terminated_summary.append(f"Terminated {p_name} (PID: {proc_info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue # Process ended or inaccessible
        
        print("⏳ Chờ processes tắt (3 giây)...")
        time.sleep(3) # Grace period
        
        # Force kill remaining identified ROS processes
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_info = proc.info
                p_name = proc_info['name']
                if p_name in ros_process_names and proc.is_running(): # Check if still running
                    print(f"💀 Force killing: {p_name} (PID: {proc_info['pid']})")
                    proc.kill()
                    terminated_summary.append(f"KILLED {p_name} (PID: {proc_info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        print(f"⚠️ Lỗi khi sử dụng psutil: {e}")

    # Backup: System commands (pkill, killall)
    # These are less precise than psutil but good fallbacks
    backup_commands = {
        'pkill -f': ['roscore', 'roslaunch', 'rosrun', 'rviz', 'rosmaster'],
        'killall -9': ['roscore', 'roslaunch', 'rosrun', 'rviz', 'rosmaster'] # More aggressive
    }
    for tool_cmd, targets in backup_commands.items():
        tool = tool_cmd.split()[0]
        args = tool_cmd.split()[1:] if len(tool_cmd.split()) > 1 else []
        print(f"🔄 Sử dụng backup method ({tool_cmd})...")
        for target in targets:
            try:
                full_command = [tool] + args + [target]
                result = subprocess.run(full_command, capture_output=True, text=True, timeout=3)
                if result.returncode == 0 : # Indicates success for pkill/killall if process found
                     print(f"✅ {tool_cmd} {target} successful or process not found.")
                terminated_summary.append(f"Attempted {tool_cmd} {target}")
            except subprocess.TimeoutExpired:
                print(f"⏰ Timeout khi chạy {tool_cmd} {target}")
            except FileNotFoundError:
                print(f"⚠️ Command '{tool}' not found. Skipping remaining uses of this tool.")
                break # Stop trying this tool if not found
            except Exception as e:
                print(f"⚠️ Lỗi khi chạy {tool_cmd} {target}: {e}")
    
    # ROS file cleanup (cautious approach)
    print("🧹 Cleaning up ROS temporary files (log directory)...")
    try:
        ros_log_path = os.path.expanduser("~/.ros/log")
        if os.path.isdir(ros_log_path):
            # For safety, one might list files first or archive instead of direct rm -rf
            # subprocess.run(['rm', '-rf', ros_log_path], check=True) # Careful with rm -rf
            print(f"✅ ROS log directory cleanup attempted for {ros_log_path} (manual check/rm recommended for safety).")
        else:
            print(f"ℹ️ ROS log directory not found at {ros_log_path}.")
    except Exception as e:
        print(f"⚠️ Lỗi cleanup ROS logs: {e}")
    
    if terminated_summary:
        print(f"✅ Tóm tắt các hành động tắt processes: {terminated_summary}")
    else:
        print("ℹ️ Không có ROS processes nào được tìm thấy hoặc không có hành động nào được thực hiện qua psutil.")


@callback(
    Output("admin-popover", "is_open"),
    Input("admin-popover-target", "n_clicks"),
    State("admin-popover", "is_open"),
    prevent_initial_call=True
)
def toggle_admin_popover(admin_btn_clicks, is_open):
    if admin_btn_clicks:
        return not is_open
    raise PreventUpdate