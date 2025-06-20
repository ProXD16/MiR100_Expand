import dash, rospy, tf, requests
import json
import os
import time
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
from page_analystic.layout import DistanceMonitorApp
from page_analystic.callbacks import *
from page_programming.layout import LayoutManager as ProgrammingLayoutManager
import page_programming.callbacks
from page_help.layout import MiR100Manual
import subprocess
import psutil
from get_ip_address import load_ip_from_json

# Initialize components
login_page = LoginPage()
change_password_page = ChangePasswordPage()
sidebar = Sidebar()
status_bar = StatusBar()
map_section = MapSection()
map_api = MapAPI()
path_guides = PathGuideLayout()
distance_monitor = DistanceMonitorApp()
programming_layout_manager = ProgrammingLayoutManager()
mir_manual = MiR100Manual()

ip = load_ip_from_json("database_json/ip_address.json")
host = 'http://' + ip + '/api/v2.0.0/'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='
}

_last_battery_update = None

def _load_simulation_mode(simulation_state_path="simulation_state.json"):
    """
    Load mode from simulation_state.json.
    Returns 'simulation' or 'real', defaulting to 'simulation' on error.
    """
    try:
        with open(simulation_state_path, 'r') as f:
            state = json.load(f)
        mode = state.get("mode", "simulation")
        return mode
    except Exception as e:
        print(f"Failed to load mode from {simulation_state_path}: {e}. Defaulting to simulation.")
        return "simulation"

def _load_simulated_battery(battery_file_path="database_json/battery_percent.json"):
    """
    Load simulated battery level from JSON file.
    Returns the battery level, defaulting to 100.0 if file doesn't exist or on error.
    """
    try:
        if os.path.exists(battery_file_path):
            with open(battery_file_path, 'r') as f:
                data = json.load(f)
                battery_percent_current = data.get("battery_percentage", 100)
                if battery_percent_current == 0:
                    battery_percent_current = 100
                    return battery_percent_current
                return float(data.get("battery_percentage", 100.0))
        return 100.0
    except Exception as e:
        print(f"Failed to load simulated battery level from {battery_file_path}: {e}. Defaulting to 100.0.")
        return 100.0

def _save_simulated_battery(battery_level, battery_file_path="database_json/battery_percent.json"):
    """
    Save simulated battery level to JSON file.
    """
    try:
        os.makedirs(os.path.dirname(battery_file_path), exist_ok=True)
        with open(battery_file_path, 'w') as f:
            json.dump({"battery_percentage": battery_level}, f, indent=2)
        print(f"Saved simulated battery level {battery_level}% to {battery_file_path}")
    except Exception as e:
        print(f"Failed to save simulated battery level to {battery_file_path}: {e}")

