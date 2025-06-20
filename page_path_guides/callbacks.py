import json
import os
import dash
from dash import Input, Output, State, callback, html, dcc
import dash_bootstrap_components as dbc
from datetime import datetime

# Đường dẫn đến các file JSON
POSITION_MARKER_PATH = "database_json/position_marker.json"
PATH_GUIDE_PATH = "database_json/path_guide.json"

def load_json_file(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading JSON file {file_path}: {e}")
        return []

def save_json_file(file_path, data):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving JSON file {file_path}: {e}")
        return False

def get_position_options(exclude_start=None, exclude_waypoints=None, exclude_goal=None):
    positions = load_json_file(POSITION_MARKER_PATH)
    exclude_start = exclude_start or []
    exclude_waypoints = exclude_waypoints or []
    exclude_goal = exclude_goal or []
    exclude_ids = set(exclude_start + exclude_waypoints + exclude_goal)
    return [{'label': pos['name'], 'value': pos['id']} for pos in positions if pos['id'] not in exclude_ids]

def save_path_guide_data(start_data, waypoints_data, goal_data):
    path_guide_data = {
        "start_positions": start_data,
        "waypoints": waypoints_data,
        "goal_positions": goal_data,
        "last_updated": datetime.now().isoformat()
    }
    return save_json_file(PATH_GUIDE_PATH, path_guide_data)

# Callbacks for modals
@callback(
    Output("start-modal", "is_open"),
    [Input("add-start-btn", "n_clicks"), Input("start-submit-btn", "n_clicks"), Input("start-cancel-btn", "n_clicks")],
    [State("start-modal", "is_open")]
)
def toggle_start_modal(n_add, n_submit, n_cancel, is_open):
    if n_add or n_submit or n_cancel:
        return not is_open
    return is_open

@callback(
    Output("waypoint-modal", "is_open"),
    [Input("add-waypoint-btn", "n_clicks"), Input("waypoint-submit-btn", "n_clicks"), Input("waypoint-cancel-btn", "n_clicks")],
    [State("waypoint-modal", "is_open")]
)
def toggle_waypoint_modal(n_add, n_submit, n_cancel, is_open):
    if n_add or n_submit or n_cancel:
        return not is_open
    return is_open

@callback(
    Output("goal-path-modal", "is_open"),
    [Input("add-goal-btn", "n_clicks"), Input("goal-submit-btn", "n_clicks"), Input("goal-cancel-btn", "n_clicks")],
    [State("goal-path-modal", "is_open")]
)
def toggle_goal_modal(n_add, n_submit, n_cancel, is_open):
    if n_add or n_submit or n_cancel:
        return not is_open
    return is_open

# Callbacks for dropdown options
@callback(
    Output('start-position-dropdown', 'options'),
    Input('start-modal', 'is_open'),
    State('waypoints-store', 'data'),
    State('goal-positions-store', 'data')
)
def update_start_dropdown(is_open, waypoints_data, goal_data):
    if is_open:
        return get_position_options(exclude_waypoints=waypoints_data, exclude_goal=goal_data)
    return dash.no_update

@callback(
    Output('waypoint-position-dropdown', 'options'),
    Input('waypoint-modal', 'is_open'),
    State('start-positions-store', 'data'),
    State('goal-positions-store', 'data')
)
def update_waypoint_dropdown(is_open, start_data, goal_data):
    if is_open:
        return get_position_options(exclude_start=start_data, exclude_goal=goal_data)
    return dash.no_update

@callback(
    Output('goal-position-dropdown', 'options'),
    Input('goal-path-modal', 'is_open'),
    State('start-positions-store', 'data'),
    State('waypoints-store', 'data')
)
def update_goal_dropdown(is_open, start_data, waypoints_data):
    if is_open:
        return get_position_options(exclude_start=start_data, exclude_waypoints=waypoints_data)
    return dash.no_update

# Callbacks for adding positions
@callback(
    Output('start-positions-store', 'data', allow_duplicate=True),
    Input('start-submit-btn', 'n_clicks'),
    State('start-position-dropdown', 'value'),
    State('start-positions-store', 'data'),
    State('waypoints-store', 'data'),
    State('goal-positions-store', 'data'),
    prevent_initial_call=True
)
def add_start_position(n_clicks, position, start_data, waypoints_data, goal_data):
    if n_clicks and position:
        if position not in start_data:
            start_data.append(position)
            save_path_guide_data(start_data, waypoints_data, goal_data)
    return start_data

@callback(
    Output('waypoints-store', 'data', allow_duplicate=True),
    Input('waypoint-submit-btn', 'n_clicks'),
    State('waypoint-position-dropdown', 'value'),
    State('waypoints-store', 'data'),
    State('start-positions-store', 'data'),
    State('goal-positions-store', 'data'),
    prevent_initial_call=True
)
def add_waypoint(n_clicks, position, waypoints_data, start_data, goal_data):
    if n_clicks and position:
        if position not in waypoints_data:
            waypoints_data.append(position)
            save_path_guide_data(start_data, waypoints_data, goal_data)
    return waypoints_data

@callback(
    Output('goal-positions-store', 'data', allow_duplicate=True),
    Input('goal-submit-btn', 'n_clicks'),
    State('goal-position-dropdown', 'value'),
    State('goal-positions-store', 'data'),
    State('start-positions-store', 'data'),
    State('waypoints-store', 'data'),
    prevent_initial_call=True
)
def add_goal_position(n_clicks, position, goal_data, start_data, waypoints_data):
    if n_clicks and position:
        if position not in goal_data:
            goal_data.append(position)
            save_path_guide_data(start_data, waypoints_data, goal_data)
    return goal_data

# Callbacks for deleting positions
@callback(
    Output('start-positions-store', 'data', allow_duplicate=True),
    Input({'type': 'delete-start-btn', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('start-positions-store', 'data'),
    State('waypoints-store', 'data'),
    State('goal-positions-store', 'data'),
    prevent_initial_call=True
)
def delete_start_position(n_clicks, start_data, waypoints_data, goal_data):
    if not any(n_clicks):
        return dash.no_update
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    button_id = json.loads(button_id)
    index_to_delete = button_id['index']
    
    if index_to_delete < len(start_data):
        new_data = [pos for i, pos in enumerate(start_data) if i != index_to_delete]
        save_path_guide_data(new_data, waypoints_data, goal_data)
        return new_data
    
    return start_data

@callback(
    Output('waypoints-store', 'data', allow_duplicate=True),
    Input({'type': 'delete-waypoint-btn', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('waypoints-store', 'data'),
    State('start-positions-store', 'data'),
    State('goal-positions-store', 'data'),
    prevent_initial_call=True
)
def delete_waypoint(n_clicks, waypoints_data, start_data, goal_data):
    if not any(n_clicks):
        return dash.no_update
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    button_id = json.loads(button_id)
    index_to_delete = button_id['index']
    
    if index_to_delete < len(waypoints_data):
        new_data = [pos for i, pos in enumerate(waypoints_data) if i != index_to_delete]
        save_path_guide_data(start_data, new_data, goal_data)
        return new_data
    
    return waypoints_data

@callback(
    Output('goal-positions-store', 'data', allow_duplicate=True),
    Input({'type': 'delete-goal-btn', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('goal-positions-store', 'data'),
    State('start-positions-store', 'data'),
    State('waypoints-store', 'data'),
    prevent_initial_call=True
)
def delete_goal_position(n_clicks, goal_data, start_data, waypoints_data):
    if not any(n_clicks):
        return dash.no_update
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    button_id = json.loads(button_id)
    index_to_delete = button_id['index']
    
    if index_to_delete < len(goal_data):
        new_data = [pos for i, pos in enumerate(goal_data) if i != index_to_delete]
        save_path_guide_data(start_data, waypoints_data, new_data)
        return new_data
    
    return goal_data

# Callbacks for displaying lists
@callback(
    Output('start-positions-list', 'children'),
    Input('start-positions-store', 'data')
)
def update_start_positions_list(data):
    if not data:
        return html.P("No start positions added", style={'color': '#999', 'fontStyle': 'italic'})
    
    positions = load_json_file(POSITION_MARKER_PATH)
    position_map = {pos['id']: pos for pos in positions}
    
    return [
        dbc.Card([
            dbc.CardBody([
                html.Span(f"{position_map.get(pos, {}).get('name', 'Unknown')}", style={'fontWeight': '500'}),
                dbc.Button(
                    "×", 
                    id={'type': 'delete-start-btn', 'index': i},
                    color="link", 
                    size="sm", 
                    style={'float': 'right', 'padding': '0', 'color': '#dc3545'}
                )
            ])
        ], style={'marginBottom': '8px', 'border': '1px solid #e0e0e0'}) 
        for i, pos in enumerate(data)
    ]

@callback(
    Output('waypoints-list', 'children'),
    Input('waypoints-store', 'data')
)
def update_waypoints_list(data):
    if not data:
        return html.P("No waypoints added", style={'color': '#999', 'fontStyle': 'italic'})
    
    positions = load_json_file(POSITION_MARKER_PATH)
    position_map = {pos['id']: pos for pos in positions}
    
    return [
        dbc.Card([
            dbc.CardBody([
                html.Span(f"{position_map.get(pos, {}).get('name', 'Unknown')}", style={'fontWeight': '500'}),
                dbc.Button(
                    "×", 
                    id={'type': 'delete-waypoint-btn', 'index': i},
                    color="link", 
                    size="sm", 
                    style={'float': 'right', 'padding': '0', 'color': '#dc3545'}
                )
            ])
        ], style={'marginBottom': '8px', 'border': '1px solid #e0e0e0'}) 
        for i, pos in enumerate(data)
    ]

@callback(
    Output('goal-positions-list', 'children'),
    Input('goal-positions-store', 'data')
)
def update_goal_positions_list(data):
    if not data:
        return html.P("No goal positions added", style={'color': '#999', 'fontStyle': 'italic'})
    
    positions = load_json_file(POSITION_MARKER_PATH)
    position_map = {pos['id']: pos for pos in positions}
    
    return [
        dbc.Card([
            dbc.CardBody([
                html.Span(f"{position_map.get(pos, {}).get('name', 'Unknown')}", style={'fontWeight': '500'}),
                dbc.Button(
                    "×", 
                    id={'type': 'delete-goal-btn', 'index': i},
                    color="link", 
                    size="sm", 
                    style={'float': 'right', 'padding': '0', 'color': '#dc3545'}
                )
            ])
        ], style={'marginBottom': '8px', 'border': '1px solid #e0e0e0'}) 
        for i, pos in enumerate(data)
    ]

# Callback để tải dữ liệu ban đầu từ file path_guide.json khi khởi động app
@callback(
    [Output('start-positions-store', 'data', allow_duplicate=True),
     Output('waypoints-store', 'data', allow_duplicate=True),
     Output('goal-positions-store', 'data', allow_duplicate=True)],
    Input('url', 'pathname'),
    prevent_initial_call='initial_duplicate'
)
def load_initial_data(pathname):
    path_guide_data = load_json_file(PATH_GUIDE_PATH)
    if path_guide_data:
        return (
            path_guide_data.get('start_positions', []),
            path_guide_data.get('waypoints', []),
            path_guide_data.get('goal_positions', [])
        )
    return [], [], []