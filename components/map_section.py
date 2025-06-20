import rospy
from geometry_msgs.msg import Twist
from dash import Dash, dcc, html, Output, Input, State
from dash.dependencies import ClientsideFunction
import dash_bootstrap_components as dbc
import dash_daq as daq
import math

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Updated button styles to match status_bar.py's aesthetic
button_style = {
    "padding": "8px 16px",
    "border": "none",
    "color": "#FFFFFF",
    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
    "borderRadius": "8px",
    "transition": "all 0.3s ease",
    "cursor": "pointer",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
    "fontFamily": "Arial, sans-serif",
    "fontWeight": "600",
    "fontSize": "14px",
}

button_primary_style = {
    "width": "20%",
    "padding": "8px 16px",
    "border": "none",
    "color": "#FFFFFF",
    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
    "borderRadius": "8px",
    "transition": "all 0.3s ease",
    "cursor": "pointer",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
    "fontFamily": "Arial, sans-serif",
    "fontWeight": "600",
    "fontSize": "14px",
}

button_secondary_style = {
    "width": "100%",
    "padding": "8px 16px",
    "border": "none",
    "color": "#FFFFFF",
    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
    "borderRadius": "8px",
    "transition": "all 0.3s ease",
    "cursor": "pointer",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
    "fontFamily": "Arial, sans-serif",
    "fontWeight": "600",
    "fontSize": "14px",
}

button_hover_style = {
    "width": "100%",
    "padding": "8px 16px",
    "border": "none",
    "color": "#FFFFFF",
    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
    "borderRadius": "8px",
    "transition": "all 0.3s ease",
    "cursor": "pointer",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
    "fontFamily": "Arial, sans-serif",
    "fontWeight": "600",
    "fontSize": "14px",
}

button_default_manual_style = {
    "width": "100%",
    "padding": "8px 16px",
    "border": "none",
    "color": "#FFFFFF",
    "background": "linear-gradient(135deg, #D3D3D3 0%, #B0B0B0 100%)",
    "borderRadius": "8px",
    "transition": "all 0.3s ease",
    "cursor": "pointer",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
    "fontFamily": "Arial, sans-serif",
    "fontWeight": "600",
    "fontSize": "14px",
}

button_active_manual_style = {
    "width": "100%",
    "padding": "8px 16px",
    "border": "none",
    "color": "#FFFFFF",
    "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
    "borderRadius": "8px",
    "transition": "all 0.3s ease",
    "cursor": "pointer",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
    "fontFamily": "Arial, sans-serif",
    "fontWeight": "600",
    "fontSize": "14px",
}

def create_charging_status_component():
    return html.Div(
        id='charging-status-container',
        style={
            "border": "1px solid #ddd",
            "padding": "15px",
            "margin": "10px",
            "background": "linear-gradient(135deg, #f9f9f9 0%, #e9ecef 100%)",
            "borderRadius": "10px",
            "textAlign": "center",
            "width": "100%",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
            "fontFamily": "Arial, sans-serif",
        },
        children=[
            html.Div(
                id='status-message',
                children=[
                    html.I(id='status-icon', className="fas fa-spinner fa-spin me-2"),
                    html.Span(id='status-text', children="", style={"fontSize": "14px", "fontWeight": "600"}),
                ],
                style={"display": "flex", "alignItems": "center", "justifyContent": "center"},
            ),
            html.Div(
                id='status-details',
                style={"marginTop": "10px"},
                children=[
                    html.Span(id='status-action', style={"fontSize": "13px", "color": "#333"}),
                    html.Span(":", style={"margin": "0 5px"}),
                    html.Span(id='status-position', style={"fontSize": "13px", "color": "#333"}),
                    html.Div(
                        style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginTop': '10px'},
                        children=[
                            dbc.Badge(id='status-badge', color="success", className="me-1", style={"fontSize": "12px"}),
                            html.Button(
                                "X",
                                id='cancel-button',
                                style={
                                    "background": "linear-gradient(135deg, #dc3545 0%, #c82333 100%)",
                                    "color": "white",
                                    "border": "none",
                                    "padding": "6px 12px",
                                    "borderRadius": "8px",
                                    "cursor": "pointer",
                                    "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
                                    "fontFamily": "Arial, sans-serif",
                                    "fontWeight": "600",
                                    "fontSize": "12px",
                                }
                            ),
                        ]
                    )
                ]
            )
        ]
    )

