from dash import html, dcc, callback, Input, Output, State, no_update, Dash
import dash_bootstrap_components as dbc
import rospy, dash, io, base64, json, os, math, threading
from geometry_msgs.msg import PoseStamped, Twist, PoseWithCovarianceStamped
import numpy as np
from PIL import Image
import plotly.express as px
from utils_function.move_along_path_line import *
from mpc_controller import LineMPCController, Spline3_MPCController, Spline5_MPCController, Arc_MPCController
from components import button_primary_style, button_style
import os
import json
import subprocess
import rospy
from actionlib_msgs.msg import GoalID
from dash.exceptions import PreventUpdate

is_moving = True
arc_controller = Arc_MPCController(dt=0.1, v_max=1.0, v_min=-1.0, omega_max=1.5, omega_min=-1.5, lookahead_distance=0.2)
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

class RVizSection:
    FIXED_ARROW_LENGTH = 30

    def __init__(self, goal_topic="/move_base_simple/goal", twist_topic="/cmd_vel", pose_topic="/amcl_pose"):
        self.goal_topic = goal_topic
        self.twist_topic = twist_topic
        self.pose_topic = pose_topic
        try:
            self.goal_pub = rospy.Publisher(self.goal_topic, PoseStamped, queue_size=10)
            self.twist_pub = rospy.Publisher(self.twist_topic, Twist, queue_size=10)
            self.current_pose = None
            self.pose_sub = rospy.Subscriber(self.pose_topic, PoseWithCovarianceStamped, self.pose_callback)
        except rospy.exceptions.ROSException as e:
            print(f"Error connecting to ROS: {e}")
            self.goal_pub = None
            self.twist_pub = None
        self.map_data = self.load_image_as_numpy("static/map_image.png")
        rospy.Subscriber("/amcl_pose", PoseWithCovarianceStamped, self.pose_callback)

    def pose_callback(self, msg):
        self.current_pose = msg.pose.pose

    def get_robot_position(self):
        if self.current_pose is None:
            return None, None, None
        
        pos = self.current_pose.position
        ori = self.current_pose.orientation

        _, _, yaw = tf.transformations.euler_from_quaternion([
            ori.x, ori.y, ori.z, ori.w
        ])
        return pos.x, pos.y, yaw

    def load_image_as_numpy(self, image_path):
        try:
            img = Image.open(image_path).convert('L')
            map_data = np.array(img)
            if len(map_data.shape) > 2:
                print("WARNING: Image has more than two dimensions, potential color issue")
            return map_data
        except FileNotFoundError:
            print(f"Error: Image file not found at {image_path}")
            return self.generate_fake_map()

    def generate_fake_map(self):
        size = 500
        return np.random.randint(0, 255, size=(size, size))

    def create_composite_image(self):
        map_path = "static/map_image.png"
        if not os.path.exists(map_path):
            print(f"[ERROR] Không tìm thấy ảnh bản đồ tại: {map_path}")
            width, height = 400, 400 
        else:
            map_img = Image.open(map_path)
            width, height = map_img.size  
        final_img = Image.new("RGBA", (width, height), (255, 255, 255, 0)) 
        return final_img

    def create_figure(self, drawing_enabled=False, start_x=None, start_y=None, end_x=None, end_y=None):
        composite_img = self.create_composite_image()
        if composite_img is None:
            fake_map = self.generate_fake_map()
            fig = px.imshow(fake_map, color_continuous_scale='gray')
        else:
            img_byte_arr = io.BytesIO()
            composite_img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            encoded_image = base64.b64encode(img_byte_arr).decode()
            img_data = f'data:image/png;base64,{encoded_image}'
            fig = px.imshow(Image.open(io.BytesIO(base64.b64decode(encoded_image))), binary_string=True)
            fig.update_layout(
                images=[dict(
                    source=img_data,
                    xref="x", yref="y",
                    x=0, y=composite_img.size[1],
                    sizex=composite_img.size[0], sizey=composite_img.size[1],
                    sizing="stretch",
                    opacity=1,
                    layer="below")],
                plot_bgcolor='rgba(255,255,255,0)',
                paper_bgcolor='rgba(255,255,255,0)'
            )

        dragmode = "drawline" if drawing_enabled else False
        fig.update_layout(
            dragmode=dragmode,
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False, scaleratio=1),
            margin=dict(l=0, r=0, b=0, t=0),
            height=600,
            width=800,
            newshape_line_color='red',
            coloraxis_showscale=False
        )
        fig.update_traces(
            hovertemplate=None,
            hoverinfo='skip'
        )

        if start_x is not None and start_y is not None and end_x is not None and end_y is not None:
            dx = end_x - start_x
            dy = end_y - start_y
            angle = math.atan2(dy, dx)
            fixed_end_x = start_x + self.FIXED_ARROW_LENGTH * math.cos(angle)
            fixed_end_y = start_y + self.FIXED_ARROW_LENGTH * math.sin(angle)
            fig.add_annotation(
                x=fixed_end_x, y=fixed_end_y, ax=start_x, ay=start_y,
                xref="x", yref="y", axref="x", ayref="y",
                arrowhead=2, arrowcolor='red', arrowwidth=2,
            )
        return fig

    def publish_goal(self, x, y, angle):
        if self.goal_pub:
            try:
                pose = PoseStamped()
                pose.header.stamp = rospy.Time.now()
                pose.header.frame_id = "map"
                pose.pose.position.x = float(x)
                pose.pose.position.y = float(y)
                pose.pose.orientation.z = math.sin(angle / 2)
                pose.pose.orientation.w = math.cos(angle / 2)
                self.goal_pub.publish(pose)
                return "Goal published successfully! (x: {}, y: {}, angle: {})".format(x, y, angle)
            except Exception as e:
                return f"Error publishing goal: {e}"
        return "Goal publisher not initialized."

    def publish_twist(self, linear_x=0.0, angular_z=0.0):
        if self.twist_pub:
            try:
                twist = Twist()
                twist.linear.x = float(linear_x)
                twist.angular.z = float(angular_z)
                self.twist_pub.publish(twist)
                return f"Twist published: linear_x={linear_x}, angular_z={angular_z}"
            except Exception as e:
                return f"Error publishing twist: {e}"
        return "Twist publisher not initialized."

    def stop_robot(self):
        return self.publish_twist(0.0, 0.0)

    def is_at_position(self, target_x, target_y, tolerance=0.2):
        if self.current_pose is None:
            return False
        current_x = self.current_pose.position.x
        current_y = self.current_pose.position.y
        distance = math.sqrt((current_x - target_x)**2 + (current_y - target_y)**2)
        return distance < tolerance

