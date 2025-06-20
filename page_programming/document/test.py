import dash
from dash import dcc, html, Input, Output, callback, State
import dash_bootstrap_components as dbc
from datetime import datetime

# Khởi tạo ứng dụng Dash với theme hiện đại
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
app.config.suppress_callback_exceptions = True

# Custom CSS styles
custom_styles = {
    'sidebar': {
        'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'minHeight': '100vh',
        'padding': '2rem 1rem',
        'borderRadius': '0 20px 20px 0',
        'boxShadow': '0 10px 30px rgba(0,0,0,0.1)'
    },
    'main_content': {
        'background': 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        'minHeight': '100vh',
        'padding': '2rem'
    },
    'card_modern': {
        'borderRadius': '15px',
        'border': 'none',
        'boxShadow': '0 8px 25px rgba(0,0,0,0.1)',
        'transition': 'all 0.3s ease',
        'background': 'rgba(255,255,255,0.95)',
        'backdropFilter': 'blur(10px)'
    },
    'gradient_button': {
        'background': 'linear-gradient(45deg, #FF6B6B, #4ECDC4)',
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
    }
}

# Dữ liệu mẫu cho các chương trình
programs_data = [
    {"name": "AI Vision System", "description": "Computer vision processing", "status": "active", "progress": 85, "category": "AI"},
    {"name": "Web Scraper Pro", "description": "Advanced data extraction", "status": "active", "progress": 92, "category": "Web"},
    {"name": "Database Manager", "description": "SQL optimization tools", "status": "active", "progress": 78, "category": "Database"},
    {"name": "API Gateway", "description": "Microservices routing", "status": "active", "progress": 65, "category": "Backend"},
    {"name": "Mobile App Core", "description": "Cross-platform framework", "status": "active", "progress": 45, "category": "Mobile"},
    {"name": "Security Scanner", "description": "Vulnerability assessment", "status": "active", "progress": 88, "category": "Security"},
    {"name": "Cloud Deployer", "description": "Automated deployment", "status": "inactive", "progress": 30, "category": "DevOps"},
    {"name": "Data Analytics", "description": "Business intelligence", "status": "inactive", "progress": 55, "category": "Analytics"},
    {"name": "Blockchain Wallet", "description": "Cryptocurrency management", "status": "inactive", "progress": 25, "category": "Blockchain"},
    {"name": "Chat Bot Engine", "description": "Natural language processing", "status": "active", "progress": 72, "category": "AI"},
]

def create_program_card(program):
    """Tạo card hiện đại cho mỗi chương trình"""
    status_color = "#4ECDC4" if program["status"] == "active" else "#95A5A6"
    category_colors = {
        "AI": "#E74C3C", "Web": "#3498DB", "Database": "#F39C12", 
        "Backend": "#9B59B6", "Mobile": "#1ABC9C", "Security": "#E67E22",
        "DevOps": "#34495E", "Analytics": "#16A085", "Blockchain": "#F1C40F"
    }
    
    category_color = category_colors.get(program["category"], "#BDC3C7")
    
    # Icon theo category
    category_icons = {
        "AI": "fas fa-brain", "Web": "fas fa-globe", "Database": "fas fa-database",
        "Backend": "fas fa-server", "Mobile": "fas fa-mobile-alt", "Security": "fas fa-shield-alt",
        "DevOps": "fas fa-cloud", "Analytics": "fas fa-chart-line", "Blockchain": "fas fa-link"
    }
    
    icon = category_icons.get(program["category"], "fas fa-code")
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className=f"{icon} fa-2x", style={"color": category_color, "marginRight": "15px"}),
                        html.Div([
                            html.H5(program["name"], className="mb-1", style={"fontWeight": "600"}),
                            html.P(program["description"], className="text-muted mb-2", style={"fontSize": "0.9rem"}),
                            dbc.Badge(program["category"], color="light", text_color="dark", className="me-2"),
                            dbc.Badge(f'{program["progress"]}%', color="info", className="me-2"),
                            dbc.Progress(value=program["progress"], color="info", className="mt-2", style={"height": "6px"})
                        ], style={"flex": "1"})
                    ], className="d-flex align-items-center")
                ], width=8),
                dbc.Col([
                    html.Div([
                        dbc.Button([html.I(className="fas fa-edit")], 
                                 color="primary", size="sm", className="me-1", outline=True,
                                 style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                        dbc.Button([html.I(className="fas fa-trash")], 
                                 color="danger", size="sm", className="me-1", outline=True,
                                 style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                        dbc.Button([html.I(className="fas fa-play")], 
                                 color="success", size="sm", outline=True,
                                 style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                    ], className="d-flex")
                ], width=4, className="text-end d-flex align-items-center justify-content-end")
            ])
        ])
    ], style=custom_styles['program_card'], className="hover-shadow")

