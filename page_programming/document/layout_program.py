import dash
from dash import dcc, html, Input, Output, callback, State
import dash_bootstrap_components as dbc

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
app.config.suppress_callback_exceptions = True

# Custom styles with updated color #77B5FE
custom_styles = {
    'sidebar': {
        'background': 'linear-gradient(135deg, #77B5FE 0%, #4A90E2 100%)',
        'minHeight': '100vh',
        'padding': '2rem 1rem',
        'borderRadius': '0 20px 20px 0',
        'boxShadow': '0 10px 30px rgba(0,0,0,0.1)',
        'color': 'white'
    },
    'main_content': {
        'background': 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        'minHeight': '100vh',
        'padding': '2rem'
    },
    'card': {
        'borderRadius': '15px',
        'border': 'none',
        'boxShadow': '0 8px 25px rgba(0,0,0,0.1)',
        'transition': 'all 0.3s ease',
        'background': 'rgba(255,255,255,0.95)',
        'backdropFilter': 'blur(10px)',
        'margin': '1rem 0'
    },
    'gradient_button': {
        'background': 'linear-gradient(45deg, #77B5FE, #4A90E2)',
        'border': 'none',
        'borderRadius': '25px',
        'padding': '12px 30px',
        'color': 'white',
        'fontWeight': 'bold',
        'boxShadow': '0 4px 15px rgba(0,0,0,0.2)',
        'transition': 'all 0.3s ease'
    },
    'program_card': {
        'borderRadius': '12px',
        'border': '1px solid rgba(255,255,255,0.2)',
        'background': 'rgba(255,255,255,0.9)',
        'backdropFilter': 'blur(10px)',
        'margin': '10px 0',
        'transition': 'all 0.3s ease',
        'boxShadow': '0 4px 20px rgba(0,0,0,0.1)'
    },
    'button': {
        'borderRadius': '10px',
        'padding': '8px 15px',
        'fontSize': '0.9rem',
        'fontWeight': '500',
        'transition': 'all 0.3s ease',
        'boxShadow': '0 2px 5px rgba(0,0,0,0.1)'
    },
    'input_group': {
        'borderRadius': '10px',
        'border': '1px solid #dee2e6',
        'background': 'white',
        'padding': '5px 10px',
        'boxShadow': '0 2px 5px rgba(0,0,0,0.1)'
    }
}

# Sample programs data (keeping only the first program as 7/7)
programs_data = [
    {"name": "7/7"}
]

def create_program_card(program):
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-bullseye fa-lg me-3", style={"color": "#28a745"}),
                        html.H6(program["name"], className="mb-0", style={"fontWeight": "600", "color": "#2C3E50"})
                    ], className="d-flex align-items-center")
                ], width=8),
                dbc.Col([
                    html.Div([
                        dbc.Button([html.I(className="fas fa-edit")], color="primary", size="sm", className="me-2", outline=True, style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                        dbc.Button([html.I(className="fas fa-trash")], color="danger", size="sm", outline=True, style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                        dbc.Button([html.I(className="fas fa-play")], color="success", size="sm", outline=True, style={"borderRadius": "50%", "width": "35px", "height": "35px"})
                    ], className="d-flex justify-content-end align-items-center")
                ], width=4)
            ])
        ])
    ], style=custom_styles['program_card'], className="hover-shadow")

