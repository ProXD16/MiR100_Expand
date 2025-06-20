from dash import html
import dash_bootstrap_components as dbc

class ChangePasswordPage:
    def __init__(self):
        self.layout = html.Div([
            dbc.Container([
                dbc.Row([
                    dbc.Col(md=6, children=[
                        html.H2("Change Password", className="mb-4 text-primary"),
                        dbc.Form([
                            dbc.Row([
                                dbc.Label("New Password", html_for="new-password", width=4, className="text-info"),
                                dbc.Col(dbc.Input(type="password", id="new-password", placeholder="Enter new password"), width=8),
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Label("Confirm Password", html_for="confirm-password", width=4, className="text-info"),
                                dbc.Col(dbc.Input(type="password", id="confirm-password", placeholder="Confirm new password"), width=8),
                            ], className="mb-3"),
                            dbc.Button("Update Password", color="success", id="update-password-button"),
                            html.Div(id="password-status", className="mt-3"),
                        ]),
                    ], style={"backgroundColor": "#f8f9fa", "padding": "20px", "border-radius": "10px"}),
                ], justify="center", align="center", style={"minHeight": "80vh"}),
            ], fluid=True)
        ], style={"backgroundColor": "#e9ecef", "minHeight": "100vh"})