def create_plc_info_component():
    return html.Div(
        style={
            "border": "1px solid #ddd",
            "padding": "15px",
            "margin": "10px",
            "background": "linear-gradient(135deg, #e1f5fe 0%, #d1e7f8 100%)",
            "borderRadius": "10px",
            "textAlign": "center",
            "width": "100%",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
            "fontFamily": "Arial, sans-serif",
        },
        children=[
            html.Div("PLC register 160", style={"fontSize": "14px", "fontWeight": "600", "color": "#333"}),
            html.Div("...", style={"fontSize": "12px", "color": "#6c757d", "margin": "5px 0"}),
            html.Div("Current value: 1", style={"fontSize": "13px", "color": "#333"}),
        ],
    )

def create_manual_control_component():
    return html.Div(
        style={
            "border": "1px solid #ddd",
            "padding": "15px",
            "margin": "10px",
            "background": "linear-gradient(135deg, #f9f9f9 0%, #e9ecef 100%)",
            "borderRadius": "10px",
            "textAlign": "center",
            "width": "100%",
            "height": "437px",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
            "fontFamily": "Arial, sans-serif",
        },
        children=[
            html.Button(
                "MANUAL CONTROL",
                id="manual-control",
                className="btn btn-secondary",
                style=button_default_manual_style
            ),
            html.Div(
                id="joystick-container",
                style={"display": "none"},
                children=[
                    daq.Joystick(
                        id='joystick',
                        label="Control Joystick",
                        size=150,
                        style={'margin': 'auto'}
                    ),
                    html.Label("Speed Scale:", style={'marginTop': '10px', 'fontSize': '14px', 'color': '#333'}),
                    html.Div([
                        dcc.Slider(
                            id='speed-scale',
                            min=0.1,
                            max=1.0,
                            step=0.1,
                            value=0.5,
                            marks={i/10: str(i/10) for i in range(1, 11)},
                            updatemode='drag'
                        )
                    ], style={'width': '80%', 'margin': '10px auto'}),
                    daq.BooleanSwitch(
                        id='emergency-stop',
                        on=False,
                        label="Emergency Stop",
                        labelPosition="top",
                        color="#ff0000",
                        style={'margin': '10px auto'}
                    ),
                    html.Div(
                        id='joystick-output',
                        style={
                            'marginTop': '10px',
                            'fontSize': '14px',
                            'color': '#333',
                            'textAlign': 'center',
                            'fontFamily': 'Arial, sans-serif',
                        }
                    ),
                    dcc.Store(id='joystick-data', data={'angle': 0, 'force': 0}),
                    dcc.Interval(id='interval-joystick', interval=50, n_intervals=0, disabled=True),
                ]
            ),
        ],
    )

