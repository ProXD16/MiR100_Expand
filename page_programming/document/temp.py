import dash
from dash import dcc, html, Input, Output, callback, State, ALL
import dash_bootstrap_components as dbc
import json
import os

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
app.config.suppress_callback_exceptions = True

# Custom styles (Giữ nguyên)
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

# Sample programs data
programs_data = [
    {"name": "7/7"}
]

def load_position_markers_from_file(default_file_path="/home/duc/Downloads/MIR100_WebApp/database_json/position_marker.json"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, default_file_path)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully loaded {len(data)} position markers from {file_path}")
        return data
    except FileNotFoundError:
        print(f"Error: Position marker file not found at {file_path}.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while loading position markers: {e}")
        return []

position_markers = load_position_markers_from_file()
if not position_markers:
    print("Warning: No position markers were loaded. Dropdowns for positions will be empty.")

# Icon definitions for dropdown items
dropdown_item_icons = {
    "move_default": "fas fa-map-marker-alt",
    "battery_docking": "fas fa-charging-station",
    "battery_charging": "fas fa-bolt",
    "battery_status": "fas fa-battery-three-quarters",
    "logic_break": "fas fa-stop-circle",
    "logic_continue": "fas fa-arrow-alt-circle-right",
    "logic_if": "fas fa-question-circle",
    "logic_loop": "fas fa-sync-alt",
    "logic_pause": "fas fa-pause-circle",
    "logic_return": "fas fa-undo-alt",
    "logic_while": "fas fa-redo-alt",
    "logic_wait": "fas fa-hourglass-half",
    "measure_distance": "fas fa-ruler-horizontal",
    "measure_area": "fas fa-vector-square",
    "measure_angle": "fas fa-drafting-compass",
    "measure_object_detection": "fas fa-binoculars",
    "plc_set_register": "fas fa-digital-tachograph", # NEW
    "plc_set_reset_register": "fas fa-toggle-on",    # NEW
    "plc_wait_register": "fas fa-hourglass-start",   # NEW
    "email_send": "fas fa-paper-plane",              # NEW
    "programming_custom_code": "fas fa-code",        # NEW (placeholder)
}

def create_dropdown_item_with_icon(text, icon_class):
    return html.Span([html.I(className=f"{icon_class} me-2"), text])

def create_program_card(program):
    # Giữ nguyên
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
                        dbc.Button([html.I(className="fas fa-trash")], color="danger", size="sm",outline=True, style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginRight": "5px"}),
                        dbc.Button([html.I(className="fas fa-play")], color="success", size="sm", outline=True, style={"borderRadius": "50%", "width": "35px", "height": "35px"})
                    ], className="d-flex justify-content-end align-items-center")
                ], width=4)
            ])
        ])
    ], style=custom_styles['program_card'], className="hover-shadow")

def create_main_layout():
    # Giữ nguyên
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
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
                    html.H5("Show programs:", className="mb-3", style={"fontWeight": "500", "color": "#2C3E50"}),
                    html.Div(id="programs-list")
                ], style=custom_styles['main_content'])
            ], width=9),
            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="fas fa-list-alt fa-2x mb-3", style={"color": "white"}),
                        html.H4("Program Queue", className="text-white mb-4", style={"fontWeight": "300"}),
                        html.P("Manage queued programs", className="text-white-50 mb-4")
                    ], className="text-center"),
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-video fa-lg me-2", style={"color": "#2ECC71"}),
                                html.Span("Cameras are ready to stream", style={"color": "#2ECC71", "fontWeight": "500"})
                            ], className="mb-3"),
                            html.P("The queue contains no programs", className="text-muted", style={"fontStyle": "italic"})
                        ])
                    ], style=custom_styles['card'])
                ], style=custom_styles['sidebar'])
            ], width=3)
        ], className="g-0")
    ])

