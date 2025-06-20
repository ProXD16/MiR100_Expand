import dash
from dash import html, dcc, callback, Input, Output, State, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

# Khởi tạo ứng dụng Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Store để lưu trữ dữ liệu
app.layout = html.Div([
    dcc.Store(id='start-positions-store', data=[]),
    dcc.Store(id='waypoints-store', data=[]),
    dcc.Store(id='goal-positions-store', data=[]),
    
    # Modal popup cho Add Start Position
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Add start position")),
        dbc.ModalBody([
            html.Label("Select position:", style={'fontWeight': 'bold', 'marginBottom': '10px'}),
            dcc.Dropdown(
                id='start-position-dropdown',
                options=[
                    {'label': 'Position A', 'value': 'A'},
                    {'label': 'Position B', 'value': 'B'},
                    {'label': 'Position C', 'value': 'C'},
                    {'label': 'Position D', 'value': 'D'},
                    {'label': 'Position E', 'value': 'E'},
                    {'label': 'Position F', 'value': 'F'},
                    {'label': 'Position G', 'value': 'G'},
                ],
                value='G',
                style={'marginBottom': '20px'}
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Submit", id="start-submit-btn", color="info", className="me-2"),
            dbc.Button("Cancel", id="start-cancel-btn", color="secondary")
        ])
    ], id="start-modal", is_open=False),
    
    # Modal popup cho Add Waypoint
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Add waypoint")),
        dbc.ModalBody([
            html.Label("Select position:", style={'fontWeight': 'bold', 'marginBottom': '10px'}),
            dcc.Dropdown(
                id='waypoint-position-dropdown',
                options=[
                    {'label': 'Waypoint 1', 'value': 'W1'},
                    {'label': 'Waypoint 2', 'value': 'W2'},
                    {'label': 'Waypoint 3', 'value': 'W3'},
                    {'label': 'Waypoint 4', 'value': 'W4'},
                    {'label': 'Waypoint 5', 'value': 'W5'},
                ],
                value='W1',
                style={'marginBottom': '20px'}
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Submit", id="waypoint-submit-btn", color="info", className="me-2"),
            dbc.Button("Cancel", id="waypoint-cancel-btn", color="secondary")
        ])
    ], id="waypoint-modal", is_open=False),
    
    # Modal popup cho Add Goal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Add goal position")),
        dbc.ModalBody([
            html.Label("Select position:", style={'fontWeight': 'bold', 'marginBottom': '10px'}),
            dcc.Dropdown(
                id='goal-position-dropdown',
                options=[
                    {'label': 'Goal A', 'value': 'GA'},
                    {'label': 'Goal B', 'value': 'GB'},
                    {'label': 'Goal C', 'value': 'GC'},
                    {'label': 'Goal D', 'value': 'GD'},
                    {'label': 'Goal E', 'value': 'GE'},
                ],
                value='GA',
                style={'marginBottom': '20px'}
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Submit", id="goal-submit-btn", color="info", className="me-2"),
            dbc.Button("Cancel", id="goal-cancel-btn", color="secondary")
        ])
    ], id="goal-modal", is_open=False),
    
    # Main content
    html.Div([
        html.Div([
            html.H2("Edit path guide positions", style={'marginBottom': '5px'}),
            html.P("Edit the path guide's positions", 
                   style={'color': '#666', 'marginBottom': '30px', 'fontSize': '14px'})
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'flex-start'}),
        
        # Top right button
        html.Div([
            dbc.Button("← Go back", color="secondary", outline=True, size="sm")
        ], style={'position': 'absolute', 'top': '20px', 'right': '20px'}),
        
        # Three columns
        html.Div([
            # Start positions column
            html.Div([
                html.H4("Start positions", style={'marginBottom': '20px', 'fontSize': '18px', 'fontWeight': '600'}),
                dbc.Button("Add start", id="add-start-btn", color="info", size="sm", className="mb-3"),
                html.Div(id="start-positions-list")
            ], className="col-md-4"),
            
            # Waypoints column
            html.Div([
                html.H4("Waypoints", style={'marginBottom': '20px', 'fontSize': '18px', 'fontWeight': '600'}),
                dbc.Button("Add waypoint", id="add-waypoint-btn", color="info", size="sm", className="mb-3"),
                html.Div(id="waypoints-list")
            ], className="col-md-4"),
            
            # Goal positions column
            html.Div([
                html.H4("Goal positions", style={'marginBottom': '20px', 'fontSize': '18px', 'fontWeight': '600'}),
                dbc.Button("Add goal", id="add-goal-btn", color="info", size="sm", className="mb-3"),
                html.Div(id="goal-positions-list")
            ], className="col-md-4")
        ], className="row")
        
    ], style={
        'padding': '30px',
        'backgroundColor': 'white',
        'borderRadius': '8px',
        'boxShadow': '0 2px 10px rgba(0,0,0,0.1)',
        'margin': '20px',
        'position': 'relative'
    })
], style={'backgroundColor': '#f5f5f5', 'minHeight': '100vh', 'padding': '20px'})