class MapSection:
    def create_map_section(self):
        return html.Div(
            style={
                'backgroundColor': '#FFFFFF',
                'height': '100vh',
                'fontFamily': 'Arial, sans-serif',
                'boxShadow': '0 4px 12px rgba(0,0,0,0.15)',
            },
            children=[
                html.Div(
                    [
                        html.H3(
                            "HOME",
                            className="mb-3",
                            style={
                                "color": "#34495E",
                                "fontWeight": "bold",
                                "fontSize": "24px",
                                "padding": "10px 0",
                            }
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Div(
                                            [
                                                html.Button("Add Markers", id="add-markers-btn",
                                                            className="fas fa-map-marker-alt me-2", style=button_primary_style),
                                                dbc.Popover(
                                                    [
                                                        dbc.PopoverHeader("Select an option", style={"fontSize": "14px", "fontWeight": "600"}),
                                                        dbc.PopoverBody(
                                                            [
                                                                html.Button("Add Positions", id="add-positions-btn",
                                                                            className="fas fa-compass me-2",
                                                                            style=button_hover_style),
                                                                html.Button("Add Dockers", id="add-dockers-btn",
                                                                            className="fas fa-bolt me-2",
                                                                            style=button_hover_style),
                                                            ]
                                                        ),
                                                    ],
                                                    id="popover",
                                                    target="add-markers-btn",
                                                    trigger="click",
                                                    placement="left",
                                                    style={"borderRadius": "10px", "boxShadow": "0 6px 20px rgba(0,0,0,0.15)"}
                                                ),
                                                html.Button("Delete Marker", id="delete-marker-btn",
                                                            className="fas fa-trash me-2", style=button_primary_style),
                                                dbc.Modal(
                                                    [
                                                        dbc.ModalHeader(dbc.ModalTitle("Delete Marker", style={"fontSize": "16px", "fontWeight": "600"})),
                                                        dbc.ModalBody(
                                                            [
                                                                dcc.Dropdown(id="marker-dropdown",
                                                                             placeholder="Choose Marker to Delete",
                                                                             style={"fontSize": "14px", "borderRadius": "8px"}),
                                                            ]
                                                        ),
                                                        dbc.ModalFooter(
                                                            [
                                                                html.Button("Delete", id="confirm-delete-btn",
                                                                            className="btn btn-danger me-2",
                                                                            style=button_style),
                                                                html.Button("Cancel", id="close-delete-modal",
                                                                            className="btn btn-secondary",
                                                                            style=button_style),
                                                            ]
                                                        ),
                                                    ],
                                                    id="delete-marker-modal",
                                                    is_open=False,
                                                    style={"borderRadius": "10px"}
                                                ),
                                                html.Button("Add Mission", id="add-mission-marker-btn",
                                                            className="fas fa-bullseye me-2", style=button_primary_style),
                                                dbc.Modal(
                                                    [
                                                        dbc.ModalHeader(dbc.ModalTitle("Add Mission From Markers", style={"fontSize": "16px", "fontWeight": "600"})),
                                                        dbc.ModalBody(
                                                            [
                                                                dcc.Dropdown(id="mission-marker-dropdown",
                                                                             placeholder="Choose Marker to Add Mission",
                                                                             style={"fontSize": "14px", "borderRadius": "8px"}),
                                                            ]
                                                        ),
                                                        dbc.ModalFooter(
                                                            [
                                                                html.Button("Append", id="append-mission-btn",
                                                                            className="btn btn-success me-2",
                                                                            style=button_style),
                                                                html.Button("Clear and Append", id="clear-and-append-btn",
                                                                            className="btn btn-danger me-2",
                                                                            style=button_style),
                                                                html.Button("Cancel", id="close-delete-mission-modal",
                                                                            className="btn btn-secondary",
                                                                            style=button_style),
                                                            ]
                                                        ),
                                                    ],
                                                    id="add-mission-marker-modal",
                                                    is_open=False,
                                                    style={"borderRadius": "10px"}
                                                ),
                                            ],
                                            className="mb-3",
                                            style={"display": "flex", "gap": "10px"}
                                        ),

                                        dbc.Modal(
                                            [
                                                dbc.ModalHeader(dbc.ModalTitle("Add Position", style={"fontSize": "16px", "fontWeight": "600"})),
                                                dbc.ModalBody(
                                                    [
                                                        dbc.Form(
                                                            [
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Label("Name:", width=2, style={"fontSize": "14px"}),
                                                                        dbc.Col(
                                                                            dbc.Input(type="text", id="name-position",
                                                                                      placeholder="Enter Name of Position",
                                                                                      style={"fontSize": "14px", "borderRadius": "8px"}),
                                                                            width=10,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Label("X:", width=2, style={"fontSize": "14px"}),
                                                                        dbc.Col(
                                                                            dbc.Input(type="number", id="x-input",
                                                                                      placeholder="Enter X coordinate",
                                                                                      style={"fontSize": "14px", "borderRadius": "8px"}),
                                                                            width=10,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Label("Y:", width=2, style={"fontSize": "14px"}),
                                                                        dbc.Col(
                                                                            dbc.Input(type="number", id="y-input",
                                                                                      placeholder="Enter Y coordinate",
                                                                                      style={"fontSize": "14px", "borderRadius": "8px"}),
                                                                            width=10,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Label("Z:", width=2, style={"fontSize": "14px"}),
                                                                        dbc.Col(
                                                                            dbc.Input(type="number", id="z-input",
                                                                                      placeholder="Enter Z coordinate",
                                                                                      style={"fontSize": "14px", "borderRadius": "8px"}),
                                                                            width=10,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Label("W:", width=2, style={"fontSize": "14px"}),
                                                                        dbc.Col(
                                                                            dbc.Input(type="number", id="w-input",
                                                                                      placeholder="Enter W coordinate",
                                                                                      style={"fontSize": "14px", "borderRadius": "8px"}),
                                                                            width=10,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                            ]
                                                        ),
                                                    ]
                                                ),
                                                dbc.ModalFooter(
                                                    [
                                                        html.Button("Use Robot Position", id="use-robot-btn",
                                                                    className="btn btn-secondary me-2",
                                                                    style=button_style),
                                                        html.Button("Add Position", id="add-position-btn",
                                                                    className="btn btn-primary me-2",
                                                                    style=button_style),
                                                        html.Button("Cancel", id="cancel-btn", className="btn btn-danger",
                                                                    style=button_style),
                                                    ]
                                                ),
                                            ],
                                            id="position-modal",
                                            is_open=False,
                                            style={"borderRadius": "10px"}
                                        ),

                                        dbc.Modal(
                                            [
                                                dbc.ModalHeader(dbc.ModalTitle("Add Docker", style={"fontSize": "16px", "fontWeight": "600"})),
                                                dbc.ModalBody(
                                                    [
                                                        dbc.Form(
                                                            [
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Label("Name:", width=2, style={"fontSize": "14px"}),
                                                                        dbc.Col(
                                                                            dbc.Input(type="text", id="name-docker",
                                                                                      placeholder="Enter Name of Docker",
                                                                                      style={"fontSize": "14px", "borderRadius": "8px"}),
                                                                            width=10,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Label("X:", width=2, style={"fontSize": "14px"}),
                                                                        dbc.Col(
                                                                            dbc.Input(type="number", id="docker-x",
                                                                                      placeholder="Enter X coordinate",
                                                                                      style={"fontSize": "14px", "borderRadius": "8px"}),
                                                                            width=10,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Label("Y:", width=2, style={"fontSize": "14px"}),
                                                                        dbc.Col(
                                                                            dbc.Input(type="number", id="docker-y",
                                                                                      placeholder="Enter Y coordinate",
                                                                                      style={"fontSize": "14px", "borderRadius": "8px"}),
                                                                            width=10,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Label("Z:", width=2, style={"fontSize": "14px"}),
                                                                        dbc.Col(
                                                                            dbc.Input(type="number", id="docker-z",
                                                                                      placeholder="Enter Z coordinate",
                                                                                      style={"fontSize": "14px", "borderRadius": "8px"}),
                                                                            width=10,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                                dbc.Row(
                                                                    [
                                                                        dbc.Label("W:", width=2, style={"fontSize": "14px"}),
                                                                        dbc.Col(
                                                                            dbc.Input(type="number", id="docker-w",
                                                                                      placeholder="Enter W coordinate",
                                                                                      style={"fontSize": "14px", "borderRadius": "8px"}),
                                                                            width=10,
                                                                        ),
                                                                    ],
                                                                    className="mb-3",
                                                                ),
                                                            ]
                                                        ),
                                                    ]
                                                ),
                                                dbc.ModalFooter(
                                                    [
                                                        html.Button("Use Robot Position", id="use-robot-docker-btn",
                                                                    className="btn btn-secondary me-2",
                                                                    style=button_style),
                                                        html.Button("Add Docker", id="add-docker-btn",
                                                                    className="btn btn-primary me-2",
                                                                    style=button_style),
                                                        html.Button("Cancel", id="cancel-btn", className="btn btn-danger",
                                                                    style=button_style),
                                                    ]
                                                ),
                                            ],
                                            id="docker-modal",
                                            is_open=False,
                                            style={"borderRadius": "10px"}
                                        ),

                                        html.Div(
                                            [
                                                html.Img(
                                                    id="map-image",
                                                    src="/static/map_image.png",
                                                    style={
                                                        "width": "100%",
                                                        "height": "600px",
                                                        "border": "5px solid #34495E",
                                                        "borderRadius": "10px",
                                                        "objectFit": "contain",
                                                        "position": "relative",
                                                        "zIndex": "1",
                                                        "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                                    },
                                                ),
                                                html.Img(
                                                    id="lidar-f-image",
                                                    src="/static/f_scan_image.png",
                                                    style={
                                                        "width": "100%",
                                                        "height": "600px",
                                                        "border": "5px solid #34495E",
                                                        "borderRadius": "10px",
                                                        "objectFit": "contain",
                                                        "position": "absolute",
                                                        "top": "0",
                                                        "left": "0",
                                                        "zIndex": "2",
                                                        "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                                    },
                                                ),
                                                html.Img(
                                                    id="lidar-b-image",
                                                    src="/static/b_scan_image.png",
                                                    style={
                                                        "width": "100%",
                                                        "height": "600px",
                                                        "border": "5px solid #34495E",
                                                        "borderRadius": "10px",
                                                        "objectFit": "contain",
                                                        "position": "absolute",
                                                        "top": "0",
                                                        "left": "0",
                                                        "zIndex": "2",
                                                        "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                                    },
                                                ),
                                                html.Img(
                                                    id="path-image",
                                                    src="/static/path_image.png",
                                                    style={
                                                        "width": "100%",
                                                        "height": "600px",
                                                        "border": "5px solid #34495E",
                                                        "borderRadius": "10px",
                                                        "objectFit": "contain",
                                                        "position": "absolute",
                                                        "top": "0",
                                                        "left": "0",
                                                        "zIndex": "3",
                                                        "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                                    },
                                                ),
                                                html.Img(
                                                    id="robot-image",
                                                    src="/static/robot_image.png",
                                                    style={
                                                        "width": "100%",
                                                        "height": "600px",
                                                        "border": "5px solid #34495E",
                                                        "borderRadius": "10px",
                                                        "objectFit": "contain",
                                                        "position": "absolute",
                                                        "top": "0",
                                                        "left": "0",
                                                        "zIndex": "7",
                                                        "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                                    },
                                                ),
                                                html.Img(
                                                    id="paths-image",
                                                    src="/static/ptah_img.png",
                                                    style={
                                                        "width": "100%",
                                                        "height": "600px",
                                                        "border": "5px solid #34495E",
                                                        "borderRadius": "10px",
                                                        "objectFit": "contain",
                                                        "position": "absolute",
                                                        "top": "0",
                                                        "left": "0",
                                                        "zIndex": "6",
                                                        "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                                    },
                                                ),
                                                html.Img(
                                                    id="markers-image",
                                                    src="/static/all_markers.png",
                                                    style={
                                                        "width": "100%",
                                                        "height": "600px",
                                                        "border": "5px solid #34495E",
                                                        "borderRadius": "10px",
                                                        "objectFit": "contain",
                                                        "position": "absolute",
                                                        "top": "0",
                                                        "left": "0",
                                                        "zIndex": "4",
                                                        "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                                    },
                                                ),
                                                html.Img(
                                                    id="dockers-image",
                                                    src="/static/all_dockers.png",
                                                    style={
                                                        "width": "100%",
                                                        "height": "600px",
                                                        "border": "5px solid #34495E",
                                                        "borderRadius": "10px",
                                                        "objectFit": "contain",
                                                        "position": "absolute",
                                                        "top": "0",
                                                        "left": "0",
                                                        "zIndex": "5",
                                                        "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                                    },
                                                ),
                                            ],
                                            style={"position": "relative", "marginBottom": "10px"}
                                        ),
                                        create_charging_status_component(),
                                    ],
                                    width=8,
                                ),

                                dbc.Col(
                                    [
                                        html.Button(
                                            id="pause-button-1",
                                            children=html.I(className="fas fa-play"),
                                            style={
                                                "width": "100%",
                                                "height": "100px",
                                                "background": "linear-gradient(135deg, #003049 0%, #00283D 100%)",
                                                "color": "#08702B",
                                                "display": "flex",
                                                "justifyContent": "center",
                                                "alignItems": "center",
                                                "fontSize": "4em",
                                                "borderRadius": "10px",
                                                "marginBottom": "10px",
                                                "marginTop": "10px",
                                                "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                                            },
                                        ),
                                        create_plc_info_component(),
                                        create_plc_info_component(),
                                        create_manual_control_component(),
                                    ],
                                    width=4,
                                )
                            ]
                        ),
                        html.Div(id="content-area"),
                        dcc.Interval(
                            id='interval-component',
                            interval=1 * 1000,
                            n_intervals=0
                        ),
                        dcc.Interval(id="check-status-interval", interval=1000, n_intervals=0)
                    ],
                    style={
                        "padding": "20px",
                        "flex": "1",
                        "marginLeft": "50px",
                        "marginTop": "50px",
                        "background": "linear-gradient(135deg, #FFFFFF 0%, #F5F7FA 100%)",
                        "borderRadius": "10px",
                        "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                    },
                )
            ]
        )