def create_rviz_section():
    # Default button style for normal state
    default_button_style = {
        **button_primary_style,
        "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
        "color": "white",
        "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
        "borderRadius": "8px",
        "padding": "10px 20px",
        "border": "none",
        "cursor": "pointer",
        "fontFamily": "Arial, sans-serif",
        "fontWeight": "600",
        "fontSize": "14px",
        "width": "160px",
        "height": "40px",
        "textAlign": "center",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
    }
    
    # Active button style (only changes color)
    active_button_style = {
        **default_button_style,
        "background": "linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)",
    }
    
    # Emergency stop button style (same dimensions as others)
    emergency_stop_style = {
        **button_style,
        "background": "linear-gradient(135deg, #DC3545 0%, #c82333 100%)",
        "color": "white",
        "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
        "borderRadius": "8px",
        "padding": "10px 20px",
        "border": "none",
        "cursor": "pointer",
        "fontFamily": "Arial, sans-serif",
        "fontWeight": "600",
        "fontSize": "14px",
        "width": "160px",
        "height": "40px",
        "textAlign": "center",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
    }
    
    # Emergency stopped style (only changes color)
    emergency_stopped_style = {
        **emergency_stop_style,
        "background": "linear-gradient(135deg, #6C757D 0%, #5a6268 100%)",
    }
    
    layout = html.Div(
        style={
            'backgroundColor': '#FFFFFF',
            'height': '100vh',
            'fontFamily': 'Arial, sans-serif',
            'boxShadow': '0 4px 12px rgba(0,0,0,0.15)',
        },
        children=[
            html.Div(
                className="control-panel",
                style={
                    "padding": "20px",
                    "margin": "20px auto",
                    "maxWidth": "1200px",
                    "background": "linear-gradient(135deg, #FFFFFF 0%, #F5F7FA 100%)",
                    "borderRadius": "10px",
                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                },
                children=[
                    html.H3(
                        [
                            html.I(className="fas fa-robot", style={"marginRight": "10px"}),
                            "RVIZ INTERFACE"
                        ],
                        className="mb-3",
                        style={
                            "color": "#2C3E50",
                            "fontWeight": "bold",
                            "fontSize": "24px",
                            "padding": "10px 0",
                            "textAlign": "center",
                        }
                    ),
                    html.Div(
                        style={
                            "display": "flex",
                            "gap": "12px",
                            "flexWrap": "wrap",
                            "justifyContent": "center",
                            "marginBottom": "20px",
                            "padding": "15px",
                            "background": "linear-gradient(135deg, #f9f9f9 0%, #e9ecef 100%)",
                            "borderRadius": "10px",
                            "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
                        },
                        children=[
                            html.Button(
                                [
                                    html.I(className="fas fa-bullseye", style={"marginRight": "8px"}),
                                    "Send Goal"
                                ],
                                id="send-goal-btn",
                                className="enhanced-button",
                                style=default_button_style,
                                n_clicks=0,
                            ),
                            html.Button(
                                [
                                    html.I(className="fas fa-crosshairs", style={"marginRight": "8px"}),
                                    "2D Nav Goal"
                                ],
                                id="nav-goal-btn",
                                className="enhanced-button",
                                style=default_button_style,
                                n_clicks=0,
                            ),
                            html.Button(
                                [
                                    html.I(className="fas fa-route", style={"marginRight": "8px"}),
                                    "Move Line"
                                ],
                                id="move-line-btn",
                                className="enhanced-button",
                                style=default_button_style,
                                n_clicks=0,
                            ),
                            html.Button(
                                [
                                    html.I(className="fas fa-circle-notch", style={"marginRight": "8px"}),
                                    "Move Arc"
                                ],
                                id="move-arc-btn",
                                className="enhanced-button",
                                style=default_button_style,
                                n_clicks=0,
                            ),
                            html.Button(
                                [
                                    html.I(className="fas fa-road", style={"marginRight": "8px"}),
                                    "Move Path"
                                ],
                                id="move-path-btn",
                                className="enhanced-button",
                                style=default_button_style,
                                n_clicks=0,
                            ),
                            html.Button(
                                [
                                    html.I(className="fas fa-wave-square", style={"marginRight": "8px"}),
                                    "Move Spline 3"
                                ],
                                id="move-spline3-btn",
                                className="enhanced-button",
                                style=default_button_style,
                                n_clicks=0,
                            ),
                            html.Button(
                                [
                                    html.I(className="fas fa-bezier-curve", style={"marginRight": "8px"}),
                                    "Move Spline 5"
                                ],
                                id="move-spline5-btn",
                                className="enhanced-button",
                                style=default_button_style,
                                n_clicks=0,
                            ),
                            html.Button(
                                [
                                    html.I(className="fas fa-stop", style={"marginRight": "8px"}),
                                    "Emergency Stop"
                                ],
                                id="emergency-stop-btn",
                                className="enhanced-button",
                                style=emergency_stop_style,
                                n_clicks=0,
                            ),
                        ]
                    ),
                    html.Div(
                        className="map-container",
                        style={
                            "position": "relative",
                            "width": "800px",
                            "height": "600px",
                            "margin": "0 auto 20px",
                            "borderRadius": "10px",
                            "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                        },
                        children=[
                            dcc.Graph(
                                id="map-graph",
                                figure=RVizSection().create_figure(),
                                style={
                                    "width": "800px",
                                    "height": "600px",
                                    "background": "rgba(0, 0, 0, 0)",
                                    "position": "absolute",
                                    "zIndex": "9",
                                    "top": "0",
                                    "left": "0",
                                    "border": "5px solid #34495E",
                                    "borderRadius": "10px",
                                },
                                config={'scrollZoom': False, 'displayModeBar': False}
                            ),
                            html.Img(
                                id="map-image",
                                src="/static/map_image.png",
                                style={
                                    "width": "800px",
                                    "height": "600px",
                                    "border": "5px solid #34495E",
                                    "borderRadius": "10px",
                                    "objectFit": "contain",
                                    "position": "absolute",
                                    "zIndex": "1",
                                    "top": "0",
                                    "left": "0",
                                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                },
                            ),
                            html.Img(
                                id="lidar-f-image",
                                src="/static/f_scan_image.png",
                                style={
                                    "width": "800px",
                                    "height": "600px",
                                    "border": "5px solid #34495E",
                                    "borderRadius": "10px",
                                    "objectFit": "contain",
                                    "position": "absolute",
                                    "zIndex": "2",
                                    "top": "0",
                                    "left": "0",
                                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                },
                            ),
                            html.Img(
                                id="lidar-b-image",
                                src="/static/lidar_b_image.png",
                                style={
                                    "width": "800px",
                                    "height": "600px",
                                    "border": "5px solid #34495E",
                                    "borderRadius": "10px",
                                    "objectFit": "contain",
                                    "position": "absolute",
                                    "zIndex": "3",
                                    "top": "0",
                                    "left": "0",
                                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                },
                            ),
                            html.Img(
                                id="path-image",
                                src="/static/path_image.png",
                                style={
                                    "width": "800px",
                                    "height": "600px",
                                    "border": "5px solid #34495E",
                                    "borderRadius": "10px",
                                    "objectFit": "contain",
                                    "position": "absolute",
                                    "zIndex": "4",
                                    "top": "0",
                                    "left": "0",
                                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                },
                            ),
                            html.Img(
                                id="robot-image",
                                src="/static/robot_image.png",
                                style={
                                    "width": "800px",
                                    "height": "600px",
                                    "border": "5px solid #34495E",
                                    "borderRadius": "10px",
                                    "objectFit": "contain",
                                    "position": "absolute",
                                    "zIndex": "5",
                                    "top": "0",
                                    "left": "0",
                                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                },
                            ),
                            html.Img(
                                id="paths-image",
                                src="/static/path_img.png",
                                style={
                                    "width": "800px",
                                    "height": "600px",
                                    "border": "5px solid #34495E",
                                    "borderRadius": "10px",
                                    "objectFit": "contain",
                                    "position": "absolute",
                                    "zIndex": "6",
                                    "top": "0",
                                    "left": "0",
                                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                },
                            ),
                            html.Img(
                                id="costmap-image",
                                src="/static/cost_map_image.png",
                                style={
                                    "width": "800px",
                                    "height": "600px",
                                    "border": "5px solid #34495E",
                                    "borderRadius": "10px",
                                    "objectFit": "contain",
                                    "position": "absolute",
                                    "zIndex": "7",
                                    "top": "0",
                                    "left": "0",
                                    "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                },
                            ),
                        ]
                    ),
                    html.Div(
                        style={
                            "background": "linear-gradient(135deg, #f9f9f9 0%, #e9ecef 100%)",
                            "padding": "15px",
                            "borderRadius": "10px",
                            "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
                            "marginBottom": "20px",
                            "textAlign": "center",
                        },
                        children=[
                            html.P(
                                [
                                    html.I(className="fas fa-info-circle", style={"marginRight": "8px"}),
                                    "Draw line and after release, it sends the goal"
                                ],
                                className="text-info mt-2",
                                style={
                                    "fontStyle": "italic",
                                    "fontSize": "14px",
                                    "color": "#17A2B8",
                                    "fontFamily": "Arial, sans-serif",
                                }
                            ),
                            html.Div(
                                id="goal-status",
                                style={
                                    "fontSize": "14px",
                                    "color": "#333",
                                    "fontFamily": "Arial, sans-serif",
                                    "marginTop": "10px",
                                }
                            ),
                        ]
                    ),
                    dcc.Interval(
                        id='interval-component',
                        interval=1 * 1000,
                        n_intervals=0
                    ),
                    dcc.Interval(
                        id='move-line-interval',
                        interval=1 * 1000,
                        disabled=True
                    ),
                    dcc.Interval(
                        id='move-spline-interval',
                        interval=1 * 1000,
                        disabled=True
                    ),
                    dcc.Store(id="drag-start-coords", data=None),
                    dcc.Store(id="drawing-enabled", data=False),
                    dcc.Store(id="latest-goal", data=None),
                    dcc.Store(id="move-line-data", data=None),
                    dcc.Store(id="path-line-data", data=[]),
                    dcc.Store(id="spline3-coordinates", data=[]),
                    dcc.Store(id="spline5-coordinates", data=[]),
                    dcc.Store(id="current-line-index", data=0),
                    dcc.Store(id="button-style-store", data={
                        "nav_goal_button": default_button_style,
                        "active_nav_goal_button": active_button_style
                    }),
                    dcc.Store(id="emergency-stop-state", data={
                        "is_stopped": False,
                        "style": emergency_stop_style
                    }),
                    dbc.Modal(
                        [
                            dbc.ModalHeader(
                                dbc.ModalTitle(
                                    [
                                        html.I(className="fas fa-crosshairs", style={"marginRight": "8px"}),
                                        "Enter Goal Coordinates"
                                    ],
                                    style={"fontSize": "16px", "fontWeight": "600"}
                                ),
                                style={
                                    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
                                    "color": "white",
                                    "borderRadius": "10px 10px 0 0",
                                }
                            ),
                            dbc.ModalBody(
                                dbc.Form(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(dbc.Label("X:", html_for="goal-x", style={"fontSize": "14px", "fontWeight": "600"})),
                                                dbc.Col(dbc.Input(
                                                    type="number",
                                                    id="goal-x",
                                                    placeholder="X Coordinate",
                                                    style={"fontSize": "14px", "borderRadius": "8px"}
                                                )),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(dbc.Label("Y:", html_for="goal-y", style={"fontSize": "14px", "fontWeight": "600"})),
                                                dbc.Col(dbc.Input(
                                                    type="number",
                                                    id="goal-y",
                                                    placeholder="Y Coordinate",
                                                    style={"fontSize": "14px", "borderRadius": "8px"}
                                                )),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(dbc.Label("Z:", html_for="goal-z", style={"fontSize": "14px", "fontWeight": "600"})),
                                                dbc.Col(dbc.Input(
                                                    type="number",
                                                    id="goal-z",
                                                    placeholder="Z Coordinate",
                                                    value=0,
                                                    style={"fontSize": "14px", "borderRadius": "8px"}
                                                )),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(dbc.Label("W:", html_for="goal-w", style={"fontSize": "14px", "fontWeight": "600"})),
                                                dbc.Col(dbc.Input(
                                                    type="number",
                                                    id="goal-w",
                                                    placeholder="W Orientation",
                                                    value=1,
                                                    style={"fontSize": "14px", "borderRadius": "8px"}
                                                )),
                                            ],
                                            className="mb-3",
                                        ),
                                    ]
                                ),
                                style={"background": "rgba(248, 249, 250, 0.8)", "padding": "20px"}
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button(
                                        "Close",
                                        id="close-goal-modal",
                                        className="ms-auto",
                                        style={**button_style, "borderRadius": "8px"}
                                    ),
                                    dbc.Button(
                                        "Send",
                                        id="send-goal-modal-btn",
                                        color="primary",
                                        className="ms-2",
                                        style={**button_style, "borderRadius": "8px"}
                                    ),
                                ]
                            ),
                        ],
                        id="goal-modal",
                        is_open=False,
                        style={"borderRadius": "10px"}
                    ),
                    dbc.Modal(
                        [
                            dbc.ModalHeader(
                                dbc.ModalTitle(
                                    [
                                        html.I(className="fas fa-tachometer-alt", style={"marginRight": "8px"}),
                                        "Set Movement Speed"
                                    ],
                                    style={"fontSize": "16px", "fontWeight": "600"}
                                ),
                                style={
                                    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
                                    "color": "white",
                                    "borderRadius": "10px 10px 0 0",
                                }
                            ),
                            dbc.ModalBody(
                                dbc.Form(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(dbc.Label("Linear Speed (m/s):", html_for="linear-speed", style={"fontSize": "14px", "fontWeight": "600"})),
                                                dbc.Col(dbc.Input(
                                                    type="number",
                                                    id="linear-speed",
                                                    placeholder="Enter speed",
                                                    value=0.2,
                                                    step=0.1,
                                                    style={"fontSize": "14px", "borderRadius": "8px"}
                                                )),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(dbc.Label("Angular Speed (rad/s):", html_for="angular-speed", style={"fontSize": "14px", "fontWeight": "600"})),
                                                dbc.Col(dbc.Input(
                                                    type="number",
                                                    id="angular-speed",
                                                    placeholder="Enter angular speed",
                                                    value=0.5,
                                                    step=0.1,
                                                    style={"fontSize": "14px", "borderRadius": "8px"}
                                                )),
                                            ],
                                            className="mb-3",
                                        ),
                                    ]
                                ),
                                style={"background": "rgba(248, 249, 250, 0.8)", "padding": "20px"}
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button(
                                        "Cancel",
                                        id="cancel-line-modal",
                                        className="ms-auto",
                                        style={**button_style, "borderRadius": "8px"}
                                    ),
                                    dbc.Button(
                                        "Start",
                                        id="start-line-modal-btn",
                                        color="primary",
                                        className="ms-2",
                                        style={**button_style, "borderRadius": "8px"}
                                    ),
                                ]
                            ),
                        ],
                        id="line-modal",
                        is_open=False,
                        style={"borderRadius": "10px"}
                    ),
                    dbc.Modal(
                        [
                            dbc.ModalHeader(
                                dbc.ModalTitle(
                                    [
                                        html.I(className="fas fa-bezier-curve", style={"marginRight": "8px"}),
                                        "Move Along Spline"
                                    ],
                                    style={"fontSize": "16px", "fontWeight": "600"}
                                ),
                                style={
                                    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
                                    "color": "white",
                                    "borderRadius": "10px 10px 0 0",
                                }
                            ),
                            dbc.ModalBody(
                                "Do you want to start moving along the spline?",
                                style={
                                    "background": "rgba(248, 249, 250, 0.8)",
                                    "fontSize": "14px",
                                    "textAlign": "center",
                                    "padding": "20px",
                                    "color": "#333"
                                }
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button(
                                        "Cancel",
                                        id="cancel-spline-modal",
                                        className="ms-auto",
                                        style={**button_style, "borderRadius": "8px"}
                                    ),
                                    dbc.Button(
                                        "Start",
                                        id="start-spline-modal-btn",
                                        color="primary",
                                        className="ms-2",
                                        style={**button_style, "borderRadius": "8px"}
                                    ),
                                ]
                            ),
                        ],
                        id="spline-modal",
                        is_open=False,
                        style={"borderRadius": "10px"}
                    ),
                    dbc.Modal(
                        [
                            dbc.ModalHeader(
                                dbc.ModalTitle(
                                    [
                                        html.I(className="fas fa-wave-square", style={"marginRight": "8px"}),
                                        "Move Along Spline 5"
                                    ],
                                    style={"fontSize": "16px", "fontWeight": "600"}
                                ),
                                style={
                                    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
                                    "color": "white",
                                    "borderRadius": "10px 10px 0 0",
                                }
                            ),
                            dbc.ModalBody(
                                "Do you want to start moving along the spline 5?",
                                style={
                                    "background": "rgba(248, 249, 250, 0.8)",
                                    "fontSize": "14px",
                                    "textAlign": "center",
                                    "padding": "20px",
                                    "color": "#333"
                                }
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button(
                                        "Cancel",
                                        id="cancel-spline5-modal",
                                        className="ms-auto",
                                        style={**button_style, "borderRadius": "8px"}
                                    ),
                                    dbc.Button(
                                        "Start",
                                        id="start-spline5-modal-btn",
                                        color="primary",
                                        className="ms-2",
                                        style={**button_style, "borderRadius": "8px"}
                                    ),
                                ]
                            ),
                        ],
                        id="spline5-modal",
                        is_open=False,
                        style={"borderRadius": "10px"}
                    ),
                    dbc.Modal(
                        [
                            dbc.ModalHeader(
                                dbc.ModalTitle(
                                    [
                                        html.I(className="fas fa-road", style={"marginRight": "8px"}),
                                        "Move Along Full Path"
                                    ],
                                    style={"fontSize": "16px", "fontWeight": "600"}
                                ),
                                style={
                                    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
                                    "color": "white",
                                    "borderRadius": "10px 10px 0 0",
                                }
                            ),
                            dbc.ModalBody(
                                "Do you want to start moving along the full path?",
                                style={
                                    "background": "rgba(248, 249, 250, 0.8)",
                                    "fontSize": "14px",
                                    "textAlign": "center",
                                    "padding": "20px",
                                    "color": "#333"
                                }
                            ),
                            dbc.ModalFooter([
                                dbc.Button(
                                    "Cancel",
                                    id="cancel-path-modal",
                                    className="ms-auto",
                                    style={**button_style, "borderRadius": "8px"}
                                ),
                                dbc.Button(
                                    "Start",
                                    id="start-path-modal-btn",
                                    color="primary",
                                    className="ms-2",
                                    style={**button_style, "borderRadius": "8px"}
                                ),
                            ]),
                        ],
                        id="path-modal",
                        is_open=False,
                        style={"borderRadius": "10px"}
                    ),
                    dbc.Modal(
                        [
                            dbc.ModalHeader(
                                dbc.ModalTitle(
                                    [
                                        html.I(className="fas fa-circle-notch", style={"marginRight": "8px"}),
                                        "Move Along Arc"
                                    ],
                                    style={"fontSize": "16px", "fontWeight": "600"}
                                ),
                                style={
                                    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
                                    "color": "white",
                                    "borderRadius": "10px 10px 0 0",
                                }
                            ),
                            dbc.ModalBody(
                                "Do you want to start moving along the arc?",
                                style={
                                    "background": "rgba(248, 249, 250, 0.8)",
                                    "fontSize": "14px",
                                    "textAlign": "center",
                                    "padding": "20px",
                                    "color": "#333"
                                }
                            ),
                            dbc.ModalFooter([
                                dbc.Button(
                                    "Cancel",
                                    id="cancel-arc-modal",
                                    className="ms-auto",
                                    style={**button_style, "borderRadius": "8px"}
                                ),
                                dbc.Button(
                                    "Start",
                                    id="start-arc-modal-btn",
                                    color="primary",
                                    className="ms-2",
                                    style={**button_style, "borderRadius": "8px"}
                                ),
                            ]),
                        ],
                        id="arc-modal",
                        is_open=False,
                        style={"borderRadius": "10px"}
                    ),
                ]
            )
        ]
    )
    return layout