def create_main_layout():
    return html.Div([
        dbc.Row([
            # Main content
            dbc.Col([
                html.Div([
                    # Header
                    dbc.Row([
                        dbc.Col([
                            html.H1("Programming", style={"fontWeight": "300", "color": "#2C3E50", "marginBottom": "5px"}),
                            html.P("Create and edit programs.", className="text-muted mb-4", style={"fontSize": "1.1rem"})
                        ], width=8),
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-plus me-2"),
                                "Create program"
                            ], id="create-program-btn", style=custom_styles['gradient_button'], className="float-end")
                        ], width=4)
                    ], className="mb-4"),
                    
                    # Added "Show programs" as a static header
                    html.H5("Show programs:", className="mb-3", style={"fontWeight": "500", "color": "#2C3E50"}),
                    
                    # programs list
                    html.Div(id="programs-list")
                ], style=custom_styles['main_content'])
            ], width=9),
            
            # Sidebar (program Queue) on the right
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-list-alt fa-2x mb-3", style={"color": "white"}),
                        html.H4("program Queue", className="text-white mb-4", style={"fontWeight": "300"}),
                        html.P("Manage queued programs", className="text-white-50 mb-4")
                    ], className="text-center"),
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-video fa-lg me-2", style={"color": "#2ECC71"}),
                                # html.Span("Cameras are ready to stream", style={"color": "#2ECC71", "fontWeight": "500"})
                            ], className="mb-3"),
                            html.P("The queue contains no programs", className="text-muted", style={"fontStyle": "italic"})
                        ])
                    ], style=custom_styles['card'])
                ], style=custom_styles['sidebar'])
            ], width=3)
        ], className="g-0")
    ])

def create_program_editor_layout():
    return html.Div([
        # Header
        html.Div([
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.H2([
                            html.I(className="fas fa-code me-3"),
                            "Programming"
                        ], className="text-white mb-2", style={"fontWeight": "300"}),
                        html.P("Advanced program configuration", className="text-white-50")
                    ], width=6),
                    dbc.Col([
                        dbc.ButtonGroup([
                            dbc.Button([html.I(className="fas fa-arrow-left me-2"), "Go Back"], id="go-back-btn", color="light", outline=True),
                            dbc.Button([html.I(className="fas fa-save me-2"), "Save"], color="success"),
                            dbc.Button([html.I(className="fas fa-copy me-2"), "Save As"], color="info"),
                            dbc.Button([html.I(className="fas fa-trash me-2"), "Delete"], color="danger")
                        ], className="float-end")
                    ], width=6)
                ])
            ])
        ], style={"background": "linear-gradient(135deg, #77B5FE 0%, #4A90E2 100%)", "padding": "2rem 0", "marginBottom": "2rem"}),
        
        # Add name input field
        dbc.Row([
            dbc.Col([
                html.Label("Program Name:", style={"fontWeight": "500", "color": "#2C3E50", "marginBottom": "5px"}),
                dbc.Input(
                    id="program-name-input",
                    placeholder="Enter program name",
                    type="text",
                    style=custom_styles['input_group']
                )
            ], width=6)
        ], className="mb-4"),
        
        # Tabs
        dbc.Card([
            dbc.CardHeader([
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink([html.I(className="fas fa-walking me-2"), "Move"], active=True, className="fw-bold")),
                    dbc.NavItem(dbc.NavLink([html.I(className="fas fa-battery-full me-2"), "Battery"])),
                    dbc.NavItem(dbc.NavLink([html.I(className="fas fa-brain me-2"), "Logic"])),
                    dbc.NavItem(dbc.NavLink([html.I(className="fas fa-exclamation-triangle me-2"), "Error Handling"])),
                    dbc.NavItem(dbc.NavLink([html.I(className="fas fa-lightbulb me-2"), "Sound/Light"])),
                    dbc.NavItem(dbc.NavLink([html.I(className="fas fa-microchip me-2"), "PLC"])),
                    dbc.NavItem(dbc.NavLink([html.I(className="fas fa-envelope me-2"), "Email"])),
                    dbc.NavItem(dbc.NavLink([html.I(className="fas fa-plug me-2"), "I/O Module"])),
                    dbc.NavItem(dbc.NavLink([html.I(className="fas fa-tasks me-2"), "Programming"], className="text-primary fw-bold"))
                ], pills=True)
            ], style={"background": "#f8f9fa"})
        ], style=custom_styles['card'], className="mb-4"),
        
        # Loop Configuration
        dbc.Card([
            dbc.CardHeader([
                dbc.Row([
                    dbc.Col([
                        html.H5([html.I(className="fas fa-sync-alt me-2", style={"color": "#77B5FE"}), "Loop Configuration"], className="mb-0", style={"fontWeight": "600"})
                    ], width=8),
                    dbc.Col([
                        dbc.ButtonGroup([
                            dbc.Button([html.I(className="fas fa-copy")], color="light", size="sm"),
                            dbc.Button([html.I(className="fas fa-question")], color="light", size="sm"),
                            dbc.Button([html.I(className="fas fa-cog")], color="light", size="sm")
                        ], className="float-end")
                    ], width=4)
                ])
            ], style={"background": "linear-gradient(45deg, #e3f2fd, #77B5FE)"}),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Loop Type:", className="form-label fw-bold"),
                        dbc.InputGroup([
                            dbc.InputGroupText(html.I(className="fas fa-infinity")),
                            dbc.Input(value="endless", style={"fontWeight": "500"}),
                            dbc.InputGroupText("iterations")
                        ])
                    ], width=6)
                ], className="mb-3"),
                
                html.H6("Movement Commands:", className="mb-3", style={"fontWeight": "600"}),
                html.Div([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-map-marker-alt fa-lg me-3", style={"color": "#E74C3C"}),
                                html.Span("Move to P1", style={"fontSize": "1.1rem", "fontWeight": "500"}),
                                html.Small("Position: (100, 200, 0)", className="text-muted")
                            ], className="d-flex align-items-center")
                        ])
                    ], color="danger", outline=True, style={"borderWidth": "2px", "borderRadius": "12px"}, className="mb-2"),
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-map-marker-alt fa-lg me-3", style={"color": "#2ECC71"}),
                                html.Span("Move to P2", style={"fontSize": "1.1rem", "fontWeight": "500"}),
                                html.Small("Position: (150, 300, 0)", className="text-muted")
                            ], className="d-flex align-items-center")
                        ])
                    ], color="success", outline=True, style={"borderWidth": "2px", "borderRadius": "12px"}, className="mb-2"),
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-map-marker-alt fa-lg me-3", style={"color": "#3498DB"}),
                                html.Span("Move to P3", style={"fontSize": "1.1rem", "fontWeight": "500"}),
                                html.Small("Position: (200, 100, 0)", className="text-muted")
                            ], className="d-flex align-items-center")
                        ])
                    ], color="primary", outline=True, style={"borderWidth": "2px", "borderRadius": "12px"}, className="mb-2"),
                    dbc.Button([
                        html.I(className="fas fa-plus me-2"),
                        "Add New Command"
                    ], color="light", outline=True, className="w-100", style={"borderStyle": "dashed", "borderWidth": "2px", "padding": "15px"})
                ])
            ])
        ], style=custom_styles['card'])
    ], style=custom_styles['main_content'])