def create_main_layout():
    """Layout chính với thiết kế hiện đại"""
    return html.Div([
        dbc.Row([
            # Sidebar
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-code fa-3x mb-3", style={"color": "white"}),
                        html.H3("Programming", className="text-white mb-4", style={"fontWeight": "300"}),
                        html.P("Manage your development projects", className="text-white-50 mb-4")
                    ], className="text-center mb-4"),
                    
                    dbc.Nav([
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-home me-2"), "Dashboard"], 
                                              href="#", active=True, className="text-white mb-2",
                                              style={"borderRadius": "10px", "padding": "10px 15px"})),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-project-diagram me-2"), "Projects"], 
                                              href="#", className="text-white-75 mb-2",
                                              style={"borderRadius": "10px", "padding": "10px 15px"})),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-cog me-2"), "Settings"], 
                                              href="#", className="text-white-75 mb-2",
                                              style={"borderRadius": "10px", "padding": "10px 15px"})),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-chart-bar me-2"), "Analytics"], 
                                              href="#", className="text-white-75 mb-2",
                                              style={"borderRadius": "10px", "padding": "10px 15px"}))
                    ], vertical=True, className="mb-4"),
                    
                    html.Div([
                        html.H6("Quick Stats", className="text-white mb-3"),
                        dbc.Card([
                            dbc.CardBody([
                                html.H4("7", className="text-primary mb-1"),
                                html.P("Active Projects", className="mb-0", style={"fontSize": "0.8rem"})
                            ])
                        ], style={"borderRadius": "10px", "background": "rgba(255,255,255,0.1)", "border": "none"}),
                    ])
                ], style=custom_styles['sidebar'])
            ], width=3),
            
            # Main content
            dbc.Col([
                html.Div([
                    # Header section
                    dbc.Row([
                        dbc.Col([
                            html.H1("Development Dashboard", 
                                   style={"fontWeight": "300", "color": "#2C3E50", "marginBottom": "5px"}),
                            html.P("Manage and monitor your programming projects", 
                                  className="text-muted mb-4", style={"fontSize": "1.1rem"})
                        ], width=8),
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-plus me-2"),
                                "Create Program"
                            ], id="create-program-btn", 
                            style=custom_styles['gradient_button'],
                            className="float-end")
                        ], width=4)
                    ], className="mb-4"),
                    
                    # Stats cards
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.Div([
                                        html.I(className="fas fa-rocket fa-2x", style={"color": "#3498DB"}),
                                        html.Div([
                                            html.H3("7", className="mb-0", style={"fontWeight": "bold"}),
                                            html.P("Active Programs", className="text-muted mb-0")
                                        ], className="ms-3")
                                    ], className="d-flex align-items-center")
                                ])
                            ], style=custom_styles['card_modern'])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.Div([
                                        html.I(className="fas fa-pause-circle fa-2x", style={"color": "#E74C3C"}),
                                        html.Div([
                                            html.H3("3", className="mb-0", style={"fontWeight": "bold"}),
                                            html.P("Paused Programs", className="text-muted mb-0")
                                        ], className="ms-3")
                                    ], className="d-flex align-items-center")
                                ])
                            ], style=custom_styles['card_modern'])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.Div([
                                        html.I(className="fas fa-chart-line fa-2x", style={"color": "#2ECC71"}),
                                        html.Div([
                                            html.H3("68%", className="mb-0", style={"fontWeight": "bold"}),
                                            html.P("Avg Progress", className="text-muted mb-0")
                                        ], className="ms-3")
                                    ], className="d-flex align-items-center")
                                ])
                            ], style=custom_styles['card_modern'])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.Div([
                                        html.I(className="fas fa-clock fa-2x", style={"color": "#F39C12"}),
                                        html.Div([
                                            html.H3("24/7", className="mb-0", style={"fontWeight": "bold"}),
                                            html.P("System Status", className="text-muted mb-0")
                                        ], className="ms-3")
                                    ], className="d-flex align-items-center")
                                ])
                            ], style=custom_styles['card_modern'])
                        ], width=3)
                    ], className="mb-4"),
                    
                    # Filters and controls
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Program Management", className="mb-3", style={"fontWeight": "600"}),
                                    dbc.Row([
                                        dbc.Col([
                                            html.Label("Filter by status:", className="form-label", style={"fontWeight": "500"}),
                                            dcc.Dropdown(
                                                id="program-filter",
                                                options=[
                                                    {"label": "🚀 All programs", "value": "all"},
                                                    {"label": "✅ Active programs", "value": "active"},
                                                    {"label": "⏸️ Inactive programs", "value": "inactive"}
                                                ],
                                                value="all",
                                                style={"borderRadius": "10px"}
                                            )
                                        ], width=6),
                                        dbc.Col([
                                            html.Label("Quick actions:", className="form-label", style={"fontWeight": "500"}),
                                            html.Div([
                                                dbc.Button("🏷️ Manage Tags", color="outline-primary", size="sm", className="me-2"),
                                                dbc.Button("📊 Export Data", color="outline-secondary", size="sm")
                                            ])
                                        ], width=6)
                                    ])
                                ])
                            ], style=custom_styles['card_modern'])
                        ], width=8),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader([
                                    html.H5([html.I(className="fas fa-list-alt me-2"), "Program Queue"], 
                                           className="mb-0", style={"fontWeight": "600"})
                                ], style={"background": "linear-gradient(45deg, #667eea, #764ba2)", "color": "white", "border": "none"}),
                                dbc.CardBody([
                                    html.Div([
                                        html.I(className="fas fa-video fa-lg me-2", style={"color": "#2ECC71"}),
                                        html.Span("Cameras ready to stream", style={"color": "#2ECC71", "fontWeight": "500"})
                                    ], className="mb-3"),
                                    html.P("🔄 Queue is empty - Ready for new programs", 
                                          className="text-muted", style={"fontStyle": "italic"})
                                ])
                            ], style=custom_styles['card_modern'])
                        ], width=4)
                    ], className="mb-4"),
                    
                    # Programs list
                    html.Div(id="programs-list")
                ], style=custom_styles['main_content'])
            ], width=9)
        ], className="g-0")
    ])

