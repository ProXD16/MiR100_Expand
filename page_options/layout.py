from dash import html, dcc
import dash_bootstrap_components as dbc

def get_layout():
    # Define button styles
    primary_button_style = {
        "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
        "color": "white",
        "border": "none",
        "borderRadius": "25px",
        "padding": "12px 35px",
        "fontFamily": "Arial, sans-serif",
        "fontWeight": "600",
        "fontSize": "14px",
        "boxShadow": "0 4px 15px rgba(52, 152, 219, 0.4)",
        "cursor": "pointer",
        "width": "140px",
        "textAlign": "center",
        "textTransform": "uppercase",
        "letterSpacing": "1px",
    }
    
    active_button_style = {
        **primary_button_style,
        "background": "linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)",
        "boxShadow": "0 4px 15px rgba(39, 174, 96, 0.4)",
    }
    
    confirm_button_style = {
        **primary_button_style,
        "background": "linear-gradient(135deg, #27ae60 0%, #219653 100%)",
        "boxShadow": "0 4px 15px rgba(39, 174, 96, 0.3)",
    }
    
    cancel_button_style = {
        **primary_button_style,
        "background": "linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%)",
        "boxShadow": "0 4px 15px rgba(149, 165, 166, 0.3)",
    }

    return html.Div([
        dcc.Store(id='session-mode', storage_type='session'),
        dcc.Interval(id='redirect-interval', interval=1000, n_intervals=0, disabled=True),
        dcc.Store(id='simulation-state', data=None),
        dcc.Store(id="button-style-store", data={
            "primary_button": primary_button_style,
            "active_button": active_button_style,
            "confirm_button": confirm_button_style,
            "cancel_button": cancel_button_style
        }),
        
        # Background overlay
        html.Div(style={
            "position": "fixed",
            "top": 0,
            "left": 0,
            "width": "100%",
            "height": "100%",
            "backgroundImage": "url('https://www.procobot.com/wp-content/uploads/2019/10/do-ofertymirek100.png')",
            "backgroundSize": "cover",
            "backgroundRepeat": "no-repeat",
            "backgroundPosition": "center",
            "backgroundAttachment": "fixed",
            "opacity": "0.1",
            "zIndex": "-1"
        }),
        
        dbc.Container([
            # Header
            dbc.Row([
                dbc.Col(
                    html.Div([
                        html.H1(
                            "WELCOME TO THE",
                            className="text-center mb-0",
                            style={
                                "fontFamily": "Arial, sans-serif",
                                "color": "#2c3e50",
                                "fontWeight": "300",
                                "fontSize": "32px",
                                "letterSpacing": "2px"
                            }
                        ),
                        html.H2(
                            "MiR100 OPTIONS DASHBOARD",
                            className="text-center mb-0",
                            style={
                                "fontFamily": "Arial, sans-serif",
                                "background": "linear-gradient(45deg, #3498db, #2980b9)",
                                "backgroundClip": "text",
                                "-webkit-background-clip": "text",
                                "color": "transparent",
                                "fontWeight": "bold",
                                "fontSize": "40px",
                                "letterSpacing": "3px",
                                "textShadow": "2px 2px 4px rgba(0,0,0,0.1)",
                            }
                        ),
                        html.Hr(style={
                            "width": "50%",
                            "margin": "20px auto",
                            "border": "2px solid #3498db",
                            "borderRadius": "5px",
                        })
                    ]),
                    width=12
                )
            ], justify="center", align="center", style={"marginBottom": "30px", "marginTop": "20px"}),
            
            # Main content cards
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-desktop", style={
                            "fontSize": "64px",
                            "color": "#3498db",
                            "marginBottom": "20px"
                        }),
                        html.H3(
                            "Simulation Mode",
                            className="text-center",
                            style={
                                "fontFamily": "Arial, sans-serif",
                                "color": "#2c3e50",
                                "fontWeight": "600",
                                "fontSize": "20px",
                                "marginBottom": "15px"
                            }
                        ),
                        html.P(
                            "Explore the MiR100 in a simulated environment with advanced features and real-time monitoring.",
                            className="text-center",
                            style={
                                "fontFamily": "Arial, sans-serif",
                                "color": "#7f8c8d",
                                "fontSize": "14px",
                                "lineHeight": "1.6",
                                "marginBottom": "25px"
                            }
                        ),
                        html.Button(
                            "SIMULATION",
                            id="btn-simulation",
                            n_clicks=0,
                            className="btn d-block mx-auto",
                            style=primary_button_style
                        )
                    ], className="card-hover text-center", style={
                        "background": "linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(233, 236, 239, 0.95) 100%)",
                        "borderRadius": "20px",
                        "padding": "40px 30px",
                        "margin": "10px",
                        "boxShadow": "0 8px 32px rgba(0,0,0,0.1)",
                        "border": "1px solid rgba(255,255,255,0.2)",
                        "minHeight": "350px",
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "center"
                    })
                ], md=5),
                
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-robot", style={
                            "fontSize": "64px",
                            "color": "#e74c3c",
                            "marginBottom": "20px"
                        }),
                        html.H3(
                            "Real Model Mode",
                            className="text-center",
                            style={
                                "fontFamily": "Arial, sans-serif",
                                "color": "#2c3e50",
                                "fontWeight": "600",
                                "fontSize": "20px",
                                "marginBottom": "15px"
                            }
                        ),
                        html.P(
                            "Connect and interact with the real MiR100 robot for live operations and control.",
                            className="text-center",
                            style={
                                "fontFamily": "Arial, sans-serif",
                                "color": "#7f8c8d",
                                "fontSize": "14px",
                                "lineHeight": "1.6",
                                "marginBottom": "25px"
                            }
                        ),
                        html.Button(
                            "REAL MODEL",
                            id="btn-real-model",
                            n_clicks=0,
                            className="btn d-block mx-auto",
                            style=primary_button_style
                        )
                    ], className="card-hover text-center", style={
                        "background": "linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(233, 236, 239, 0.95) 100%)",
                        "borderRadius": "20px",
                        "padding": "40px 30px",
                        "margin": "10px",
                        "boxShadow": "0 8px 32px rgba(0,0,0,0.1)",
                        "border": "1px solid rgba(255,255,255,0.2)",
                        "minHeight": "350px",
                        "display": "flex",
                        "flexDirection": "column",
                        "justifyContent": "center"
                    }),
                    
                    # Modal
                    dbc.Modal([
                        dbc.ModalHeader(
                            html.Div([
                                html.I(className="fas fa-network-wired", style={
                                    "fontSize": "24px",
                                    "color": "#3498db",
                                    "marginRight": "10px"
                                }),
                                html.Span(
                                    "Enter Robot IP Address",
                                    style={
                                        "fontFamily": "Arial, sans-serif",
                                        "fontSize": "16px",
                                        "fontWeight": "600",
                                        "color": "#2c3e50"
                                    }
                                )
                            ]),
                            style={
                                "background": "linear-gradient(135deg, #5DADE2 0%, #4B9CCB 100%)",
                                "color": "white",
                                "borderRadius": "15px 15px 0 0",
                                "padding": "15px"
                            }
                        ),
                        dbc.ModalBody([
                            html.P(
                                "Please enter the IP address of your MiR100 robot:",
                                style={
                                    "fontFamily": "Arial, sans-serif",
                                    "color": "#7f8c8d",
                                    "fontSize": "14px",
                                    "marginBottom": "20px"
                                }
                            ),
                            dbc.Input(
                                id="input-ip",
                                type="text",
                                placeholder="Ex: 192.168.1.100",
                                style={
                                    "fontFamily": "Arial, sans-serif",
                                    "fontSize": "14px",
                                    "border": "2px solid #ecf0f1",
                                    "borderRadius": "10px",
                                    "padding": "12px 15px"
                                }
                            ),
                        ], style={"padding": "25px"}),
                        dbc.ModalFooter([
                            dbc.Button(
                                [html.I(className="fas fa-check", style={"marginRight": "8px"}), "Connect"],
                                id="confirm-ip-btn",
                                className="me-2",
                                style=confirm_button_style
                            ),
                            dbc.Button(
                                [html.I(className="fas fa-times", style={"marginRight": "8px"}), "Cancel"],
                                id="cancel-ip-btn",
                                style=cancel_button_style
                            )
                        ], style={
                            "borderTop": "1px solid #dee2e6",
                            "borderRadius": "0 0 15px 15px",
                            "padding": "15px"
                        })
                    ], id="ip-modal", is_open=False, centered=True, size="md", style={"borderRadius": "15px"}),
                    dcc.Store(id="stored-ip")
                ], md=5)
            ], justify="center", align="center", style={"minHeight": "60vh"}),
            
            # Robot image showcase
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4(
                            "MiR100 Autonomous Mobile Robot",
                            className="text-center mb-3",
                            style={
                                "fontFamily": "Arial, sans-serif",
                                "color": "#2c3e50",
                                "fontWeight": "600",
                                "fontSize": "18px"
                            }
                        ),
                        html.Img(
                            src='https://www.procobot.com/wp-content/uploads/2019/10/do-ofertymirek100.png',
                            style={
                                'maxWidth': '70%',
                                'display': 'block',
                                'margin': '0 auto',
                                'borderRadius': '15px',
                                'border': '5px solid #34495E',
                                'boxShadow': '0 8px 25px rgba(0,0,0,0.15)'
                            },
                            className="robot-image"
                        )
                    ], style={
                        "background": "linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(233, 236, 239, 0.95) 100%)",
                        "borderRadius": "20px",
                        "padding": "30px",
                        "boxShadow": "0 8px 32px rgba(0,0,0,0.1)",
                        "border": "1px solid rgba(255,255,255,0.2)"
                    })
                ], width=12)
            ], justify="center", align="center", className="mt-4")
        ], fluid=True)
    ], style={
        "minHeight": "100vh",
        "paddingTop": "30px",
        "fontFamily": "Arial, sans-serif"
    })