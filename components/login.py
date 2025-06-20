from dash import html
import dash_bootstrap_components as dbc

class LoginPage:
    def __init__(self):
        self.layout = html.Div([
            dbc.Container([
                dbc.Row([
                    dbc.Col(md=6, children=[
                        html.H2("Login", className="mb-4 text-primary"),
                        dbc.Form([
                            dbc.Row([
                                dbc.Label("Username", html_for="username", width=4, className="text-info"),
                                dbc.Col(dbc.Input(type="text", id="username", placeholder="Enter username"), width=8),
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Label("Password", html_for="password", width=4, className="text-info"),
                                dbc.Col(dbc.Input(type="password", id="password", placeholder="Enter password"), width=8),
                            ], className="mb-3"),
                            dbc.Button("Submit", color="primary", id="login-button", className="mb-3"),
                            html.Div(id="login-status", className="mt-3", style={"minHeight": "30px"}),
                        ]),
                    ], style={
                        "backgroundColor": "rgba(248, 249, 250, 0.9)",
                        "padding": "30px",
                        "border-radius": "15px",
                        "position": "relative",
                        "overflow": "hidden",
                        "box-shadow": "0 4px 15px rgba(0,0,0,0.1)"
                    }),
                ], justify="center", align="center", style={"minHeight": "80vh", "position": "relative"}),
            ], fluid=True, style={"position": "relative", "overflow": "hidden"})
        ], style={"backgroundColor": "#e9ecef", "minHeight": "100vh",
                  "backgroundImage": "url('static/mir100.png')",
                  "backgroundSize": "cover",
                  "backgroundRepeat": "no-repeat",
                  "backgroundPosition": "center",
                  })