def create_program_editor_layout():
    """Layout cho trang chỉnh sửa chương trình với thiết kế hiện đại"""
    return html.Div([
        # Header với gradient background
        html.Div([
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.H2([
                            html.I(className="fas fa-code me-3"),
                            "Program Editor"
                        ], className="text-white mb-2", style={"fontWeight": "300"}),
                        html.P("Advanced programming interface", className="text-white-50")
                    ], width=6),
                    dbc.Col([
                        dbc.ButtonGroup([
                            dbc.Button([html.I(className="fas fa-arrow-left me-2"), "Go Back"], 
                                     id="go-back-btn", color="light", outline=True),
                            dbc.Button([html.I(className="fas fa-save me-2"), "Save"], 
                                     color="success"),
                            dbc.Button([html.I(className="fas fa-copy me-2"), "Save As"], 
                                     color="info"),
                            dbc.Button([html.I(className="fas fa-trash me-2"), "Delete"], 
                                     color="danger")
                        ], className="float-end")
                    ], width=6)
                ])
            ])
        ], style={
            "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            "padding": "2rem 0",
            "marginBottom": "2rem"
        }),
        
        dbc.Container([
            # Navigation tabs
            dbc.Card([
                dbc.CardHeader([
                    dbc.Nav([
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-walking me-2"), "Move"], 
                                              active=True, className="fw-bold")),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-battery-full me-2"), "Battery"])),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-brain me-2"), "Logic"])),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-exclamation-triangle me-2"), "Error Handling"])),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-lightbulb me-2"), "Sound/Light"])),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-microchip me-2"), "PLC"])),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-envelope me-2"), "Email"])),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-plug me-2"), "I/O Module"])),
                        dbc.NavItem(dbc.NavLink([html.I(className="fas fa-tasks me-2"), "Missions"], 
                                              className="text-primary fw-bold")),
                    ], pills=True)
                ], style={"background": "#f8f9fa"})
            ], style=custom_styles['card_modern'], className="mb-4"),
            
            # Program details
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-star fa-2x me-3", style={"color": "#F39C12"}),
                                html.Div([
                                    html.H3("AI Vision System ⭐", className="mb-1", style={"fontWeight": "600"}),
                                    html.P("Advanced computer vision processing program", className="text-muted")
                                ])
                            ], className="d-flex align-items-center")
                        ])
                    ], style=custom_styles['card_modern'])
                ], width=12)
            ], className="mb-4"),
            
            # Loop programming section
            dbc.Card([
                dbc.CardHeader([
                    dbc.Row([
                        dbc.Col([
                            html.H5([
                                html.I(className="fas fa-sync-alt me-2", style={"color": "#3498DB"}),
                                "Loop Configuration"
                            ], className="mb-0", style={"fontWeight": "600"})
                        ], width=8),
                        dbc.Col([
                            dbc.ButtonGroup([
                                dbc.Button([html.I(className="fas fa-copy")], color="light", size="sm"),
                                dbc.Button([html.I(className="fas fa-question")], color="light", size="sm"),
                                dbc.Button([html.I(className="fas fa-cog")], color="light", size="sm")
                            ])
                        ], width=4, className="text-end")
                    ])
                ], style={"background": "linear-gradient(45deg, #e3f2fd, #bbdefb)"}),
                
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Loop Type:", className="form-label fw-bold"),
                            dbc.InputGroup([
                                dbc.InputGroupText(html.I(className="fas fa-infinity")),
                                dbc.Input(value="endless", style={"fontWeight": "500"}),
                                dbc.InputGroupText("iterations")
                            ])
                        ], width=6),
                        dbc.Col([
                            html.Label("Execution Mode:", className="form-label fw-bold"),
                            dcc.Dropdown(
                                options=[
                                    {"label": "🔄 Continuous", "value": "continuous"},
                                    {"label": "⏯️ Step-by-step", "value": "step"},
                                    {"label": "🎯 Conditional", "value": "conditional"}
                                ],
                                value="continuous"
                            )
                        ], width=6)
                    ], className="mb-4"),
                    
                    html.H6("Movement Commands:", className="mb-3", style={"fontWeight": "600"}),
                    
                    # Movement commands với animation
                    html.Div([
                        dbc.Card([
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        html.Div([
                                            html.I(className="fas fa-map-marker-alt fa-lg me-3", 
                                                  style={"color": "#E74C3C"}),
                                            html.Span("Move to ", style={"fontSize": "1.1rem"}),
                                            dbc.Badge("P1", color="danger", className="me-2", 
                                                    style={"fontSize": "1rem", "padding": "8px 12px"}),
                                            html.Small("Position: (100, 200, 0)", className="text-muted")
                                        ], className="d-flex align-items-center")
                                    ], width=9),
                                    dbc.Col([
                                        dbc.ButtonGroup([
                                            dbc.Button([html.I(className="fas fa-edit")], 
                                                     color="primary", size="sm", outline=True),
                                            dbc.Button([html.I(className="fas fa-cog")], 
                                                     color="secondary", size="sm", outline=True)
                                        ])
                                    ], width=3, className="text-end")
                                ])
                            ])
                        ], color="danger", outline=True, className="mb-3", 
                           style={"borderWidth": "2px", "borderRadius": "12px"}),
                        
                        dbc.Card([
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        html.Div([
                                            html.I(className="fas fa-map-marker-alt fa-lg me-3", 
                                                  style={"color": "#2ECC71"}),
                                            html.Span("Move to ", style={"fontSize": "1.1rem"}),
                                            dbc.Badge("P2", color="success", className="me-2", 
                                                    style={"fontSize": "1rem", "padding": "8px 12px"}),
                                            html.Small("Position: (150, 300, 0)", className="text-muted")
                                        ], className="d-flex align-items-center")
                                    ], width=9),
                                    dbc.Col([
                                        dbc.ButtonGroup([
                                            dbc.Button([html.I(className="fas fa-edit")], 
                                                     color="primary", size="sm", outline=True),
                                            dbc.Button([html.I(className="fas fa-cog")], 
                                                     color="secondary", size="sm", outline=True)
                                        ])
                                    ], width=3, className="text-end")
                                ])
                            ])
                        ], color="success", outline=True, className="mb-3", 
                           style={"borderWidth": "2px", "borderRadius": "12px"}),
                        
                        dbc.Card([
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        html.Div([
                                            html.I(className="fas fa-map-marker-alt fa-lg me-3", 
                                                  style={"color": "#3498DB"}),
                                            html.Span("Move to ", style={"fontSize": "1.1rem"}),
                                            dbc.Badge("P3", color="primary", className="me-2", 
                                                    style={"fontSize": "1rem", "padding": "8px 12px"}),
                                            html.Small("Position: (200, 100, 0)", className="text-muted")
                                        ], className="d-flex align-items-center")
                                    ], width=9),
                                    dbc.Col([
                                        dbc.ButtonGroup([
                                            dbc.Button([html.I(className="fas fa-edit")], 
                                                     color="primary", size="sm", outline=True),
                                            dbc.Button([html.I(className="fas fa-cog")], 
                                                     color="secondary", size="sm", outline=True)
                                        ])
                                    ], width=3, className="text-end")
                                ])
                            ])
                        ], color="primary", outline=True, className="mb-3", 
                           style={"borderWidth": "2px", "borderRadius": "12px"}),
                        
                        # Add new command button
                        dbc.Button([
                            html.I(className="fas fa-plus me-2"),
                            "Add New Command"
                        ], color="light", outline=True, className="w-100", 
                           style={"borderStyle": "dashed", "borderWidth": "2px", "padding": "15px"})
                    ])
                ])
            ], style=custom_styles['card_modern'])
        ])
    ])