def create_move_command_card_layout(command_info, command_idx):
    # Giữ nguyên
    marker = next((m for m in position_markers if m["id"] == command_info["marker_id"]), None)
    if not marker:
        error_label = f"Marker ID {command_info['marker_id']} (Not Found)"
        marker_display_name = "Unknown Position"
        marker_details = "Marker data missing"
    else:
        error_label = None
        marker_display_name = marker['name']
        marker_details = f"Current: {marker['name']} (X: {marker.get('x', 'N/A'):.2f}, Y: {marker.get('y', 'N/A'):.2f}, Z: {marker.get('z', 'N/A'):.2f})"

    card_children_elements = [
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className=f"{dropdown_item_icons['move_default']} fa-lg me-3", style={"color": "#E74C3C"}),
                    dbc.DropdownMenu(
                        [
                            dbc.DropdownMenuItem(
                                create_dropdown_item_with_icon(
                                    f"{m['name']} (X: {m.get('x', 'N/A'):.2f}, Y: {m.get('y', 'N/A'):.2f}, Z: {m.get('z', 'N/A'):.2f})",
                                    dropdown_item_icons['move_default']
                                ),
                                id={"type": "change-position-marker", "command_index": command_idx, "marker_id": m["id"]}
                            ) for m in position_markers
                        ] if position_markers else [dbc.DropdownMenuItem("No positions available", disabled=True)],
                        label=f"Move to {marker_display_name}" if not error_label else error_label,
                        id={"type": "position-dropdown-individual", "index": command_idx},
                        color="info",
                        size="sm",
                        style={"display": "inline-block", "marginLeft": "10px"}
                    ),
                    html.Div(
                        marker_details,
                        style={"display": "inline-block", "marginLeft": "15px", "fontWeight": "500", "fontSize":"0.9em"}
                    )
                ], className="d-flex align-items-center")
            ], width=True),
            dbc.Col([
                dbc.Button(
                    html.I(className="fas fa-cog"),
                    color="light", outline=True, size="sm",
                    id={"type": "command-config-btn", "index": command_idx, "command_type": "move"},
                    style={"borderRadius": "50%", "width": "35px", "height": "35px"}
                ),
                dbc.Button(
                    html.I(className="fas fa-trash"),
                    color="danger", outline=True, size="sm",
                    id={"type": "delete-command-btn", "index": command_idx},
                    style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}
                )
            ], width="auto")
        ], align="center")
    ]
    if error_label:
        card_children_elements.insert(0, dbc.Alert(f"Warning: Could not find marker data for ID {command_info['marker_id']}.", color="warning", duration=4000, style={'fontSize': '0.8em'}))

    return dbc.Card([
        dbc.CardBody(card_children_elements)
    ], color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

def create_battery_command_card_layout(command_info, command_idx):
    # Giữ nguyên
    subtype = command_info.get("subtype", "Unknown")
    icon_class = dropdown_item_icons.get(f"battery_{subtype}", "fas fa-question-circle")
    color = "#28a745"
    if subtype == "charging": color = "#fd7e14"
    if subtype == "status": color = "#17a2b8"

    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                        html.Span(f"Battery Command: {subtype.capitalize()}", style={"fontWeight": "500"})
                    ], className="d-flex align-items-center")
                ], width=True),
                dbc.Col([
                     dbc.Button(
                        html.I(className="fas fa-cog"),
                        color="light", outline=True, size="sm",
                        id={"type": "command-config-btn", "index": command_idx, "command_type": "battery"},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px"}
                    ),
                    dbc.Button(
                        html.I(className="fas fa-trash"),
                        color="danger", outline=True, size="sm",
                        id={"type": "delete-command-btn", "index": command_idx},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}
                    )
                ], width="auto")
            ], align="center")
        ])
    ], color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

