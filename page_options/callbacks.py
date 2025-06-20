from dash import html, Input, Output, callback_context, callback, State, dcc
import time, subprocess, dash
import logging
import os
import json
from components import Sidebar, StatusBar, MapSection  # Import components for layout
from page_options.state_manager import StateManager  # Import StateManager

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Khởi tạo StateManager
state_manager = StateManager()

@callback(
    [
        Output('btn-simulation', 'children'),
        Output('url', 'pathname'),
        Output('redirect-interval', 'disabled'),
        Output('app-container', 'children', allow_duplicate=True),
        Output('session-mode', 'data'),
    ],
    Input('btn-simulation', 'n_clicks'),
    prevent_initial_call=True
)
def launch_simulation(n_clicks):
    if n_clicks:
        logger.debug("Simulation button clicked, starting commands...")
        try:
            # Command 1: Start Gazebo simulation
            logger.debug("Launching mir_maze_world.launch")
            subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', 'roslaunch mir_gazebo mir_maze_world.launch; exec bash'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)

            # Command 2: Unpause physics
            logger.debug("Launching unpause_physics")
            subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', 'rosservice call /gazebo/unpause_physics; exec bash'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)

            # Command 3: Start AMCL
            logger.debug("Launching amcl.launch")
            subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', 
                             'roslaunch mir_navigation amcl.launch initial_pose_x:=10.0 initial_pose_y:=10.0; exec bash'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)

            # Command 4: Start planner
            logger.debug("Launching start_planner.launch")
            subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', 
                             'roslaunch mir_navigation start_planner.launch map_file:=$(rospack find mir_gazebo)/maps/maze.yaml virtual_walls_map_file:=$(rospack find mir_gazebo)/maps/maze_virtual_walls.yaml; exec bash'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)

            # Command 5: Start RViz
            logger.debug("Launching RViz")
            subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', 
                             'rviz -d $(rospack find mir_navigation)/rviz/navigation.rviz; exec bash'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Lưu trạng thái simulation đã chạy
            state_manager.save_simulation_state(mode="simulation", running=True)
            
            logger.debug("All commands executed, redirecting to /")
            # Create layout matching login callback in ui_callbacks.py
            sidebar = Sidebar()
            status_bar = StatusBar()
            new_layout = html.Div(
                [
                    dcc.Location(id='url', refresh=False),
                    status_bar.create_status_bar(),
                    sidebar.create_sidebar(),
                    html.Div(id="page-content", style={"marginLeft": "250px"}),
                ],
                style={"background": "#BDC3C7", "height": "100vh", "overflow": "hidden"},
            )
            return "Simulation started!", "/", True, new_layout, "simulation"
        except Exception as e:
            logger.error(f"Error during simulation launch: {e}")
            return f"Error: {e}", dash.no_update, dash.no_update, dash.no_update, dash.no_update
    logger.debug("No click detected, no action taken")
    return "SIMULATION", dash.no_update, dash.no_update, dash.no_update, dash.no_update

@callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('redirect-interval', 'n_intervals'),
    prevent_initial_call=True
)
def force_redirect(n_intervals):
    logger.debug("Forcing redirect to / via interval")
    return "/"