@callback(
    Output("app-container", "children"),
    Input("login-button", "n_clicks"),
    State("username", "value"),
    State("password", "value"),
    prevent_initial_call=True
)
def login(n_clicks, username, password):
    if authenticate(username, password):
        status_bar_height = "60px"
        return html.Div(
            [
                dcc.Location(id='url', refresh=False),
                status_bar.create_status_bar(),
                sidebar.create_sidebar(),
                html.Div(id="page-content", style={
                    "marginLeft": "250px",
                    "paddingTop": status_bar_height,
                    "height": f"calc(100vh - {status_bar_height})",
                    "overflowY": "auto"
                }),
            ],
            style={"background": "#BDC3C7", "height": "100vh", "overflow": "hidden"},
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
        Output("docker-modal", "is_open"),
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
        Input("cancel-docker-btn", "n_clicks"),
    ],
    [
        State("name-dockeranger", "value"),
        State("docker-x", "value"),
        State("docker-y", "value"),
        State("docker-z", "value"),
        State("docker-w", "value"),
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
            return no_update, name_docker, robot_x, robot_y, robot_z_orientation, robot_w_orientation, no_update
        except (tf.Exception, tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            return no_update, name_docker, None, None, None, None, "Không thể lấy vị trí robot"

    elif button_id == "add-docker-btn":
        if x_val is not None and y_val is not None and name_docker is not None:
            save_docker_to_json(name_docker, x_val, y_val, z_val, w_val)
            generate_docker_image()
            return False, "", None, None, None, None, f"Đã thêm điểm Docker"
        return no_update, name_docker, x_val, y_val, z_val, w_val, "Vui lòng nhập X hoặc Y hoặc Tên trạm sạc"

    elif button_id == "cancel-docker-btn":
        return False, "", None, None, None, None, no_update

    return no_update, no_update, no_update, no_update, no_update, no_update, no_update

@callback(
    [Output("pause-button", "children"), Output("pause-button", "className")],
    Input("pause-button", "n_clicks"),
    State("pause-button", "children"),
    prevent_initial_call=True
)
def toggle_pause(n_clicks, current_icon_children):
    if n_clicks:
        is_playing = False
        if isinstance(current_icon_children, dict) and 'props' in current_icon_children:
            if 'className' in current_icon_children['props'] and 'fa-play' in current_icon_children['props']['className']:
                is_playing = True

        if is_playing:
            return html.I(className="fas fa-pause"), "btn btn-warning btn-sm me-2"
        else:
            return html.I(className="fas fa-play"), "btn btn-success btn-sm me-2"
    return no_update, no_update

@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    shared_interval = dcc.Interval(
        id='page-specific-interval-component',
        interval=1*1000,
        n_intervals=0
    )

    if pathname == '/draw-mode':
        return html.Div(
            [
                status_bar.create_status_bar(),
                html.Iframe(
                    src="/assets/drawing_tool.html",
                    style={"width": "100%", "height": "1000px", "border": "none"}
                ),
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,
                    n_intervals=0
                )
            ]
        )
    elif pathname == '/maps':
        return html.Div(
            [
                status_bar.create_status_bar(),
                map_section.create_map_section(),
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,
                    n_intervals=0
                )
            ]
        )
    elif pathname == '/change-password':
        return html.Div(
            [
                status_bar.create_status_bar(),
                change_password_page.layout,
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,
                    n_intervals=0
                )
            ]
        )
    elif pathname == '/rviz':
        return html.Div(
            style={
                'paddingTop': '25px'
            },
            children=[
                status_bar.create_status_bar(),
                create_rviz_section(),
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,
                    n_intervals=0
                )
            ]
        )
    elif pathname == '/missions':
        return html.Div(
            style={
                'paddingTop': '40px',
                "height": "100vh",
                "overflowY": "auto",
            },
            children=[
                status_bar.create_status_bar(),
                mission_queue_layout(),
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,
                    n_intervals=0
                )
            ]
        )
    elif pathname == '/map-api':
        return html.Div(
            [
                status_bar.create_status_bar(),
                map_api.create_map_api(),
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,
                    n_intervals=0
                )
            ]
        )
    elif pathname == '/path-guides':
        return html.Div(
            [
                status_bar.create_status_bar(),
                path_guides.create_layout(),
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,
                    n_intervals=0
                )
            ]
        )
    elif pathname == '/programming':
        status_bar_height = "60px"
        page_content_program_style = {
            "height": "100vh",
            "overflowY": "auto",
            "paddingTop": "40px",
        }
        programming_page_shell_style = {
            "height": "100vh",
            "position": "relative",
        }
        return html.Div(
            [
                status_bar.create_status_bar(),
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,
                    n_intervals=0
                ),
                dcc.Location(id="url_program", refresh=False),
                html.Div(id="page-content-program", style=page_content_program_style),
                dcc.Store(id="page-state", data={"current_page": "main"}),
                dcc.Store(id="program-commands-store", data=[]),
                dcc.Store(id="editing-program-name-store", data=None),
                dcc.Store(id="save-status-store"),
                html.Div(id="toast-container", style={"position": "fixed", "top": "80px", "right": "20px", "zIndex": 1050}),
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle("Confirm Deletion")),
                        dbc.ModalBody(id="delete-modal-body-content"),
                        dbc.ModalFooter([
                            dbc.Button("Cancel", id="cancel-delete-modal-btn", color="secondary", outline=True, className="ms-auto"),
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
                dbc.Modal(
                    [
                        dbc.ModalHeader(dbc.ModalTitle("Confirm Delete from Queue")),
                        dbc.ModalBody(id="delete-queue-item-modal-body-content"),
                        dbc.ModalFooter([
                            dbc.Button("Cancel", id="cancel-delete-queue-item-modal-btn", color="secondary", outline=True, className="ms-auto"),
                            dbc.Button("Confirm Delete", id="confirm-delete-queue-item-modal-btn", color="danger"),
                        ]),
                    ],
                    id="delete-queue-item-confirm-modal", is_open=False,
                ),
                dcc.Store(id="item-index-to-delete-from-queue-store", data=None),
            ], style=programming_page_shell_style
        )
    elif pathname == '/analystic':
        return html.Div(
            style={
                'paddingTop': '30px',
                'height': '100vh',
                "overflowY": "auto"
            },
            children=[
                status_bar.create_status_bar(),
                distance_monitor.setup_layout(),
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,
                    n_intervals=0
                )
            ]
        )
    else:
        return html.Div(
            [
                status_bar.create_status_bar(),
                map_section.create_map_section(),
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000,
                    n_intervals=0
                )
            ]
        )