def create_logic_command_card_layout(command_info, command_idx):
    # Giữ nguyên
    subtype = command_info.get("subtype", "Unknown")
    icon_class = dropdown_item_icons.get(f"logic_{subtype}", "fas fa-code-branch")
    color = "#6f42c1"

    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                        html.Span(f"Logic: {subtype.capitalize()}", style={"fontWeight": "500"})
                    ], className="d-flex align-items-center")
                ], width=True),
                dbc.Col([
                     dbc.Button(
                        html.I(className="fas fa-cog"),
                        color="light", outline=True, size="sm",
                        id={"type": "command-config-btn", "index": command_idx, "command_type": "logic"},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px"}
                    ),
                    dbc.Button(
                        html.I(className="fas fa-trash"),
                        color="danger", outline=True, size="sm",
                        id={"type": "delete-command-btn", "index": command_idx},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}
                    )
                ], width="auto")
            ], align="center")
        ])
    ], color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

def create_measure_command_card_layout(command_info, command_idx):
    # Giữ nguyên
    subtype = command_info.get("subtype", "Unknown")
    icon_class = dropdown_item_icons.get(f"measure_{subtype}", "fas fa-ruler")
    color = "#007bff"

    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                        html.Span(f"Measure: {subtype.capitalize().replace('_', ' ')}", style={"fontWeight": "500"})
                    ], className="d-flex align-items-center")
                ], width=True),
                dbc.Col([
                     dbc.Button(
                        html.I(className="fas fa-cog"),
                        color="light", outline=True, size="sm",
                        id={"type": "command-config-btn", "index": command_idx, "command_type": "measure"},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px"}
                    ),
                    dbc.Button(
                        html.I(className="fas fa-trash"),
                        color="danger", outline=True, size="sm",
                        id={"type": "delete-command-btn", "index": command_idx},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}
                    )
                ], width="auto")
            ], align="center")
        ])
    ], color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

# NEW: Function to create PLC command card layout
def create_plc_command_card_layout(command_info, command_idx):
    subtype = command_info.get("subtype", "Unknown")
    icon_class = dropdown_item_icons.get(f"plc_{subtype}", "fas fa-cogs") # Default PLC icon
    color = "#ffc107" # Yellow for PLC commands

    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                        html.Span(f"PLC: {subtype.replace('_', ' ').capitalize()}", style={"fontWeight": "500"})
                    ], className="d-flex align-items-center")
                ], width=True),
                dbc.Col([
                     dbc.Button(
                        html.I(className="fas fa-cog"),
                        color="light", outline=True, size="sm",
                        id={"type": "command-config-btn", "index": command_idx, "command_type": "plc"},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px"}
                    ),
                    dbc.Button(
                        html.I(className="fas fa-trash"),
                        color="danger", outline=True, size="sm",
                        id={"type": "delete-command-btn", "index": command_idx},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}
                    )
                ], width="auto")
            ], align="center")
        ])
    ], color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

# NEW: Function to create Email command card layout
def create_email_command_card_layout(command_info, command_idx):
    subtype = command_info.get("subtype", "Unknown") # Should be "send"
    icon_class = dropdown_item_icons.get(f"email_{subtype}", "fas fa-envelope")
    color = "#e83e8c" # Pink for Email commands

    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                        html.Span(f"Email: {subtype.capitalize()}", style={"fontWeight": "500"})
                    ], className="d-flex align-items-center")
                ], width=True),
                dbc.Col([
                     dbc.Button(
                        html.I(className="fas fa-cog"),
                        color="light", outline=True, size="sm",
                        id={"type": "command-config-btn", "index": command_idx, "command_type": "email"},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px"}
                    ),
                    dbc.Button(
                        html.I(className="fas fa-trash"),
                        color="danger", outline=True, size="sm",
                        id={"type": "delete-command-btn", "index": command_idx},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}
                    )
                ], width="auto")
            ], align="center")
        ])
    ], color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