@callback(
    [
        Output("ip-modal", "is_open"),
        Output("stored-ip", "data"),
        Output('url', 'pathname', allow_duplicate=True),
        Output('app-container', 'children', allow_duplicate=True),
        Output('session-mode', 'data', allow_duplicate=True),
        Output('btn-real-model', 'n_clicks'),
        Output('redirect-interval', 'disabled', allow_duplicate=True),
    ],
    [
        Input("btn-real-model", "n_clicks"),
        Input("confirm-ip-btn", "n_clicks"),
        Input("cancel-ip-btn", "n_clicks"),
    ],
    [
        State("ip-modal", "is_open"),
        State("input-ip", "value"),
    ],
    prevent_initial_call=True
)
def handle_modal(btn_real_click, confirm_click, cancel_click, is_open, ip_value):
    ctx = callback_context
    if not ctx.triggered:
        logger.debug("handle_modal: No trigger detected, preventing update")
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    logger.debug(f"handle_modal triggered by {button_id}, btn_real_click={btn_real_click}, confirm_click={confirm_click}, cancel_click={cancel_click}, is_open={is_open}, ip_value={ip_value}")

    if button_id == "btn-real-model" and btn_real_click:
        logger.debug("btn-real-model clicked, opening modal")
        return True, dash.no_update, dash.no_update, dash.no_update, dash.no_update, 0, dash.no_update

    elif button_id == "cancel-ip-btn" and cancel_click:
        logger.debug("cancel-ip-btn clicked, closing modal")
        return False, dash.no_update, dash.no_update, dash.no_update, dash.no_update, 0, dash.no_update

    elif button_id == "confirm-ip-btn" and confirm_click:
        logger.debug(f"confirm-ip-btn clicked with ip_value: {ip_value}")
        if ip_value:
            try:
                # Save IP address to database_json/ip_address.json
                ip_json_path = os.path.join("database_json", "ip_address.json")
                ip_data = {"ip_address": ip_value}
                os.makedirs(os.path.dirname(ip_json_path), exist_ok=True)
                with open(ip_json_path, 'w', encoding='utf-8') as f:
                    json.dump(ip_data, f, indent=2)
                logger.info(f"Saved IP address {ip_value} to {ip_json_path}")

                # Execute ROS commands
                cmd1 = f"roslaunch mir_driver mir.launch mir_hostname:={ip_value}"
                subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'{cmd1}; exec bash'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(5)
                cmd2 = "rosrun tf tf_monitor"
                subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'{cmd2}; exec bash'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # Save simulation state
                state_manager.save_simulation_state(mode="real", running=True)
                sidebar = Sidebar()
                status_bar = StatusBar()
                new_layout = html.Div(
                    [
                        dcc.Location(id='url', refresh=False),
                        status_bar.create_status_bar(),
                        sidebar.create_sidebar(),
                        html.Div(id="page-content", style={"marginLeft": "250px"}),
                        dcc.Store(id='dummy-output'),
                        dcc.Store(id='session-mode', storage_type='session'),
                    ],
                    style={"background": "#BDC3C7", "height": "100vh", "overflow": "hidden"},
                )

                logger.debug("Real model commands executed, redirecting to /")
                return False, ip_value, "/", new_layout, "real", 0, True
            except Exception as e:
                logger.error(f"Error during real model commands or IP saving: {e}")
                return True, dash.no_update, dash.no_update, dash.no_update, dash.no_update, 0, dash.no_update
        else:
            logger.debug("No IP provided, keeping modal open")
            return True, dash.no_update, dash.no_update, dash.no_update, dash.no_update, 0, dash.no_update

    logger.debug("No valid trigger, returning no update")
    return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update, 0, dash.no_update

@callback(
    [
        Output('app-container', 'children', allow_duplicate=True),
        Output('url', 'pathname', allow_duplicate=True),
    ],
    Input('url', 'pathname'),
    prevent_initial_call='initial_duplicate'
)
def check_simulation_status_on_load(pathname):
    """Kiểm tra trạng thái simulation khi load trang"""
    logger.debug(f"Checking simulation status for pathname: {pathname}")
    
    # Normalize pathname
    pathname = pathname or '/'
    
    # If no simulation is running, redirect to /options
    if not state_manager.should_redirect_to_home():
        logger.info("No simulation running, redirecting to /options")
        from page_options.layout import get_layout
        return get_layout(), "/options"
    
    # If simulation is running, create home layout for '/' or keep current page
    from components import Sidebar, StatusBar
    sidebar = Sidebar()
    status_bar = StatusBar()
    new_layout = html.Div(
        [
            dcc.Location(id='url', refresh=False),
            status_bar.create_status_bar(),
            sidebar.create_sidebar(),
            html.Div(id="page-content", style={"marginLeft": "250px"}),
        ],
        style={"background": "#BDC3C7", "height": "100vh", "overflow": "hidden"},
    )
    
    # If pathname is /options but simulation is running, redirect to /
    if pathname == '/options':
        logger.info("Simulation is running, redirecting from /options to /")
        return new_layout, "/"
    
    # For other pages, keep the current pathname
    logger.info(f"Simulation running, staying on {pathname}")
    return new_layout, pathname