def load_map_info():
    map_info_path = "static/map_image.json"
    if os.path.exists(map_info_path):
        with open(map_info_path, "r") as f:
            return json.load(f)
    else:
        print("WARNING: map_info.json not found. Using default values or disabling auto-goal sending.")
        return None

# Callbacks
@callback(
    Output("goal-modal", "is_open"),
    [Input("send-goal-btn", "n_clicks"), Input("close-goal-modal", "n_clicks"), Input("send-goal-modal-btn", "n_clicks")],
    [State("goal-modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_modal(n1, n2, n3, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "send-goal-btn":
        return True
    elif button_id == "close-goal-modal" or button_id == "send-goal-modal-btn":
        return False
    return is_open

@callback(
    Output("goal-status", "children"),
    [Input("send-goal-modal-btn", "n_clicks")],
    [
        State("goal-x", "value"),
        State("goal-y", "value"),
        State("goal-z", "value"),
        State("goal-w", "value"),
    ],
    prevent_initial_call=True,
)
def send_goal_coordinates(n_clicks, x, y, z, w):
    if n_clicks:
        rviz_section = RVizSection()
        angle = math.atan2(z, w)
        status = rviz_section.publish_goal(x, y, angle)
        return status
    return no_update

@callback(
    Output("map-graph", "figure"),
    [Input("map-graph", "clickData"), Input("map-graph", "relayoutData"), Input("interval-component", "n_intervals")],
    [State("map-graph", "figure"), State("drag-start-coords", "data"), State("drawing-enabled", "data")],
    prevent_initial_call=True,
)
def update_map(clickData, relayoutData, n_intervals, existing_map, drag_start_coords, drawing_enabled):
    ctx = dash.callback_context
    rviz_section = RVizSection()
    if not ctx.triggered:
        return existing_map
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == "map-graph" and clickData and drawing_enabled:
        start_x = clickData['points'][0]['x']
        start_y = clickData['points'][0]['y']
        return rviz_section.create_figure(drawing_enabled, start_x=start_x, start_y=start_y, end_x=start_x, end_y=start_y)

    elif trigger_id == "map-graph" and relayoutData and drag_start_coords and drawing_enabled:
        start_x = drag_start_coords["start_x"]
        start_y = drag_start_coords["start_y"]
        end_x = relayoutData.get("xaxis.range[0]")
        end_y = relayoutData.get("yaxis.range[1]")
        return rviz_section.create_figure(drawing_enabled, start_x=start_x, start_y=start_y, end_x=end_x, end_y=end_y)

    elif trigger_id == "interval-component":
        return rviz_section.create_figure(drawing_enabled)

    return existing_map

@callback(
    Output("drag-start-coords", "data"),
    [Input("map-graph", "clickData")],
    [State("drawing-enabled", "data")],
    prevent_initial_call=True
)
def store_drag_start_coords(clickData, drawing_enabled):
    if clickData and drawing_enabled:
        return {"start_x": clickData['points'][0]['x'], "start_y": clickData['points'][0]['y']}
    return no_update

@callback(
    [Output("drawing-enabled", "data"), Output("nav-goal-btn", "style")],
    [Input("nav-goal-btn", "n_clicks")],
    [State("drawing-enabled", "data"), State("button-style-store", "data")],
    prevent_initial_call=True
)
def toggle_drawing_mode(n_clicks, drawing_enabled, button_style_store):
    if n_clicks is None:
        return no_update, no_update

    new_drawing_enabled = not drawing_enabled
    nav_goal_style = button_style_store["active_nav_goal_button"] if new_drawing_enabled else button_style_store["nav_goal_button"]

    return new_drawing_enabled, nav_goal_style

@callback(
    [Output("goal-status", "children", allow_duplicate=True),
     Output("drawing-enabled", "data", allow_duplicate=True),
     Output("nav-goal-btn", "style", allow_duplicate=True)],
    Input("map-graph", "relayoutData"),
    [State("drag-start-coords", "data"), State("drawing-enabled", "data"), State("button-style-store", "data")],
    prevent_initial_call=True
)
def auto_send_goal(relayoutData, drag_start_coords, drawing_enabled, button_style_store):
    if not (relayoutData and drawing_enabled):
        print("Không thỏa mãn điều kiện gửi goal")
        return no_update, no_update, no_update

    map_info = load_map_info()

    if not map_info:
        print("Không thể tải thông tin bản đồ từ map_info.json. Không tự động gửi goal.")
        return "Không thể gửi goal tự động do thiếu thông tin bản đồ.", no_update, no_update

    if "shapes" not in relayoutData or not relayoutData["shapes"]:
        print("relayoutData không có shapes hợp lệ!")
        return no_update, no_update, no_update

    shape = relayoutData["shapes"][0]
    x_pixel_start, y_pixel_start = shape["x0"], shape["y0"]
    x_pixel_end, y_pixel_end = shape["x1"], shape["y1"]

    start_x = map_info["origin_x"] + (x_pixel_start * map_info["resolution"])
    start_y = map_info["origin_y"] + ((map_info["height"] - y_pixel_start) * map_info["resolution"])
    end_x = map_info["origin_x"] + (x_pixel_end * map_info["resolution"])
    end_y = map_info["origin_y"] + ((map_info["height"] - y_pixel_end) * map_info["resolution"])

    dx = end_x - start_x
    dy = end_y - start_y
    angle = math.atan2(dy, dx)

    rviz_section = RVizSection()
    status = rviz_section.publish_goal(start_x, start_y, angle)

    new_drawing_enabled = False
    nav_goal_style = button_style_store["nav_goal_button"]

    return status, new_drawing_enabled, nav_goal_style

@callback(
    Output("line-modal", "is_open"),
    [Input("move-line-btn", "n_clicks"), Input("cancel-line-modal", "n_clicks"), Input("start-line-modal-btn", "n_clicks")],
    [State("line-modal", "is_open")],
    prevent_initial_call=True,
)
def toggle_line_modal(n1, n2, n3, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "move-line-btn":
        return True
    elif button_id in ["cancel-line-modal", "start-line-modal-btn"]:
        return False
    return is_open

@callback(
    [Output("goal-status", "children", allow_duplicate=True),
     Output("move-line-data", "data", allow_duplicate=True),
     Output("path-line-data", "data", allow_duplicate=True),
     Output("current-line-index", "data", allow_duplicate=True),
     Output("move-line-interval", "disabled", allow_duplicate=True)],
    Input("start-line-modal-btn", "n_clicks"),
    [State("linear-speed", "value"),
     State("angular-speed", "value")],
    prevent_initial_call=True,
)
def start_line_mpc(n_clicks, linear_speed, angular_speed):
    """Callback to start line_mpc_new.py when the button is clicked."""
    global is_moving, process

    if n_clicks is None:
        raise PreventUpdate

    # Stop any existing process if running
    if process is not None:
        is_moving = False
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
        process = None
        cancel_pub.publish(GoalID())
        print("📍 Sent cancel signal to /move_base/cancel")
        send_zero_velocity()

    # Validate speed inputs
    if linear_speed is None or angular_speed is None:
        return (
            "❌ Error: Linear or angular speed not provided.",
            no_update,
            no_update,
            no_update,
            no_update
        )

    try:
        linear_speed = float(linear_speed)
        angular_speed = float(angular_speed)
    except (ValueError, TypeError):
        return (
            "❌ Error: Invalid speed values. Please enter numeric values.",
            no_update,
            no_update,
            no_update,
            no_update
        )

    # Start the MPC script
    is_moving = True
    script_path = "mpc_controller/line_mpc_new.py"
    
    def run_script():
        global process
        try:
            # Pass speed values via environment variables
            env = {
                **os.environ,
                "MPC_LINEAR_SPEED": str(linear_speed),
                "MPC_ANGULAR_SPEED": str(angular_speed)
            }
            process = subprocess.Popen(
                ["python3", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            stdout, stderr = process.communicate()
            if stdout:
                print(f"[Line_MPC] Output: {stdout}")
            if stderr:
                print(f"[Line_MPC] Error: {stderr}")
        except Exception as e:
            print(f"[Line_MPC] Error running line_mpc_new.py: {e}")
        finally:
            is_moving = False
            process = None
            if not rospy.is_shutdown():
                cancel_pub.publish(GoalID())
                send_zero_velocity()

    threading.Thread(target=run_script, daemon=True).start()
    
    # Return values for all outputs
    return (
        f"🚀 Starting Line MPC with linear speed: {linear_speed} m/s, angular speed: {angular_speed} rad/s",
        None,  # move-line-data.data (not used in current logic, set to None)
        [],    # path-line-data.data (empty list, as per original)
        0,     # current-line-index.data (reset to 0, as per original)
        False  # move-line-interval.disabled (enable interval, as per original intent)
    )

@callback(
    Output("goal-status", "children", allow_duplicate=True),
    Input("start-spline-modal-btn", "n_clicks"),
    prevent_initial_call=True,
)
def start_spline3_mpc(n_clicks):
    """Callback to start spline5_mpc_new.py when the button is clicked."""
    global is_moving, process

    # Stop any existing process if running
    if process is not None:
        is_moving = False
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
        process = None
        cancel_pub.publish(GoalID())
        print("📍 Sent cancel signal to /move_base/cancel")
        send_zero_velocity()

    # Start the MPC script
    is_moving = True
    script_path = "mpc_controller/spline3_mpc_new.py"
    def run_script():
        global process
        try:
            process = subprocess.Popen(
                ["python3", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            if stdout:
                print(f"[Spline3_MPC] Output: {stdout}")
            if stderr:
                print(f"[Spline3_MPC] Error: {stderr}")
        except Exception as e:
            print(f"[Spline3_MPC] Error running spline3_mpc_new.py: {e}")
        finally:
            is_moving = False
            process = None
            if not rospy.is_shutdown():
                cancel_pub.publish(GoalID())
                send_zero_velocity()

    threading.Thread(target=run_script, daemon=True).start()
    return "🚀 Đang điều khiển spline3 bằng MPC..."

# Global variables
is_moving = False
process = None  # To track the subprocess running spline5_mpc_new.py
cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
cancel_pub = rospy.Publisher('/move_base/cancel', GoalID, queue_size=10)

def send_zero_velocity():
    """Helper function to publish zero velocity to /cmd_vel."""
    twist = Twist()
    twist.linear.x = 0.0
    twist.angular.z = 0.0
    cmd_vel_pub.publish(twist)
    print("🛑 Published cmd_vel = (0, 0) to stop robot.")

@callback(
    Output("goal-status", "children", allow_duplicate=True),
    Input("start-spline5-modal-btn", "n_clicks"),
    prevent_initial_call=True,
)
def start_spline5_mpc(n_clicks):
    """Callback to start spline5_mpc_new.py when the button is clicked."""
    global is_moving, process

    # Stop any existing process if running
    if process is not None:
        is_moving = False
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
        process = None
        cancel_pub.publish(GoalID())
        print("📍 Sent cancel signal to /move_base/cancel")
        send_zero_velocity()

    # Start the MPC script
    is_moving = True
    script_path = "mpc_controller/spline5_mpc_new.py"
    def run_script():
        global process
        try:
            process = subprocess.Popen(
                ["python3", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            if stdout:
                print(f"[Spline5_MPC] Output: {stdout}")
            if stderr:
                print(f"[Spline5_MPC] Error: {stderr}")
        except Exception as e:
            print(f"[Spline5_MPC] Error running spline5_mpc_new.py: {e}")
        finally:
            is_moving = False
            process = None
            if not rospy.is_shutdown():
                cancel_pub.publish(GoalID())
                send_zero_velocity()

    threading.Thread(target=run_script, daemon=True).start()
    return "🚀 Đang điều khiển spline5 bằng MPC..."

@callback(
    Output("spline-modal", "is_open"),
    [Input("move-spline3-btn", "n_clicks"),
     Input("cancel-spline-modal", "n_clicks"),
     Input("start-spline-modal-btn", "n_clicks")],
    [State("spline-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_spline_modal(n1, n2, n3, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == "move-spline3-btn":
        return True
    elif trigger in ["cancel-spline-modal", "start-spline-modal-btn"]:
        return False
    return is_open

@callback(
    Output("spline5-modal", "is_open"),
    [Input("move-spline5-btn", "n_clicks"),
     Input("cancel-spline5-modal", "n_clicks"),
     Input("start-spline5-modal-btn", "n_clicks")],
    [State("spline5-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_spline5_modal(n1, n2, n3, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == "move-spline5-btn":
        return True
    elif trigger in ["cancel-spline5-modal", "start-spline5-modal-btn"]:
        return False
    return is_open

@callback(
    Output("goal-status", "children", allow_duplicate=True),
    Input("start-path-modal-btn", "n_clicks"),
    prevent_initial_call=True,
)
def start_full_path_mpc(n_clicks):
    """Callback to start spline5_mpc_new.py when the button is clicked."""
    global is_moving, process

    # Stop any existing process if running
    if process is not None:
        is_moving = False
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
        process = None
        cancel_pub.publish(GoalID())
        print("📍 Sent cancel signal to /move_base/cancel")
        send_zero_velocity()

    # Start the MPC script
    is_moving = True
    script_path = "mpc_controller/single_mpc_controller/all_mpc.py"
    def run_script():
        global process
        try:
            process = subprocess.Popen(
                ["python3", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            if stdout:
                print(f"[Full_MPC] Output: {stdout}")
            if stderr:
                print(f"[Full_MPC] Error: {stderr}")
        except Exception as e:
            print(f"[Full_MPC] Error running line_mpc_new.py: {e}")
        finally:
            is_moving = False
            process = None
            if not rospy.is_shutdown():
                cancel_pub.publish(GoalID())
                send_zero_velocity()

    threading.Thread(target=run_script, daemon=True).start()
    return "🚀 Đang điều khiển line bằng MPC..."

@callback(
    Output("path-modal", "is_open"),
    [Input("move-path-btn", "n_clicks"),
     Input("cancel-path-modal", "n_clicks"),
     Input("start-path-modal-btn", "n_clicks")],
    [State("path-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_path_modal(n1, n2, n3, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == "move-path-btn":
        return True
    elif trigger in ["cancel-path-modal", "start-path-modal-btn"]:
        return False
    return is_open

def move_along_arc_thread():
    global is_moving
    try:
        file_path = "database_json/path_drawn.json"
        if not os.path.exists(file_path):
            print(f"[Arc] ❌ Không tìm thấy file: {file_path}")
            return

        with open(file_path, "r") as f:
            arc_data = json.load(f)

        if not arc_data:
            print("[Arc] ⚠️ File rỗng hoặc không có dữ liệu cung tròn")
            return

        for arc in arc_data:
            if arc["type"] != "arc":
                continue
            if not is_moving:
                print("[Arc] Dừng khẩn cấp được kích hoạt")
                send_velocity(0.0, 0.0)
                return

            start_x = arc["start_x"]
            start_y = arc["start_y"]
            center_x = arc["center_x"]
            center_y = arc["center_y"]
            radius = arc["radius"]
            start_angle = arc["start_angle"]
            end_angle = arc["end_angle"]
            rviz = RVizSection()
            arc_controller.waypoints_x = [start_x, start_x + 0.1, center_x]
            arc_controller.waypoints_y = [start_y, start_y + 0.1, center_y]
            arc_controller.circle_center = (center_x, center_y)
            arc_controller.circle_radius = radius
            arc_controller.arc_start_angle = start_angle
            arc_controller.arc_end_angle = end_angle
            arc_controller.start_time = rospy.Time.now().to_sec()
            while is_moving:
                x, y, theta = rviz.get_robot_position()
                if x is None:
                    continue
                # v, omega = line_controller.mpc_control(x, y, theta, start_x, start_y)
                send_velocity(v, omega)
                if np.hypot(x - start_x, y - start_y) < 0.1:
                    break
                rospy.sleep(0.1)
            print("[Arc] ✅ Đã đến điểm bắt đầu, bắt đầu bám cung tròn...")
            arc_controller.reached_goal = False
            while is_moving and not arc_controller.reached_goal:
                x, y, theta = rviz.get_robot_position()
                if x is None:
                    continue
                v, omega = arc_controller.mpc_control(x, y, theta)
                send_velocity(v, omega)
                rospy.sleep(0.1)
            send_velocity(0.0, 0.0)
            print("[Arc] 🎯 Đã hoàn thành một cung tròn")

    except Exception as e:
        print(f"[Arc] ❌ Lỗi MPC cung tròn: {e}")

@callback(
    Output("goal-status", "children", allow_duplicate=True),
    Input("start-arc-modal-btn", "n_clicks"),
    prevent_initial_call=True,
)
def start_arc_mpc(n_clicks):
    """Callback to start spline5_mpc_new.py when the button is clicked."""
    global is_moving, process

    # Stop any existing process if running
    if process is not None:
        is_moving = False
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
        process = None
        cancel_pub.publish(GoalID())
        print("📍 Sent cancel signal to /move_base/cancel")
        send_zero_velocity()

    # Start the MPC script
    is_moving = True
    script_path = "mpc_controller/arc_mpc_new.py"
    def run_script():
        global process
        try:
            process = subprocess.Popen(
                ["python3", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            if stdout:
                print(f"[Arc_MPC] Output: {stdout}")
            if stderr:
                print(f"[Arc_MPC] Error: {stderr}")
        except Exception as e:
            print(f"[Arc_MPC] Error running arc_mpc_new.py: {e}")
        finally:
            is_moving = False
            process = None
            if not rospy.is_shutdown():
                cancel_pub.publish(GoalID())
                send_zero_velocity()

    threading.Thread(target=run_script, daemon=True).start()
    return "🚀 Đang điều khiển arc bằng MPC..."

@callback(
    Output("arc-modal", "is_open"),
    [Input("move-arc-btn", "n_clicks"),
     Input("cancel-arc-modal", "n_clicks"),
     Input("start-arc-modal-btn", "n_clicks")],
    [State("arc-modal", "is_open")],
    prevent_initial_call=True
)
def toggle_arc_modal(n1, n2, n3, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == "move-arc-btn":
        return True
    elif trigger in ["cancel-arc-modal", "start-arc-modal-btn"]:
        return False
    return is_open

@callback(
    [Output("goal-status", "children", allow_duplicate=True),
     Output("emergency-stop-btn", "style"),
     Output("emergency-stop-state", "data")],
    Input("emergency-stop-btn", "n_clicks"),
    State("emergency-stop-state", "data"),
    prevent_initial_call=True
)
def emergency_stop(n_clicks, stop_state):
    global is_moving, process
    if n_clicks is None:
        raise PreventUpdate

    # Define button styles (consistent with create_rviz_section)
    emergency_stop_style = {
        "background": "linear-gradient(135deg, #DC3545 0%, #c82333 100%)",
        "color": "white",
        "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
        "borderRadius": "8px",
        "padding": "10px 20px",
        "border": "none",
        "cursor": "pointer",
        "fontFamily": "Arial, sans-serif",
        "fontWeight": "600",
        "fontSize": "14px",
        "width": "160px",
        "height": "40px",
        "textAlign": "center",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
    }
    emergency_stopped_style = {
        "background": "linear-gradient(135deg, #6C757D 0%, #5a6268 100%)",
        "color": "white",
        "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
        "borderRadius": "8px",
        "padding": "10px 20px",
        "border": "none",
        "cursor": "pointer",
        "fontFamily": "Arial, sans-serif",
        "fontWeight": "600",
        "fontSize": "14px",
        "width": "160px",
        "height": "40px",
        "textAlign": "center",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
    }

    is_stopped = stop_state["is_stopped"]
    rviz_section = RVizSection()

    if not is_stopped:
        # Activate emergency stop
        is_moving = False
        # Stop any running subprocess
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
            process = None
            print("📍 Terminated running MPC process")
        
        # Cancel any active goals
        cancel_pub.publish(GoalID())
        print("📍 Sent cancel signal to /move_base/cancel")
        
        # Send zero velocity
        status = rviz_section.stop_robot()
        
        new_state = {"is_stopped": True, "style": emergency_stopped_style}
        return f"🛑 Emergency Stop Activated: {status}", emergency_stopped_style, new_state
    else:
        # Release emergency stop
        is_moving = True
        new_state = {"is_stopped": False, "style": emergency_stop_style}
        return "🚀 Emergency Stop Released", emergency_stop_style, new_state

def create_rviz_section_layout():
    return create_rviz_section()