# NEW: Function to create Programming command card layout (placeholder)
def create_programming_command_card_layout(command_info, command_idx):
    subtype = command_info.get("subtype", "Unknown") # e.g., "custom_code"
    icon_class = dropdown_item_icons.get(f"programming_{subtype}", "fas fa-terminal")
    color = "#343a40" # Dark grey for Programming commands

    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                        html.Span(f"Programming: {subtype.replace('_', ' ').capitalize()}", style={"fontWeight": "500"})
                    ], className="d-flex align-items-center")
                ], width=True),
                dbc.Col([
                     dbc.Button(
                        html.I(className="fas fa-cog"),
                        color="light", outline=True, size="sm",
                        id={"type": "command-config-btn", "index": command_idx, "command_type": "programming"},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px"}
                    ),
                    dbc.Button(
                        html.I(className="fas fa-trash"),
                        color="danger", outline=True, size="sm",
                        id={"type": "delete-command-btn", "index": command_idx},
                        style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}
                    )
                ], width="auto")
            ], align="center")
        ])
    ], color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

def create_program_editor_layout():
    add_move_dropdown_items = []
    if position_markers:
        for marker in position_markers:
            add_move_dropdown_items.append(
                dbc.DropdownMenuItem(
                    create_dropdown_item_with_icon(
                        marker.get("name", f"Unnamed Marker ID: {marker.get('id', 'N/A')}"),
                        dropdown_item_icons['move_default']
                    ),
                    id={"type": "add-move-command-action", "marker_id": marker.get("id")}
                )
            )
    else:
        add_move_dropdown_items.append(dbc.DropdownMenuItem("No positions available", disabled=True))

    battery_dropdown_items = [
        dbc.DropdownMenuItem(
            create_dropdown_item_with_icon("Docking", dropdown_item_icons['battery_docking']),
            id={"type": "add-battery-command-action", "subtype": "docking"}
        ),
        dbc.DropdownMenuItem(
            create_dropdown_item_with_icon("Charging", dropdown_item_icons['battery_charging']),
            id={"type": "add-battery-command-action", "subtype": "charging"}
        ),
        dbc.DropdownMenuItem(
            create_dropdown_item_with_icon("Status Battery", dropdown_item_icons['battery_status']),
            id={"type": "add-battery-command-action", "subtype": "status"}
        ),
    ]

    logic_dropdown_items_data = [
        ("Break", "break"), ("Continue", "continue"), ("If", "if"), ("Loop", "loop"),
        ("Pause", "pause"), ("Return", "return"), ("While", "while"), ("Wait", "wait"),
    ]
    logic_dropdown_items = [
        dbc.DropdownMenuItem(
            create_dropdown_item_with_icon(text, dropdown_item_icons[f"logic_{subtype}"]),
            id={"type": "add-logic-command-action", "subtype": subtype}
        ) for text, subtype in logic_dropdown_items_data
    ]

    measure_dropdown_items_data = [
        ("Distance", "distance"), ("Area", "area"),
        ("Angle", "angle"), ("Object Detection", "object_detection")
    ]
    measure_dropdown_items = [
        dbc.DropdownMenuItem(
            create_dropdown_item_with_icon(text, dropdown_item_icons.get(f"measure_{subtype}", "fas fa-ruler")),
            id={"type": "add-measure-command-action", "subtype": subtype}
        ) for text, subtype in measure_dropdown_items_data
    ]

    # Items for PLC Dropdown
    plc_dropdown_items_data = [
        ("Set PLC Register", "set_register"),
        ("Set and Reset PLC Register", "set_reset_register"),
        ("Wait for PLC Register", "wait_register")
    ]
    plc_dropdown_items = [
        dbc.DropdownMenuItem(
            create_dropdown_item_with_icon(text, dropdown_item_icons.get(f"plc_{subtype}", "fas fa-cogs")),
            id={"type": "add-plc-command-action", "subtype": subtype}
        ) for text, subtype in plc_dropdown_items_data
    ]

    # Item for Email Dropdown
    email_dropdown_items = [
        dbc.DropdownMenuItem(
            create_dropdown_item_with_icon("Send Email", dropdown_item_icons['email_send']),
            id={"type": "add-email-command-action", "subtype": "send"}
        )
    ]

    # Item for Programming Dropdown (placeholder)
    programming_dropdown_items = [
        dbc.DropdownMenuItem(
            create_dropdown_item_with_icon("Add Custom Code Block", dropdown_item_icons['programming_custom_code']),
            id={"type": "add-programming-command-action", "subtype": "custom_code"}
        ),
        # Add more programming-related options here if needed in the future
    ]

    return html.Div([
        html.Div([ # Header
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.H2([html.I(className="fas fa-code me-3"), "Programming"], className="text-white mb-2", style={"fontWeight": "300"}),
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
        
        dbc.Row([ # Program Name Input
            dbc.Col([
                html.Label("Program Name:", style={"fontWeight": "500", "color": "#2C3E50", "marginBottom": "5px"}),
                dbc.Input(id="program-name-input", placeholder="Enter program name", type="text", style=custom_styles['input_group'])
            ], width=6)
        ], className="mb-4"),
        
        dbc.Card([ # Tabs Card
            dbc.CardHeader([
                dbc.Nav([
                    dbc.NavItem(
                        dbc.DropdownMenu(
                            label=html.Span([html.I(className="fas fa-walking me-2"), "Move"]),
                            children=add_move_dropdown_items, nav=True, toggleClassName="fw-bold",
                        )
                    ),
                    dbc.NavItem(
                        dbc.DropdownMenu(
                            label=html.Span([html.I(className="fas fa-battery-full me-2"), "Battery"]),
                            children=battery_dropdown_items, nav=True, toggleClassName="fw-bold",
                        )
                    ),
                    dbc.NavItem(
                        dbc.DropdownMenu(
                            label=html.Span([html.I(className="fas fa-brain me-2"), "Logic"]),
                            children=logic_dropdown_items, nav=True, toggleClassName="fw-bold",
                        )
                    ),
                    dbc.NavItem(
                        dbc.DropdownMenu(
                            label=html.Span([html.I(className="fas fa-ruler-combined me-2"), "Measure"]),
                            children=measure_dropdown_items, nav=True, toggleClassName="fw-bold",
                        )
                    ),
                    dbc.NavItem( # PLC Tab
                        dbc.DropdownMenu(
                            label=html.Span([html.I(className="fas fa-microchip me-2"), "PLC"]),
                            children=plc_dropdown_items, nav=True, toggleClassName="fw-bold",
                        )
                    ),
                    dbc.NavItem( # Email Tab
                        dbc.DropdownMenu(
                            label=html.Span([html.I(className="fas fa-envelope me-2"), "Email"]),
                            children=email_dropdown_items, nav=True, toggleClassName="fw-bold",
                        )
                    ),
                    dbc.NavItem( # Programming Tab
                        dbc.DropdownMenu(
                            label=html.Span([html.I(className="fas fa-tasks me-2"), "Programming"]), # Icon was fa-tasks
                            children=programming_dropdown_items, nav=True, toggleClassName="fw-bold",
                        )
                    ),
                ], pills=True)
            ], style={"background": "#f8f9fa"})
        ], style={**custom_styles['card'], "position": "relative", "zIndex": 2}, className="mb-4"),
        
        dbc.Card([ # Loop Configuration & Commands Card
            # ... (giữ nguyên)
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
                html.H6("Program Commands:", className="mb-3 mt-4", style={"fontWeight": "600"}),
                html.Div(id="program-commands-container", children=[])
            ])
        ], style={**custom_styles['card'], "position": "relative", "zIndex": 1}, className="mb-4")
    ], style=custom_styles['main_content'])