# Main app layout
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content"),
    dcc.Store(id="page-state", data={"current_page": "main"})
])

@callback(
    Output("programs-list", "children"),
    Input("url", "pathname")  # Using a dummy input since dropdown is removed
)
def update_programs_list(pathname):
    return [create_program_card(program) for program in programs_data]

@callback(
    [Output("page-content", "children"),
     Output("page-state", "data")],
    [Input("url", "pathname")],
    [State("page-state", "data")],
    prevent_initial_call=False
)
def display_page(pathname, page_state):
    return create_main_layout(), {"current_page": "main"}

@callback(
    [Output("page-content", "children", allow_duplicate=True),
     Output("page-state", "data", allow_duplicate=True)],
    [Input("create-program-btn", "n_clicks")],
    prevent_initial_call=True
)
def go_to_editor(n_clicks):
    if n_clicks:
        return create_program_editor_layout(), {"current_page": "editor"}
    return dash.no_update, dash.no_update

@callback(
    [Output("page-content", "children", allow_duplicate=True),
     Output("page-state", "data", allow_duplicate=True)],
    [Input("go-back-btn", "n_clicks")],
    prevent_initial_call=True
)
def go_back_to_main(n_clicks):
    if n_clicks:
        return create_main_layout(), {"current_page": "main"}
    return dash.no_update, dash.no_update

if __name__ == "__main__":
    app.run(debug=True, port=8050)