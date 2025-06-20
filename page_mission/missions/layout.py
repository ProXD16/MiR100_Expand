from dash import html, dcc
import dash_bootstrap_components as dbc

def create_mission_row(mission):
    mission_id = mission.get("guid", "")
    return html.Tr([
        html.Td(mission_id, style={'padding': '12px', 'verticalAlign': 'middle', 'fontWeight': '500'}),
        html.Td(mission.get("name", ""), style={'padding': '12px', 'verticalAlign': 'middle'}),
        html.Td([
            html.Button(
                html.I(className="fas fa-check"),
                id={"type": "addmission-btn", "index": mission_id},
                className="btn btn-success btn-sm",
                style={
                    "marginLeft": "8px",
                    "borderRadius": "8px",
                    "padding": "8px 12px",
                    "border": "none",
                    "boxShadow": "0 2px 8px rgba(40, 167, 69, 0.3)",
                    "transition": "all 0.3s ease"
                },
            ),
            html.Button(
                html.I(className="fas fa-eye"),
                id = "viewmission-btn",
                className="btn btn-primary btn-sm",
                style={
                    "marginLeft": "8px",
                    "borderRadius": "8px",
                    "padding": "8px 12px",
                    "border": "none",
                    "boxShadow": "0 2px 8px rgba(0, 123, 255, 0.3)",
                    "transition": "all 0.3s ease"
                },
            ),
            html.Button(
                html.I(className="fas fa-times"),
                id = "stopmission-btn",
                className="btn btn-danger btn-sm",
                style={
                    "marginLeft": "8px",
                    "borderRadius": "8px",
                    "padding": "8px 12px",
                    "border": "none",
                    "boxShadow": "0 2px 8px rgba(220, 53, 69, 0.3)",
                    "transition": "all 0.3s ease"
                },
            ),
        ], style={'padding': '12px', 'verticalAlign': 'middle'}),
    ], style={'borderBottom': '1px solid #f0f0f0'})