# Callbacks for modal controls
@app.callback(
    Output("start-modal", "is_open"),
    [Input("add-start-btn", "n_clicks"), Input("start-submit-btn", "n_clicks"), Input("start-cancel-btn", "n_clicks")],
    [State("start-modal", "is_open")]
)
def toggle_start_modal(n_add, n_submit, n_cancel, is_open):
    if n_add or n_submit or n_cancel:
        return not is_open
    return is_open

@app.callback(
    Output("waypoint-modal", "is_open"),
    [Input("add-waypoint-btn", "n_clicks"), Input("waypoint-submit-btn", "n_clicks"), Input("waypoint-cancel-btn", "n_clicks")],
    [State("waypoint-modal", "is_open")]
)
def toggle_waypoint_modal(n_add, n_submit, n_cancel, is_open):
    if n_add or n_submit or n_cancel:
        return not is_open
    return is_open

@app.callback(
    Output("goal-modal", "is_open"),
    [Input("add-goal-btn", "n_clicks"), Input("goal-submit-btn", "n_clicks"), Input("goal-cancel-btn", "n_clicks")],
    [State("goal-modal", "is_open")]
)
def toggle_goal_modal(n_add, n_submit, n_cancel, is_open):
    if n_add or n_submit or n_cancel:
        return not is_open
    return is_open

# Callbacks for adding positions
@app.callback(
    Output('start-positions-store', 'data'),
    Input('start-submit-btn', 'n_clicks'),
    State('start-position-dropdown', 'value'),
    State('start-positions-store', 'data')
)
def add_start_position(n_clicks, position, current_data):
    if n_clicks and position:
        if position not in current_data:
            current_data.append(position)
    return current_data

@app.callback(
    Output('waypoints-store', 'data'),
    Input('waypoint-submit-btn', 'n_clicks'),
    State('waypoint-position-dropdown', 'value'),
    State('waypoints-store', 'data')
)
def add_waypoint(n_clicks, position, current_data):
    if n_clicks and position:
        if position not in current_data:
            current_data.append(position)
    return current_data

@app.callback(
    Output('goal-positions-store', 'data'),
    Input('goal-submit-btn', 'n_clicks'),
    State('goal-position-dropdown', 'value'),
    State('goal-positions-store', 'data')
)
def add_goal_position(n_clicks, position, current_data):
    if n_clicks and position:
        if position not in current_data:
            current_data.append(position)
    return current_data

# Callbacks for displaying lists
@app.callback(
    Output('start-positions-list', 'children'),
    Input('start-positions-store', 'data')
)
def update_start_positions_list(data):
    if not data:
        return html.P("No start positions added", style={'color': '#999', 'fontStyle': 'italic'})
    
    return [
        dbc.Card([
            dbc.CardBody([
                html.Span(f"Position {pos}", style={'fontWeight': '500'}),
                dbc.Button("×", color="link", size="sm", style={'float': 'right', 'padding': '0', 'color': '#dc3545'})
            ])
        ], style={'marginBottom': '8px', 'border': '1px solid #e0e0e0'}) 
        for pos in data
    ]

@app.callback(
    Output('waypoints-list', 'children'),
    Input('waypoints-store', 'data')
)
def update_waypoints_list(data):
    if not data:
        return html.P("No waypoints added", style={'color': '#999', 'fontStyle': 'italic'})
    
    return [
        dbc.Card([
            dbc.CardBody([
                html.Span(f"Waypoint {pos}", style={'fontWeight': '500'}),
                dbc.Button("×", color="link", size="sm", style={'float': 'right', 'padding': '0', 'color': '#dc3545'})
            ])
        ], style={'marginBottom': '8px', 'border': '1px solid #e0e0e0'}) 
        for pos in data
    ]

@app.callback(
    Output('goal-positions-list', 'children'),
    Input('goal-positions-store', 'data')
)
def update_goal_positions_list(data):
    if not data:
        return html.P("No goal positions added", style={'color': '#999', 'fontStyle': 'italic'})
    
    return [
        dbc.Card([
            dbc.CardBody([
                html.Span(f"Goal {pos}", style={'fontWeight': '500'}),
                dbc.Button("×", color="link", size="sm", style={'float': 'right', 'padding': '0', 'color': '#dc3545'})
            ])
        ], style={'marginBottom': '8px', 'border': '1px solid #e0e0e0'}) 
        for pos in data
    ]

if __name__ == '__main__':
    app.run(debug=True)