# Main app layout
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content"),
    dcc.Store(id="page-state", data={"current_page": "main"}),
    dcc.Store(id="program-commands-store", data=[])
])

# --- Callbacks ---
@callback(Output("programs-list", "children"), Input("url", "pathname"))
def update_programs_list(pathname):
    return [create_program_card(program) for program in programs_data]

@callback(
    [Output("page-content", "children"), Output("page-state", "data")],
    [Input("url", "pathname")],
    [State("page-state", "data")],
    prevent_initial_call=False
)
def display_page(pathname, page_state_data):
    return create_main_layout(), {"current_page": "main"}

@callback(
    [Output("page-content", "children", allow_duplicate=True),
     Output("page-state", "data", allow_duplicate=True),
     Output("program-commands-store", "data", allow_duplicate=True)],
    [Input("create-program-btn", "n_clicks")],
    prevent_initial_call=True
)
def go_to_editor(n_clicks):
    if n_clicks:
        return create_program_editor_layout(), {"current_page": "editor"}, []
    return dash.no_update, dash.no_update, dash.no_update

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

# Generic command adder
def _add_command_to_store(n_clicks_all, current_commands, command_type):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks for n_clicks in n_clicks_all if n_clicks is not None):
        return dash.no_update
    triggered_input = ctx.triggered[0]; prop_id = triggered_input['prop_id']
    if ".n_clicks" not in prop_id: return dash.no_update
    item_id_str = prop_id.split(".n_clicks")[0]
    try:
        item_id_dict = json.loads(item_id_str)
        subtype_to_add = item_id_dict.get("subtype") # marker_id for move
        marker_id_to_add = item_id_dict.get("marker_id")

        if command_type == "move" and marker_id_to_add is None: return dash.no_update
        if command_type != "move" and subtype_to_add is None: return dash.no_update

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Error parsing ID in add_{command_type}_command: {item_id_str}, Error: {e}")
        return dash.no_update
    
    new_command = {"type": command_type, "config": {}}
    if command_type == "move":
        new_command["marker_id"] = marker_id_to_add
    else:
        new_command["subtype"] = subtype_to_add
        
    current_commands = current_commands or []
    return current_commands + [new_command]