@callback(
    [
        Output("index-link", "active"),
        Output("draw-mode-link", "active"),
        Output("rviz-link", "active"),
        Output("mission-link", "active"),
        Output("map-api-link", "active"),
        Output("path-guides-link", "active"),
        Output("programming-link", "active"),
        Output("analystic-link", "active"),
        Output("user-groups-link", "active"),
        Output("paths-link", "active"),
        Output("marker-types-link", "active"),
        Output("help-link", "active"),
        Output("change-password-link", "active"),
    ],
    Input('url', 'pathname'),
    prevent_initial_call=True
)
def update_active_link(pathname):
    nav_links = [
        {"href": "/", "id": "index-link"},
        {"href": "/draw-mode", "id": "draw-mode-link"},
        {"href": "/rviz", "id": "rviz-link"},
        {"href": "/missions", "id": "mission-link"},
        {"href": "/map-api", "id": "map-api-link"},
        {"href": "/path-guides", "id": "path-guides-link"},
        {"href": "/programming", "id": "programming-link"},
        {"href": "/analystic", "id": "analystic-link"},
        {"href": "/user-group", "id": "user-groups-link"},
        {"href": "/paths", "id": "paths-link"},
        {"href": "/marker-types", "id": "marker-types-link"},
        {"href": "/help", "id": "help-link"},
        {"href": "/change-password", "id": "change-password-link"},
    ]

    active_states = [False] * len(nav_links)
    for i, link in enumerate(nav_links):
        if link["href"] == pathname:
            active_states[i] = True
        elif link["href"] == "/programming" and pathname.startswith("/programming"):
            active_states[i] = True

    return active_states

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
            html.Img(src="/assets/map_image.png", style={"width": "100%", "border": "2px solid #34495E"}),
            html.P(translation['ready'], className="text-info mt-2"),
            html.Div(id="content-area"),
        ],
        style={
            "padding": "20px",
            "flex": "1",
            "background": "#ECF0F1",
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
    Output("battery-percen", "children"),
    Input("interval-component", "n_intervals")
)
def update_battery_status(n):
    global _last_battery_update
    simulation_state_path = "database_json/simulation_state.json"
    battery_file_path = "database_json/battery_percent.json"
    mode = _load_simulation_mode(simulation_state_path)

    if mode == "real":
        try:
            response = requests.get(host + '/status', headers=headers, timeout=2)
            response.raise_for_status()
            data = response.json()
            battery_level = data.get("battery_percentage", "--")
            if isinstance(battery_level, (int, float)):
                battery_level = round(float(battery_level))
                return f"{battery_level}%"
            return "--%"
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch real battery level: {e}")
            return "--%"
        except Exception as e:
            print(f"Error processing real battery data: {e}")
            return "--%"
    else:  # Simulation mode
        # Load current battery level from JSON
        battery_level = _load_simulated_battery(battery_file_path)
        
        # Initialize last update time if None
        if _last_battery_update is None:
            _last_battery_update = time.time()
        
        # Check if 30 seconds have passed to decrement battery
        current_time = time.time()
        if (current_time - _last_battery_update) >= 30.0:
            # Decrement battery by 1% if above 0
            if battery_level > 0.0:
                battery_level = max(0.0, battery_level - 1.0)
                _save_simulated_battery(battery_level, battery_file_path)
                print(f"Simulation mode: Battery level decreased to {battery_level}%")
            _last_battery_update = current_time
        
        return f"{round(battery_level)}%"

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
    except (TypeError, ValueError):
        message = message_template

    icon_class = "fas fa-question-circle me-2"
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
        badge_color = "primary"
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

