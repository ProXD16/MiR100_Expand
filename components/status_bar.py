
from dash import dcc, html, callback, Input, Output, State
import dash_bootstrap_components as dbc
from utils_function.data import LANGUAGES
from dash_iconify import DashIconify
import json
import os
import threading, subprocess
import dash_daq as daq

class StatusBar:
    def create_status_bar(self):
        return html.Div(
            [
                dbc.Row(
                    [
                        # Play/Pause button
                        dbc.Col(
                            [
                                html.Button(
                                    html.I(className="fas fa-play"),
                                    id="pause-button",
                                    className="btn btn-success btn-sm me-2",
                                    style={
                                        "marginLeft": "5px",
                                        "borderRadius": "8px",
                                        "border": "none",
                                        "boxShadow": "0 2px 4px rgba(0,0,0,0.2)",
                                        "transition": "all 0.3s ease",
                                        "padding": "8px 12px"
                                    }
                                )
                            ],
                            width="auto",
                            style={"padding": "5px", "display": "flex", "alignItems": "center", "marginRight": "2px"}
                        ),
                        
                        # Program Queue section with Play Programming button
                        dbc.Col(
                            html.Div(
                                [
                                    # Program Queue Dropdown
                                    dbc.Button(
                                        [
                                            DashIconify(
                                                icon="mdi:playlist-play", 
                                                width=16, 
                                                height=16, 
                                                style={"color": "#666", "marginRight": "8px"}
                                            ),
                                            html.Span(
                                                "Program Queue", 
                                                id="status-bar-program",
                                                style={
                                                    "color": "#333", 
                                                    "fontFamily": "Arial, sans-serif",
                                                    "fontSize": "14px",
                                                    "fontWeight": "500"
                                                }
                                            ),
                                            DashIconify(
                                                icon="mdi:chevron-down", 
                                                width=16, 
                                                height=16, 
                                                style={"color": "#666", "marginLeft": "8px"}
                                            )
                                        ],
                                        id="program-queue-button",
                                        color="light",
                                        className="d-flex align-items-center",
                                        style={
                                            "backgroundColor": "white",
                                            "border": "1px solid #ddd",
                                            "borderRadius": "8px",
                                            "padding": "8px 12px",
                                            "boxShadow": "0 2px 6px rgba(0,0,0,0.15)",
                                            "transition": "all 0.3s ease",
                                            "minWidth": "160px",
                                            "marginRight": "8px"
                                        }
                                    ),
                                    
                                    # Play Programming Button
                                    dbc.Button(
                                        [
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
                                        ],
                                        id="play-programming-btn",
                                        color="primary",
                                        className="d-flex align-items-center",
                                        style={
                                            "backgroundColor": "#007bff",
                                            "border": "none",
                                            "borderRadius": "8px",
                                            "padding": "8px 14px",
                                            "boxShadow": "0 2px 6px rgba(0,123,255,0.3)",
                                            "transition": "all 0.3s ease",
                                            "fontSize": "13px"
                                        }
                                    ),
                                    
                                    # Dropdown collapse
                                    dbc.Collapse(
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        [
                                                            html.H6(
                                                                [
                                                                    DashIconify(
                                                                        icon="mdi:format-list-bulleted", 
                                                                        width=18, 
                                                                        height=18, 
                                                                        style={"marginRight": "8px", "color": "#007bff"}
                                                                    ),
                                                                    "Available Programs"
                                                                ],
                                                                className="mb-3 d-flex align-items-center",
                                                                style={
                                                                    "color": "#333",
                                                                    "fontWeight": "600",
                                                                    "borderBottom": "1px solid #eee",
                                                                    "paddingBottom": "8px"
                                                                }
                                                            ),
                                                            html.Div(id="program-list-container")
                                                        ]
                                                    )
                                                ],
                                                style={"padding": "15px"}
                                            ),
                                            style={
                                                "maxHeight": "300px",
                                                "overflowY": "auto",
                                                "border": "1px solid #ddd",
                                                "borderRadius": "10px",
                                                "boxShadow": "0 6px 20px rgba(0,0,0,0.15)"
                                            }
                                        ),
                                        id="program-queue-collapse",
                                        is_open=False,
                                        style={
                                            "position": "absolute",
                                            "top": "100%",
                                            "left": "0",
                                            "zIndex": "1050",
                                            "marginTop": "5px",
                                            "minWidth": "300px"
                                        }
                                    )
                                ],
                                className="d-flex align-items-center",
                                style={
                                    "position": "relative",
                                    "display": "inline-flex"
                                }
                            ),
                            width="auto",
                            style={"padding": "5px", "marginRight": "5px"}
                        ),
                        
                        # Status indicator
                        dbc.Col(
                            [
                                DashIconify(
                                    icon="mdi:check-circle", 
                                    width=20, 
                                    height=20, 
                                    style={"color": "#4CAF50", "marginRight": "6px"}
                                ),
                                html.Span(
                                    "ALL OK",
                                    style={
                                        "color": "white",
                                        "fontWeight": "bold",
                                        "fontFamily": "Arial, sans-serif",
                                        "backgroundColor": "#4CAF50",
                                        "padding": "4px 8px",
                                        "borderRadius": "6px",
                                        "fontSize": "12px",
                                        "boxShadow": "0 2px 4px rgba(76,175,80,0.3)"
                                    }
                                )
                            ],
                            width="auto",
                            style={"padding": "5px", "display": "flex", "alignItems": "center"}
                        ),
                        
                        # Language dropdown
                        dbc.Col(
                            dcc.Dropdown(
                                id="language-dropdown",
                                options=[
                                    {"label": [html.Img(src="https://flagcdn.com/w20/us.png", style={"marginRight": "5px"}), "English"], "value": "en"},
                                    {"label": [html.Img(src="https://flagcdn.com/w20/vn.png", style={"marginRight": "5px"}), "Vietnamese"], "value": "vi"},
                                    {"label": [html.Img(src="https://flagcdn.com/w20/cn.png", style={"marginRight": "5px"}), "Chinese"], "value": "ch"},
                                ],
                                value="en",
                                clearable=False,
                                style={
                                    "color": "black", 
                                    "backgroundColor": "rgba(255,255,255,0.9)", 
                                    "border": "none", 
                                    "fontFamily": "Arial, sans-serif", 
                                    "width": "150px",
                                    "borderRadius": "8px"
                                }
                            ),
                            width="auto",
                            style={"padding": "5px"}
                        ),
                        
                        # Administrator section
                        dbc.Col(
                            [
                                dbc.Button(
                                    [
                                        DashIconify(
                                            icon="mdi:account-circle", 
                                            width=22, 
                                            height=22, 
                                            style={"color": "white", "marginRight": "6px"}
                                        ),
                                        html.Span(
                                            "ADMINISTRATOR", 
                                            style={
                                                "color": "white", 
                                                "fontFamily": "Arial, sans-serif",
                                                "fontWeight": "600",
                                                "fontSize": "13px"
                                            }
                                        )
                                    ],
                                    id="admin-popover-target",
                                    color="link",
                                    className="d-flex align-items-center",
                                    style={
                                        "padding": "6px 12px", 
                                        "textDecoration": "none",
                                        "borderRadius": "8px",
                                        "transition": "all 0.3s ease",
                                        "backgroundColor": "rgba(255,255,255,0.1)",
                                        "border": "1px solid rgba(255,255,255,0.2)"
                                    }
                                ),
                                dbc.Popover(
                                    [
                                        dbc.PopoverHeader(
                                            "Admin Profile", 
                                            style={
                                                "fontWeight": "bold",
                                                "backgroundColor": "#f8f9fa",
                                                "borderBottom": "1px solid #dee2e6"
                                            }
                                        ),
                                        dbc.PopoverBody(
                                            [
                                                html.Div(
                                                    [
                                                        html.Div(
                                                            [
                                                                html.Img(
                                                                    src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                                                                    style={
                                                                        "width": "60px", 
                                                                        "height": "60px", 
                                                                        "borderRadius": "50%", 
                                                                        "marginBottom": "12px",
                                                                        "border": "3px solid #e9ecef"
                                                                    }
                                                                ),
                                                                html.H5(
                                                                    "Admin User", 
                                                                    style={
                                                                        "marginBottom": "5px", 
                                                                        "fontWeight": "bold",
                                                                        "color": "#333"
                                                                    }
                                                                ),
                                                                html.P(
                                                                    "Duc.CX216089@sis.hust.edu.vn" \
                                                                    "Hieu.TQ210349@sis.hust.edu.vn", 
                                                                    style={
                                                                        "color": "#6c757d", 
                                                                        "marginBottom": "15px", 
                                                                        "fontSize": "0.9em"
                                                                    }
                                                                ),
                                                                html.Hr(style={"margin": "15px 0"}),
                                                                dbc.Button(
                                                                    [
                                                                        DashIconify(
                                                                            icon="mdi:logout", 
                                                                            width=18, 
                                                                            style={"marginRight": "6px"}
                                                                        ),
                                                                        "Change Mode"
                                                                    ],
                                                                    id="logout-button",
                                                                    color="danger",
                                                                    className="w-100",
                                                                    style={
                                                                        "borderRadius": "8px",
                                                                        "fontWeight": "500"
                                                                    }
                                                                )
                                                            ],
                                                            style={"textAlign": "center", "padding": "10px"}
                                                        )
                                                    ]
                                                )
                                            ]
                                        )
                                    ],
                                    id="admin-popover",
                                    target="admin-popover-target",
                                    trigger="click",
                                    placement="bottom",
                                    style={
                                        "width": "260px",
                                        "borderRadius": "10px",
                                        "boxShadow": "0 8px 25px rgba(0,0,0,0.15)"
                                    }
                                )
                            ],
                            width="auto",
                            style={"padding": "5px", "display": "flex", "alignItems": "center"}
                        ),

                        # Joystick Button and Popover
                        dbc.Col(
                            [
                                dbc.Button(
                                    [
                                        DashIconify(
                                            icon="mdi:gamepad-variant", 
                                            width=22, 
                                            height=22, 
                                            style={"color": "white", "marginRight": "6px"}
                                        ),
                                        html.Span(
                                            "JOYSTICK", 
                                            style={
                                                "color": "white", 
                                                "fontFamily": "Arial, sans-serif",
                                                "fontWeight": "600",
                                                "fontSize": "13px"
                                            }
                                        )
                                    ],
                                    id="joystick-popover-target",
                                    color="link",
                                    className="d-flex align-items-center",
                                    style={
                                        "padding": "6px 12px", 
                                        "textDecoration": "none",
                                        "borderRadius": "8px",
                                        "transition": "all 0.3s ease",
                                        "backgroundColor": "rgba(255,255,255,0.1)",
                                        "border": "1px solid rgba(255,255,255,0.2)"
                                    }
                                ),
                                dbc.Popover(
                                    [
                                        dbc.PopoverHeader(
                                            "Joystick Control", 
                                            style={
                                                "fontWeight": "bold",
                                                "backgroundColor": "#f8f9fa",
                                                "borderBottom": "1px solid #dee2e6"
                                            }
                                        ),
                                        dbc.PopoverBody(
                                            [
                                                html.Div(
                                                    [
                                                        DashIconify(
                                                            icon="mdi:gamepad-circle-outline", 
                                                            width=40, 
                                                            height=40, 
                                                            style={"color": "#333", "marginBottom": "10px"}
                                                        ),
                                                        html.P(
                                                            "Joystick Interface", 
                                                            style={"fontWeight": "bold", "marginBottom": "10px", "color": "#333"}
                                                        ),
                                                        daq.Joystick(
                                                            id="status-joystick",
                                                            label="Control Joystick",
                                                            size=120,
                                                            style={"margin": "auto", "display": "block"}
                                                        ),
                                                        html.Label(
                                                            "Speed Scale:",
                                                            style={"marginTop": "10px", "fontSize": "13px", "color": "#333"}
                                                        ),
                                                        html.Div(
                                                            [
                                                                dcc.Slider(
                                                                    id="status-speed-scale",
                                                                    min=0.1,
                                                                    max=1.0,
                                                                    step=0.1,
                                                                    value=0.5,
                                                                    marks={i/10: str(i/10) for i in range(1, 11)},
                                                                    updatemode="drag"
                                                                )
                                                            ],
                                                            style={"width": "80%", "margin": "10px auto"}
                                                        ),
                                                        daq.BooleanSwitch(
                                                            id="status-emergency-stop",
                                                            on=False,
                                                            label="Emergency Stop",
                                                            labelPosition="top",
                                                            color="#ff0000",
                                                            style={"margin": "10px auto"}
                                                        ),
                                                        html.Div(
                                                            id="status-joystick-output",
                                                            style={
                                                                "marginTop": "10px",
                                                                "fontSize": "13px",
                                                                "color": "#333",
                                                                "textAlign": "center",
                                                                "fontFamily": "Arial, sans-serif"
                                                            }
                                                        ),
                                                        dcc.Store(id="status-joystick-data", data={"angle": 0, "force": 0}),
                                                        dcc.Interval(id="status-interval-joystick", interval=50, n_intervals=0, disabled=False)
                                                    ],
                                                    style={
                                                        "textAlign": "center",
                                                        "padding": "15px",
                                                        "background": "linear-gradient(135deg, #f9f9f9 0%, #e9ecef 100%)",
                                                        "borderRadius": "8px"
                                                    }
                                                )
                                            ]
                                        )
                                    ],
                                    id="joystick-popover",
                                    target="joystick-popover-target",
                                    trigger="click",
                                    placement="bottom",
                                    style={
                                        "width": "300px",
                                        "borderRadius": "10px",
                                        "boxShadow": "0 8px 25px rgba(0,0,0,0.15)"
                                    }
                                )
                            ],
                            width="auto",
                            style={"padding": "5px", "display": "flex", "alignItems": "center"}
                        ),
                        
                        # Voice Chat Button and Popover (NEW)
                        dbc.Col(
                            [
                                dbc.Button(
                                    [
                                        DashIconify(
                                            icon="mdi:microphone", 
                                            width=22, 
                                            height=22, 
                                            style={"color": "white", "marginRight": "6px"}
                                        ),
                                        html.Span(
                                            "VOICE CHAT", 
                                            style={
                                                "color": "white", 
                                                "fontFamily": "Arial, sans-serif",
                                                "fontWeight": "600",
                                                "fontSize": "13px"
                                            }
                                        )
                                    ],
                                    id="voice-chat-popover-target", # Unique ID for the voice chat button
                                    color="link",
                                    className="d-flex align-items-center",
                                    style={
                                        "padding": "6px 12px", 
                                        "textDecoration": "none",
                                        "borderRadius": "8px",
                                        "transition": "all 0.3s ease",
                                        "backgroundColor": "rgba(255,255,255,0.1)",
                                        "border": "1px solid rgba(255,255,255,0.2)"
                                    }
                                ),
                                dbc.Popover(
                                    [
                                        dbc.PopoverHeader(
                                            "Voice Chat Control", 
                                            style={
                                                "fontWeight": "bold",
                                                "backgroundColor": "#f8f9fa",
                                                "borderBottom": "1px solid #dee2e6"
                                            }
                                        ),
                                        dbc.PopoverBody(
                                            [
                                                html.Div(
                                                    [
                                                        DashIconify(
                                                            icon="mdi:microphone-outline", 
                                                            width=40, 
                                                            height=40, 
                                                            style={"color": "#333", "marginBottom": "10px"}
                                                        ),
                                                        html.P(
                                                            "Voice Chat Interface", 
                                                            style={"fontWeight": "bold", "marginBottom": "5px", "color": "#333"}
                                                        ),
                                                        html.Small(
                                                            "This area will host voice chat functionalities.", 
                                                            style={"color": "#6c757d"}
                                                        )
                                                    ],
                                                    style={"textAlign": "center", "padding": "15px"}
                                                )
                                            ]
                                        )
                                    ],
                                    id="voice-chat-popover", # Unique ID for the voice chat popover
                                    target="voice-chat-popover-target", # Points to the voice chat button
                                    trigger="click",
                                    placement="bottom",
                                    style={
                                        "width": "280px",
                                        "borderRadius": "10px",
                                        "boxShadow": "0 8px 25px rgba(0,0,0,0.15)"
                                    }
                                )
                            ],
                            width="auto",
                            style={"padding": "5px", "display": "flex", "alignItems": "center"}
                        ),
                        
                        # Battery indicator
                        dbc.Col(
                            [
                                html.Span(
                                    id="battery-percen", 
                                    children="94%", 
                                    style={
                                        "color": "white", 
                                        "fontFamily": "Arial, sans-serif",
                                        "fontWeight": "600",
                                        "fontSize": "14px"
                                    }
                                ),
                                DashIconify(
                                    icon="mdi:battery-90", 
                                    width=22, 
                                    height=22, 
                                    style={"color": "#4CAF50", "marginRight": "12px",
                                           "transform": "rotate(90deg)", 
                                            "transformOrigin": "center"}
                                ),
                                
                            ],
                            width="auto",
                            style={"padding": "5px", "display": "flex", "alignItems": "center"}
                        ),
                    ],
                    align="center",
                    className="g-0",
                    style={"justifyContent": "space-between", "display": "flex"}
                ),
            ],
            style={
                "background": "linear-gradient(135deg, #77B5FE 0%, #6ba3fc 100%)",
                "color": "white",
                "padding": "8px 15px",
                "position": "fixed",
                "top": 0,
                "left": "250px",
                "width": "calc(100% - 250px)",
                "zIndex": 1000,
                "fontFamily": "Arial, sans-serif",
                "boxShadow": "0 4px 12px rgba(0,0,0,0.15)",
                "backdropFilter": "blur(10px)"
            }
        )

    def load_program_queue(self):
        """Load programs from JSON file"""
        try:
            json_path = "/home/duc/Downloads/MIR100_WebApp/database_json/queue_programming.json"
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    programs = json.load(f)
                return programs
            else:
                return []
        except Exception as e:
            print(f"Error loading program queue: {e}")
            return []

    def create_program_list(self, programs):
        """Create the program list display"""
        if not programs:
            return html.Div(
                [
                    DashIconify(
                        icon="mdi:information-outline", 
                        width=24, 
                        height=24, 
                        style={"color": "#6c757d", "marginBottom": "8px"}
                    ),
                    html.P(
                        "No programs available", 
                        style={
                            "color": "#6c757d", 
                            "fontStyle": "italic",
                            "textAlign": "center",
                            "margin": "0"
                        }
                    )
                ],
                style={"textAlign": "center", "padding": "20px"}
            )
        
        program_items = []
        for i, program in enumerate(programs):
            program_name = program.get('name', f'Program {i+1}')
            command_count = len(program.get('commands', []))
            
            program_items.append(
                html.Div(
                    [
                        html.Div(
                            [
                                DashIconify(
                                    icon="mdi:code-braces", 
                                    width=20, 
                                    height=20, 
                                    style={"color": "#007bff", "marginRight": "10px"}
                                ),
                                html.Div(
                                    [
                                        html.Span(
                                            program_name,
                                            style={
                                                "fontWeight": "600",
                                                "color": "#333",
                                                "fontSize": "14px"
                                            }
                                        ),
                                        html.Br(),
                                        html.Span(
                                            f"{command_count} commands",
                                            style={
                                                "fontSize": "12px",
                                                "color": "#6c757d"
                                            }
                                        )
                                    ]
                                )
                            ],
                            className="d-flex align-items-center",
                            style={"flex": "1"}
                        ),
                        html.Div(
                            DashIconify(
                                icon="mdi:eye-outline", 
                                width=16, 
                                height=16, 
                                style={"color": "#6c757d"}
                            ),
                            style={"marginLeft": "auto"}
                        )
                    ],
                    className="d-flex align-items-center",
                    style={
                        "padding": "12px",
                        "marginBottom": "8px",
                        "backgroundColor": "#f8f9fa",
                        "border": "1px solid #e9ecef",
                        "borderRadius": "8px",
                        "cursor": "pointer",
                        "transition": "all 0.3s ease"
                    },
                    **{
                        "data-bs-toggle": "tooltip",
                        "title": f"View program: {program_name}"
                    }
                )
            )
        
        return html.Div(program_items)