@app.callback(Output("program-commands-store", "data", allow_duplicate=True),
              [Input({"type": "add-move-command-action", "marker_id": ALL}, "n_clicks")],
              [State("program-commands-store", "data")], prevent_initial_call=True)
def add_move_command(n, s): return _add_command_to_store(n, s, "move")

@app.callback(Output("program-commands-store", "data", allow_duplicate=True),
              [Input({"type": "add-battery-command-action", "subtype": ALL}, "n_clicks")],
              [State("program-commands-store", "data")], prevent_initial_call=True)
def add_battery_command(n, s): return _add_command_to_store(n, s, "battery")

@app.callback(Output("program-commands-store", "data", allow_duplicate=True),
              [Input({"type": "add-logic-command-action", "subtype": ALL}, "n_clicks")],
              [State("program-commands-store", "data")], prevent_initial_call=True)
def add_logic_command(n, s): return _add_command_to_store(n, s, "logic")

@app.callback(Output("program-commands-store", "data", allow_duplicate=True),
              [Input({"type": "add-measure-command-action", "subtype": ALL}, "n_clicks")],
              [State("program-commands-store", "data")], prevent_initial_call=True)
def add_measure_command(n, s): return _add_command_to_store(n, s, "measure")

@app.callback(Output("program-commands-store", "data", allow_duplicate=True),
              [Input({"type": "add-plc-command-action", "subtype": ALL}, "n_clicks")],
              [State("program-commands-store", "data")], prevent_initial_call=True)
def add_plc_command(n, s): return _add_command_to_store(n, s, "plc")

@app.callback(Output("program-commands-store", "data", allow_duplicate=True),
              [Input({"type": "add-email-command-action", "subtype": ALL}, "n_clicks")],
              [State("program-commands-store", "data")], prevent_initial_call=True)
def add_email_command(n, s): return _add_command_to_store(n, s, "email")