def mission_queue_layout():
    # Enhanced button styles
    primary_button_style = {
        'padding': '12px 24px',
        'fontSize': '14px',
        'fontWeight': '600',
        'borderRadius': '10px',
        'border': 'none',
        'transition': 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        'boxShadow': '0 4px 12px rgba(0, 123, 255, 0.3)',
        'background': 'linear-gradient(135deg, #007bff 0%, #0056b3 100%)',
        'color': 'white',
        'cursor': 'pointer',
        'textTransform': 'uppercase',
        'letterSpacing': '0.5px',
    }
    
    secondary_button_style = {
        'padding': '10px 20px',
        'fontSize': '13px',
        'fontWeight': '500',
        'borderRadius': '8px',
        'border': '2px solid #e9ecef',
        'transition': 'all 0.3s ease',
        'backgroundColor': 'white',
        'color': '#495057',
        'cursor': 'pointer',
        'marginTop': '12px'
    }
    
    # Card styles
    card_style = {
        'backgroundColor': 'white',
        'borderRadius': '16px',
        'padding': '24px',
        'boxShadow': '0 8px 32px rgba(0, 0, 0, 0.08)',
        'border': '1px solid #f0f0f0',
        'marginBottom': '24px',
        'transition': 'transform 0.3s ease, box-shadow 0.3s ease',
        'height': 'fit-content'
    }
    
    # Table container style
    table_container_style = {
        "maxHeight": "450px", 
        "overflowY": "auto", 
        "border": "1px solid #e9ecef",
        "borderRadius": "12px",
        "backgroundColor": "white",
        "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.05)"
    }
    
    # Table header style
    table_header_style = {
        'backgroundColor': '#f8f9fa',
        'borderBottom': '2px solid #e9ecef',
        'position': 'sticky',
        'top': '0',
        'zIndex': '10'
    }
    
    return dbc.Container([
        # Enhanced Header Section
        html.Div([
            html.Div([
                html.H1("Mission Control Center", 
                       style={
                           'fontSize': '36px', 
                           'fontWeight': '700',
                           'background': 'linear-gradient(135deg, #2c3e50 0%, #3498db 100%)',
                           'backgroundClip': 'text',
                           'WebkitBackgroundClip': 'text',
                           'WebkitTextFillColor': 'transparent',
                           'marginBottom': '8px',
                           'textAlign': 'center'
                       }),
                html.P("Orchestrate and manage your robotic missions with precision", 
                       style={
                           'color': '#7f8c8d', 
                           'fontSize': '18px',
                           'textAlign': 'center',
                           'marginBottom': '40px',
                           'fontWeight': '400'
                       })
            ], style={'textAlign': 'center', 'marginBottom': '40px'})
        ]),
        
        # Mission Control Panel
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-cogs", 
                                   style={'color': '#3498db', 'fontSize': '20px', 'marginRight': '12px'}),
                            html.H4("Mission Configuration", 
                                   style={'color': '#2c3e50', 'fontWeight': '600', 'margin': '0'})
                        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
                        
                        html.Label("Show missions:", 
                                  style={'fontWeight': '600', 'color': '#34495e', 'marginBottom': '8px'}),
                        dcc.Dropdown(
                            id="mission-dropdown",
                            options=[
                                {"label": "📋 All Missions", "value": "missions"},
                            ],
                            value="missions",
                            clearable=False,
                            style={
                                "width": "100%",
                                "marginBottom": "16px",
                                "borderRadius": "8px"
                            }
                        ),
                        html.Button("✏️ Create / Edit Groups", 
                                   id="edit-groups", 
                                   style=secondary_button_style)
                    ], style=card_style)
                ], width=12),
            ], className="mb-4"),
        ]),
        
        # Main Content Area
        dbc.Row([
            # Enhanced Mission List Column
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-list-alt", 
                               style={'color': '#27ae60', 'fontSize': '20px', 'marginRight': '12px'}),
                        html.H4("Available Missions", 
                               style={'color': '#2c3e50', 'fontWeight': '600', 'margin': '0'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
                    
                    html.Div([
                        html.Table([
                            html.Thead([
                                html.Tr([
                                    html.Th("Mission ID", style={'padding': '16px', 'fontWeight': '600', 'color': '#2c3e50'}), 
                                    html.Th("Mission Name", style={'padding': '16px', 'fontWeight': '600', 'color': '#2c3e50'}), 
                                    html.Th("Actions", style={'padding': '16px', 'fontWeight': '600', 'color': '#2c3e50'})
                                ], style=table_header_style)
                            ]),
                            html.Tbody(id="mission-list-container")
                        ], className="table", style={'margin': '0', 'borderCollapse': 'separate', 'borderSpacing': '0'})
                    ], style=table_container_style)
                ], style=card_style)
            ], width=8),

            # Enhanced Mission Queue Column
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-tasks", 
                               style={'color': '#e74c3c', 'fontSize': '20px', 'marginRight': '12px'}),
                        html.H4("Active Queue", 
                               style={'color': '#2c3e50', 'fontWeight': '600', 'margin': '0'})
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
                    
                    html.Div([
                        html.Table([
                            html.Thead([
                                html.Tr([
                                    html.Th("Queue ID", style={'padding': '16px', 'fontWeight': '600', 'color': '#2c3e50'}), 
                                    html.Th("Mission", style={'padding': '16px', 'fontWeight': '600', 'color': '#2c3e50'}), 
                                    html.Th("Actions", style={'padding': '16px', 'fontWeight': '600', 'color': '#2c3e50'})
                                ], style=table_header_style)
                            ]),
                            html.Tbody(id="mission-queue-container")
                        ], className="table", style={'margin': '0', 'borderCollapse': 'separate', 'borderSpacing': '0'})
                    ], style=table_container_style),
                    
                    # Enhanced Action Buttons
                    html.Div([
                        dbc.Row([
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="fas fa-plus", style={'marginRight': '8px'}),
                                    "Create"
                                ], id="create-mission-btn", color="primary", 
                                   style={**primary_button_style, **{'width': '100%', 'marginBottom': '8px'}})
                            ], width=12),
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="fas fa-plus-circle", style={'marginRight': '8px'}),
                                    "Add to Queue"
                                ], color="warning", 
                                   style={**primary_button_style, **{
                                       'backgroundColor': '#f39c12',
                                       'boxShadow': '0 4px 12px rgba(243, 156, 18, 0.3)',
                                       'width': '100%',
                                       'marginBottom': '8px'
                                   }})
                            ], width=12),
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="fas fa-stop", style={'marginRight': '8px'}),
                                    "Stop All"
                                ], color="danger", 
                                   style={**primary_button_style, **{
                                       'backgroundColor': '#e74c3c',
                                       'boxShadow': '0 4px 12px rgba(231, 76, 60, 0.3)',
                                       'width': '100%'
                                   }})
                            ], width=12),
                        ])
                    ], style={'marginTop': '24px'}),
                    
                    html.Div(id="api-addmissions-response-message", 
                            style={
                                "marginTop": "20px",
                                "padding": "12px",
                                "borderRadius": "8px",
                                "backgroundColor": "#f8f9fa",
                                "border": "1px solid #e9ecef"
                            }),
                ], style=card_style)
            ], width=4)
        ], className="mb-4"),

        dcc.Interval(id="mission-interval", interval=5000, n_intervals=0),

        # Enhanced Modal
        dbc.Modal([
            dbc.ModalHeader([
                html.Div([
                    html.I(className="fas fa-rocket", 
                           style={'color': '#3498db', 'fontSize': '24px', 'marginRight': '12px'}),
                    html.H4("Mission Configuration", 
                           style={'color': '#2c3e50', 'fontWeight': '600', 'margin': '0'})
                ], style={'display': 'flex', 'alignItems': 'center'})
            ], style={
                'backgroundColor': '#f8f9fa',
                'borderBottom': '1px solid #e9ecef',
                'borderRadius': '16px 16px 0 0',
                'padding': '24px 32px 16px'
            }),
            
            dbc.ModalBody([
                # Mission Basic Info Section
                html.Div([
                    html.H5("📝 Basic Information", 
                           style={'color': '#2c3e50', 'fontWeight': '600', 'marginBottom': '16px'}),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Mission Name", style={'fontWeight': '600', 'color': '#34495e'}),
                            dbc.Input(id="mission-name-input", 
                                     placeholder="Enter mission name", 
                                     type="text",
                                     style={'borderRadius': '8px', 'border': '2px solid #e9ecef'}),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Mission Description", style={'fontWeight': '600', 'color': '#34495e'}),
                            dbc.Input(id="mission-desc-input", 
                                     placeholder="Enter description", 
                                     type="text",
                                     style={'borderRadius': '8px', 'border': '2px solid #e9ecef'}),
                        ], width=6),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Select Mission Group", style={'fontWeight': '600', 'color': '#34495e'}),
                            dcc.Dropdown(
                                id="mission-group-dropdown",
                                options=[],
                                placeholder="Select a group",
                                style={"width": "100%", "borderRadius": "8px"}
                            ),
                        ], width=6),
                    ], className="mb-4"),
                ], style={
                    'backgroundColor': '#f8f9fa',
                    'padding': '20px',
                    'borderRadius': '12px',
                    'marginBottom': '24px'
                }),

                html.Hr(style={'margin': '24px 0', 'border': '1px solid #e9ecef'}),

                # Actions Configuration Section
                html.Div([
                    html.H5("⚡ Action Configuration", 
                           style={'color': '#2c3e50', 'fontWeight': '600', 'marginBottom': '16px'}),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Action Type", style={'fontWeight': '600', 'color': '#34495e'}),
                            dcc.Dropdown(
                                id="action-type-dropdown",
                                options=[
                                    {"label": "🚀 Move", "value": "move"},
                                    {"label": "⏰ Wait", "value": "wait"},
                                    {"label": "🔋 Charge", "value": "charge"},
                                    {"label": "⚡ Set Digital Output", "value": "set_digital_output"}
                                ],
                                placeholder="Select an action",
                                style={"width": "100%", "borderRadius": "8px"}
                            ),
                        ], width=6),
                    ], className="mb-3"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Action Parameters (JSON format)", style={'fontWeight': '600', 'color': '#34495e'}),
                            dbc.Input(id="action-params-input", 
                                     placeholder='{"position": "some_guid", "velocity": 0.5}', 
                                     type="text",
                                     style={'borderRadius': '8px', 'border': '2px solid #e9ecef', 'fontFamily': 'monospace'}),
                        ], width=12),
                    ], className="mb-3"),

                    dbc.Button([
                        html.I(className="fas fa-plus", style={'marginRight': '8px'}),
                        "Add Action"
                    ], id="add-action-btn", color="success", 
                               style={**primary_button_style, **{
                                   'backgroundColor': '#27ae60',
                                   'boxShadow': '0 4px 12px rgba(39, 174, 96, 0.3)'
                               }}),
                    
                    html.Div(id="api-addaction-response-message", 
                            style={"marginTop": "16px", "padding": "12px", "borderRadius": "8px"}),
                ], style={
                    'backgroundColor': '#f8f9fa',
                    'padding': '20px',
                    'borderRadius': '12px',
                    'marginBottom': '24px'
                }),

                html.Hr(style={'margin': '24px 0', 'border': '1px solid #e9ecef'}),

                # Configured Actions Section
                html.Div([
                    html.H5("📋 Configured Actions", 
                           style={'color': '#2c3e50', 'fontWeight': '600', 'marginBottom': '16px'}),
                    html.Div(id="configured-actions-container", 
                            style={
                                'minHeight': '100px',
                                'backgroundColor': '#f8f9fa',
                                'borderRadius': '12px',
                                'padding': '16px',
                                'border': '2px dashed #bdc3c7'
                            })
                ])
            ], style={'backgroundColor': 'white', 'padding': '32px'}),

            dbc.ModalFooter([
                dbc.Button([
                    html.I(className="fas fa-rocket", style={'marginRight': '8px'}),
                    "Launch Mission"
                ], id="finish-mission-btn", color="primary", 
                           style={**primary_button_style, **{'marginRight': '12px'}}),
                dbc.Button([
                    html.I(className="fas fa-times", style={'marginRight': '8px'}),
                    "Close"
                ], id="close-config-btn", 
                           style={**secondary_button_style, **{'marginTop': '0', 'border': 'none', 'backgroundColor': '#95a5a6', 'color': 'white'}}),
                html.Div(id="api-finishmission-response-message", 
                        style={"marginTop": "16px", "padding": "12px", "borderRadius": "8px"}),
            ], style={
                'backgroundColor': '#f8f9fa',
                'borderTop': '1px solid #e9ecef',
                'borderRadius': '0 0 16px 16px',
                'padding': '16px 32px 24px'
            }),
        ],
        id="mission-config-modal",
        is_open=False,
        size="xl",
        backdrop=True,
        centered=True,
        style={'borderRadius': '16px', 'border': 'none', 'boxShadow': '0 20px 60px rgba(0, 0, 0, 0.15)'}),
        
    ], style={
        "background": "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
        "borderRadius": "20px", 
        "padding": "30px", 
        "boxShadow": "0 20px 60px rgba(0,0,0,0.08)",
        "minHeight": "100vh"
    })