# Layout chính của ứng dụng
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content"),
    dcc.Store(id="page-state", data={"current_page": "main"})
])

@callback(
    Output("programs-list", "children"),
    Input("program-filter", "value")
)
def update_programs_list(filter_value):
    """Cập nhật danh sách chương trình dựa trên filter"""
    if filter_value == "all":
        filtered_programs = programs_data
    else:
        filtered_programs = [p for p in programs_data if p["status"] == filter_value]
    
    return [create_program_card(program) for program in filtered_programs]

@callback(
    [Output("page-content", "children"),
     Output("page-state", "data")],
    [Input("url", "pathname")],
    [State("page-state", "data")],
    prevent_initial_call=False
)
def display_page(pathname, page_state):
    """Hiển thị trang chính"""
    return create_main_layout(), {"current_page": "main"}

@callback(
    [Output("page-content", "children", allow_duplicate=True),
     Output("page-state", "data", allow_duplicate=True)],
    [Input("create-program-btn", "n_clicks")],
    prevent_initial_call=True
)
def go_to_editor(n_clicks):
    """Chuyển đến trang editor"""
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
    """Quay lại trang chính"""
    if n_clicks:
        return create_main_layout(), {"current_page": "main"}
    return dash.no_update, dash.no_update

if __name__ == "__main__":
    app.run(debug=True, port=1600)