@app.callback(Output("program-commands-store", "data", allow_duplicate=True),
              [Input({"type": "add-programming-command-action", "subtype": ALL}, "n_clicks")],
              [State("program-commands-store", "data")], prevent_initial_call=True)
def add_programming_command(n, s): return _add_command_to_store(n, s, "programming")


@app.callback(
    Output("program-commands-container", "children"),
    [Input("program-commands-store", "data")]
)
def render_program_commands(commands_data):
    if not commands_data:
        return dbc.Alert("No program commands added yet. Select from tabs to add commands.", color="info", className="mt-3 text-center")
    
    cards = []
    for idx, cmd_data in enumerate(commands_data):
        if cmd_data:
            command_type = cmd_data.get("type")
            if command_type == "move":
                cards.append(create_move_command_card_layout(cmd_data, idx))
            elif command_type == "battery":
                cards.append(create_battery_command_card_layout(cmd_data, idx))
            elif command_type == "logic":
                cards.append(create_logic_command_card_layout(cmd_data, idx))
            elif command_type == "measure":
                cards.append(create_measure_command_card_layout(cmd_data, idx))
            elif command_type == "plc": # NEW
                cards.append(create_plc_command_card_layout(cmd_data, idx))
            elif command_type == "email": # NEW
                cards.append(create_email_command_card_layout(cmd_data, idx))
            elif command_type == "programming": # NEW
                cards.append(create_programming_command_card_layout(cmd_data, idx))
    return cards

@app.callback(
    Output("program-commands-store", "data", allow_duplicate=True),
    [Input({"type": "change-position-marker", "command_index": ALL, "marker_id": ALL}, "n_clicks")],
    [State("program-commands-store", "data")],
    prevent_initial_call=True
)
def change_command_position(n_clicks_all, current_commands):
    # Giữ nguyên
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks for n_clicks in n_clicks_all if n_clicks is not None) or not current_commands:
        return dash.no_update
    triggered_input = ctx.triggered[0]; prop_id = triggered_input['prop_id']
    if ".n_clicks" not in prop_id: return dash.no_update
    item_id_str = prop_id.split(".n_clicks")[0]
    try:
        item_id_dict = json.loads(item_id_str)
        command_idx = item_id_dict["command_index"]; new_marker_id = item_id_dict["marker_id"]
        if command_idx is None or new_marker_id is None: return dash.no_update
    except (json.JSONDecodeError, KeyError, TypeError): return dash.no_update
    if 0 <= command_idx < len(current_commands):
        updated_commands = list(current_commands)
        if updated_commands[command_idx].get("type") == "move":
            updated_commands[command_idx] = {**updated_commands[command_idx], "marker_id": new_marker_id}
            return updated_commands
    return dash.no_update

@app.callback(
    Output("program-commands-store", "data", allow_duplicate=True),
    [Input({"type": "delete-command-btn", "index": ALL}, "n_clicks")],
    [State("program-commands-store", "data")],
    prevent_initial_call=True
)
def delete_program_command(n_clicks_all, current_commands):
    # Giữ nguyên
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks for n_clicks in n_clicks_all if n_clicks is not None) or not current_commands:
        return dash.no_update
    triggered_input = ctx.triggered[0]; prop_id = triggered_input['prop_id']
    if ".n_clicks" not in prop_id: return dash.no_update
    item_id_str = prop_id.split(".n_clicks")[0]
    try:
        item_id_dict = json.loads(item_id_str)
        command_idx_to_delete = item_id_dict["index"]
        if command_idx_to_delete is None: return dash.no_update
    except (json.JSONDecodeError, KeyError, TypeError): return dash.no_update
    if 0 <= command_idx_to_delete < len(current_commands):
        updated_commands = [cmd for i, cmd in enumerate(current_commands) if i != command_idx_to_delete]
        return updated_commands
    return dash.no_update

if __name__ == "__main__":
    app.run(debug=True, port=8050)