def update_simulation_state():
    try:
        simulation_data = {
            "mode": "null",
            "simulation_running": False
        }
        json_path = "simulation_state.json"
        dir_name = os.path.dirname(json_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(simulation_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Đã cập nhật simulation state: {simulation_data}")
    except Exception as e:
        print(f"⚠️ Lỗi khi cập nhật simulation state: {e}")
        try:
            backup_dir = "database_json"
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, "simulation_state.json")
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(simulation_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Đã cập nhật simulation state tại backup path: {backup_path}")
        except Exception as backup_error:
            print(f"⚠️ Lỗi cả backup path: {backup_error}")

@callback(
    [Output("url", "pathname", allow_duplicate=True),
     Output("url", "refresh", allow_duplicate=True),
     Output("admin-popover", "is_open", allow_duplicate=True)],
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
            return "/", True, False
        except Exception as e:
            print(f"⚠️ Lỗi khi logout: {e}")
            return "/", True, False
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
                proc_info = proc.info
                p_name = proc_info['name']
                p_cmdline = proc_info['cmdline'] if proc_info['cmdline'] else []

                should_terminate = False
                if p_name in ros_process_names:
                    should_terminate = True
                else:
                    cmd_str = ' '.join(p_cmdline).lower()
                    if any(ros_name in cmd_str for ros_name in ros_process_names):
                        should_terminate = True

                if should_terminate:
                    print(f"🎯 Terminating: {p_name} (PID: {proc_info['pid']})")
                    proc.terminate()
                    terminated_summary.append(f"Terminated {p_name} (PID: {proc_info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        print("⏳ Chờ processes tắt (3 giây)...")
        time.sleep(3)

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_info = proc.info
                p_name = proc_info['name']
                if p_name in ros_process_names and proc.is_alive():
                    print(f"💀 Force killing: {p_name} (PID: {proc_info['pid']})")
                    proc.kill()
                    terminated_summary.append(f"KILLED {p_name} (PID: {proc_info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        print(f"⚠️ Lỗi khi sử dụng psutil: {e}")

    backup_commands = {
        'pkill -f': ['roscore', 'roslaunch', 'rosrun', 'rviz', 'rosmaster'],
        'killall -9': ['roscore', 'roslaunch', 'rosrun', 'rviz', 'rosmaster']
    }
    for tool_cmd, targets in backup_commands.items():
        tool = tool_cmd.split()[0]
        args = tool_cmd.split()[1:] if len(tool_cmd.split()) > 1 else []
        print(f"🔄 Sử dụng backup method ({tool_cmd})...")
        for target in targets:
            try:
                full_command = [tool] + args + [target]
                result = subprocess.run(full_command, capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    print(f"✅ {tool_cmd} {target} successful or process not found.")
                terminated_summary.append(f"Attempted {tool_cmd} {target}")
            except subprocess.TimeoutExpired:
                print(f"⏰ Timeout khi chạy {tool_cmd} {target}")
            except FileNotFoundError:
                print(f"⚠️ Command '{tool}' not found. Skipping remaining uses of this tool.")
                break
            except Exception as e:
                print(f"⚠️ Lỗi khi chạy {tool_cmd} {target}: {e}")

    print("🧹 Cleaning up ROS temporary files (log directory)...")
    try:
        ros_log_path = os.path.expanduser("~/.ros/log")
        if os.path.isdir(ros_log_path):
            print(f"✅ ROS log directory cleanup attempted for {ros_log_path} (manual check/rm recommended for safety).")
        else:
            print(f"ℹ Info: ROS log directory not found at {ros_log_path}.")
    except Exception as e:
        print(f"⚠️ Lỗi cleanup ROS logs: {e}")

    if terminated_summary:
        print(f"✅ Tóm tắt các hành động tắt processes: {terminated_summary}")
    else:
        print("ℹ Không có ROS processes nào được tìm thấy hoặc không có hành động nào được thực hiện qua psutil.")

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

@callback(
    Output("program-queue-collapse", "is_open"),
    Input("program-queue-button", "n_clicks"),
    State("program-queue-collapse", "is_open"),
    prevent_initial_call=True
)
def toggle_program_queue(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@callback(
    Output("program-list-container", "children"),
    Input("program-queue-collapse", "is_open"),
    prevent_initial_call=True
)
def update_program_list(is_open):
    if is_open:
        status_bar = StatusBar()
        programs = status_bar.load_program_queue()
        return status_bar.create_program_list(programs)
    return []

@callback(
    Output("joystick-popover", "is_open"),
    [Input("joystick-popover-target", "n_clicks")],
    [State("joystick-popover", "is_open")]
)
def toggle_joystick_popover(n_joystick, is_joystick_open):
    if n_joystick:
        return not is_joystick_open
    return is_joystick_open

@callback(
    Output("voice-chat-popover", "is_open"),
    Input("voice-chat-popover-target", "n_clicks"),
    State("voice-chat-popover", "is_open"),
    prevent_initial_call=True
)
def toggle_voice_chat_popover(n_clicks_voice_chat, is_open_voice_chat):
    if n_clicks_voice_chat:
        return not is_open_voice_chat
    return is_open_voice_chat

@callback(
    [Output("battery-icon", "icon"), Output("battery-icon", "style")],
    Input("battery-percen", "children")
)
def update_battery_icon(battery_percentage):
    try:
        percent = float(battery_percentage.strip("%"))
        base_style = {"marginRight": "12px", "transform": "rotate(90deg)", "transformOrigin": "center"}
        if 60 <= percent <= 100:
            return "ion:battery-full", {**base_style, "color": "#4CAF50"}
        elif 20 <= percent < 60:
            return "ion:battery-half", {**base_style, "color": "#FFC107"}
        else:
            return "ion:battery-low", {**base_style, "color": "#FF0000"}
    except (ValueError, AttributeError):
        return "ion:battery-low", {**base_style, "color": "#FF0000"}
