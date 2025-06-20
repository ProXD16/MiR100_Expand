import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import json
import os

class LayoutManager:
    # Static data
    CUSTOM_STYLES = {
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
        },
        'nested_command_block': {
            'padding': '1rem',
            'borderLeft': '3px solid #77B5FE',
            'marginLeft': '0.5rem',
            'backgroundColor': 'rgba(230, 240, 255, 0.4)',
            'borderRadius': '8px',
            'marginBottom': '1rem',
            'boxShadow': 'inset 0 2px 4px rgba(0,0,0,0.05)'
        },
        'config_section': {
            'padding': '0.75rem',
            'backgroundColor': 'rgba(0,0,0,0.03)',
            'borderRadius': '6px',
            'marginBottom': '1rem',
            'border': '1px solid rgba(0,0,0,0.08)'
        },
        'operator_display': {
            'fontSize': '1.5em',
            'fontWeight': 'bold',
            'color': '#5D6D7E',
            'padding': '0 1rem',
            'textAlign': 'center'
        }
    }

    DROPDOWN_ITEM_ICONS = {
        "move_default": "fas fa-map-marker-alt",
        "battery_docking": "fas fa-charging-station", "battery_charging": "fas fa-bolt", "battery_status": "fas fa-battery-three-quarters",
        "logic_break": "fas fa-stop-circle", "logic_continue": "fas fa-arrow-alt-circle-right", "logic_if": "fas fa-question-circle",
        "logic_loop": "fas fa-sync-alt", "logic_pause": "fas fa-pause-circle", "logic_return": "fas fa-undo-alt",
        "logic_while": "fas fa-redo-alt", "logic_wait": "fas fa-hourglass-half",
        "measure_distance": "fas fa-ruler-horizontal", "measure_area": "fas fa-vector-square", "measure_angle": "fas fa-drafting-compass",
        "measure_object_detection": "fas fa-binoculars",
        "plc_set_register": "fas fa-digital-tachograph", "plc_set_reset_register": "fas fa-toggle-on", "plc_wait_register": "fas fa-hourglass-start",
        "email_send": "fas fa-paper-plane",
        "programming_custom_code": "fas fa-code",
        "programming_call_program": "fas fa-project-diagram",
        "math_less_than": "fas fa-less-than",
        "math_less_than_or_equal_to": "fas fa-less-than-equal",
        "math_greater_than": "fas fa-greater-than",
        "math_greater_than_or_equal_to": "fas fa-greater-than-equal",
        "math_equal_to": "fas fa-equals",
        "math_not_equal_to": "fas fa-not-equal",
        "math_generic": "fas fa-calculator"
    }

    DEFAULT_PROGRAMS_FILE_PATH = "/home/duc/Downloads/MIR100_WebApp/database_json/programming_json.json"
    DEFAULT_POSITIONS_FILE_PATH = "/home/duc/Downloads/MIR100_WebApp/database_json/position_marker.json"
    DEFAULT_QUEUE_FILE_PATH = "/home/duc/Downloads/MIR100_WebApp/database_json/queue_programming.json"


    def __init__(self,
                 programs_file_path=None,
                 positions_file_path=None,
                 queue_file_path=None):
        self.programs_file_path = programs_file_path or self.DEFAULT_PROGRAMS_FILE_PATH
        self.positions_file_path = positions_file_path or self.DEFAULT_POSITIONS_FILE_PATH
        self.queue_file_path = queue_file_path or self.DEFAULT_QUEUE_FILE_PATH

        self.programs_data = self._load_data_from_file(self.programs_file_path, "programs")
        self.position_markers = self._load_data_from_file(self.positions_file_path, "position markers")

        if not self.programs_data:
            print("Warning: No programs loaded initially. The program list on the main page will be empty.")
        if not self.position_markers:
            print("Warning: No position markers loaded.")

    def _load_data_from_file(self, file_path_str, data_type_name="data"):
        """Generic helper to load JSON data from a file."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Ensure file_path_str is treated as a string for os.path.isabs
        current_file_path_str = str(file_path_str)
        if not os.path.isabs(current_file_path_str):
            file_path = os.path.join(script_dir, current_file_path_str)
        else:
            file_path = current_file_path_str
        
        try:
            if not os.path.exists(file_path):
                # print(f"{data_type_name.capitalize()} file '{file_path}' not found. Returning empty list.")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    # print(f"{data_type_name.capitalize()} file '{file_path}' is empty. Returning empty list.")
                    return []
                data = json.loads(content)

            if not isinstance(data, list):
                print(f"Warning: {data_type_name.capitalize()} file '{file_path}' does not contain a list (found type: {type(data)}). Returning empty list.")
                return []
            
            if data_type_name == "programs": # Specific validation for programs
                valid_programs = []
                for i, item in enumerate(data):
                    if isinstance(item, dict) and "name" in item:
                        valid_programs.append(item)
                    else:
                        print(f"Warning: Invalid program entry at index {i} in '{file_path}': {str(item)[:100]}. Skipping.")
                return valid_programs
            
            return data # For other data types like position_markers or queue
            
        except json.JSONDecodeError as jde:
            print(f"Error decoding JSON from {data_type_name} file '{file_path}': {jde}. Returning empty list.")
            return []
        except Exception as e:
            print(f"An unexpected error occurred while loading {data_type_name} from '{file_path}': {e}. Returning empty list.")
            return []

    def reload_programs_data(self, file_path=None):
        """Reloads programs_data from the specified file or the default."""
        load_path = file_path or self.programs_file_path
        self.programs_data = self._load_data_from_file(load_path, "programs")
        return self.programs_data

    def load_queued_programs_from_file(self, file_path=None):
        """Loads queued programs from the specified file or the default queue file."""
        load_path = file_path or self.queue_file_path
        return self._load_data_from_file(load_path, "queued programs")

    @staticmethod
    def create_dropdown_item_with_icon(text, icon_class):
        return html.Span([html.I(className=f"{icon_class} me-2"), text])

    def create_program_card(self, program):
        program_name = program["name"]
        return dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className="fas fa-bullseye fa-lg me-3", style={"color": "#28a745"}),
                            html.H6(program_name, className="mb-0", style={"fontWeight": "600", "color": "#2C3E50"})
                        ], className="d-flex align-items-center")
                    ], width=8),
                    dbc.Col([
                        html.Div([
                            dbc.Button([html.I(className="fas fa-edit")], id={"type": "edit-program-btn", "program_name": program_name}, color="primary", size="sm", className="me-2", outline=True, style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                            dbc.Button([html.I(className="fas fa-trash")], id={"type": "delete-program-main-btn", "program_name": program_name}, color="danger", size="sm", outline=True, style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginRight": "5px"}),
                            dbc.Button([html.I(className="fas fa-play")], id={"type": "run-program-main-btn", "program_name": program_name}, color="success", size="sm", outline=True, style={"borderRadius": "50%", "width": "35px", "height": "35px"})
                        ], className="d-flex justify-content-end align-items-center")
                    ], width=4)
                ])
            ])
        ], style=self.CUSTOM_STYLES['program_card'], className="hover-shadow")

    def create_queued_program_mini_card(self, program, index):
        program_name = program.get("name", "Unnamed Program")
        num_commands = len(program.get("commands", []))
        return dbc.Card(
            dbc.CardBody(
                [
                    dbc.Row([
                        dbc.Col(html.I(className="fas fa-stream me-2", style={"color": "#77B5FE"}), width="auto", className="ps-1 pe-0"),
                        dbc.Col(html.P(f"{index+1}. {program_name}", className="mb-0 small", style={"fontWeight": "bold"}), className="px-1"),
                        dbc.Col(html.Small(f"({num_commands} cmd{'s' if num_commands != 1 else ''})", className="text-muted ms-auto"), width="auto", className="pe-1")
                    ], align="center")
                ],
                style={"padding": "0.4rem 0.6rem"}
            ),
            className="mb-1",
            style={"backgroundColor": "rgba(255,255,255,0.85)", "border": "1px solid rgba(0,0,0,0.05)"}
        )

    def create_main_layout(self):
        return html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Row([
                            dbc.Col([html.H1("Programming", style={"fontWeight": "300", "color": "#2C3E50", "marginBottom": "5px"}), html.P("Create and edit programs.", className="text-muted mb-4", style={"fontSize": "1.1rem"})], width=8),
                            dbc.Col([dbc.Button([html.I(className="fas fa-plus me-2"), "Create program"], id="create-program-btn", style=self.CUSTOM_STYLES['gradient_button'], className="float-end")], width=4)
                        ], className="mb-4"),
                        html.H5("Show programs:", className="mb-3", style={"fontWeight": "500", "color": "#2C3E50"}),
                        html.Div(id="programs-list")
                    ], style=self.CUSTOM_STYLES['main_content'])
                ], width=9),
                dbc.Col([
                    html.Div([
                        html.Div([html.I(className="fas fa-list-alt fa-2x mb-3", style={"color": "white"}), html.H4("Program Queue", className="text-white mb-4", style={"fontWeight": "300"}), html.P("Manage queued programs", className="text-white-50 mb-4")], className="text-center"),
                        dbc.Card([
                            dbc.CardBody([
                                html.Div([
                                    html.I(className="fas fa-tasks fa-lg me-2", style={"color": "#2ECC71"}),
                                    html.Span("All Programs", style={"color": "#2ECC71", "fontWeight": "500"})
                                ], className="mb-3"),
                                html.Div(id="program-queue-list")
                            ])
                        ], style=self.CUSTOM_STYLES['card'])
                    ], style=self.CUSTOM_STYLES['sidebar'])
                ], width=3)
            ], className="g-0")
        ])

    def create_move_command_card_layout(self, command_info):
        command_id = command_info["id"]
        marker = next((m for m in self.position_markers if m["id"] == command_info["marker_id"]), None)
        error_label, marker_display_name, marker_details = None, "Unknown Position", "Marker data missing"
        if marker:
            marker_display_name = marker['name']
            marker_details = f"Current: {marker['name']} (X: {marker.get('x', 'N/A'):.2f}, Y: {marker.get('y', 'N/A'):.2f}, Z: {marker.get('z', 'N/A'):.2f})"
        else:
            error_label = f"Marker ID {command_info['marker_id']} (Not Found)"

        card_children = [
            dbc.Row([
                dbc.Col(html.Div([
                    html.I(className=f"{self.DROPDOWN_ITEM_ICONS['move_default']} fa-lg me-3", style={"color": "#E74C3C"}),
                    dbc.DropdownMenu(
                        [dbc.DropdownMenuItem(
                            self.create_dropdown_item_with_icon(
                                f"{m['name']} (X: {m.get('x', 'N/A'):.2f}, Y: {m.get('y', 'N/A'):.2f}, Z: {m.get('z', 'N/A'):.2f})",
                                self.DROPDOWN_ITEM_ICONS['move_default']
                            ), id={"type": "change-position-marker", "command_id": command_id, "marker_id": m["id"]}
                        ) for m in self.position_markers] if self.position_markers else [dbc.DropdownMenuItem("No positions available", disabled=True)],
                        label=f"Move to {marker_display_name}" if not error_label else error_label,
                        id={"type": "position-dropdown-individual", "command_id": command_id},
                        color="info", size="sm", style={"display": "inline-block", "marginLeft": "10px"}
                    ),
                    html.Div(marker_details, style={"display": "inline-block", "marginLeft": "15px", "fontWeight": "500", "fontSize":"0.9em"})
                ], className="d-flex align-items-center"), width=True),
                dbc.Col([
                    dbc.Button(html.I(className="fas fa-cog"), color="light", outline=True, size="sm",
                               id={"type": "command-config-btn", "command_id": command_id, "command_type": "move"},
                               style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                    dbc.Button(html.I(className="fas fa-trash"), color="danger", outline=True, size="sm",
                               id={"type": "delete-command-btn", "command_id": command_id},
                               style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"})
                ], width="auto")
            ], align="center")
        ]
        if error_label:
            card_children.insert(0, dbc.Alert(f"Warning: Could not find marker data for ID {command_info['marker_id']}.", color="warning", duration=4000, style={'fontSize': '0.8em'}))
        return dbc.Card(dbc.CardBody(card_children), color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

    def create_battery_command_card_layout(self, command_info):
        command_id = command_info["id"]
        subtype = command_info.get("subtype", "Unknown")
        icon_class = self.DROPDOWN_ITEM_ICONS.get(f"battery_{subtype}", "fas fa-question-circle")
        color_map = {"docking": "#28a745", "charging": "#fd7e14", "status": "#17a2b8"}
        color = color_map.get(subtype, "#6c757d")
        return dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col(html.Div([
                html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                html.Span(f"Battery Command: {subtype.capitalize()}", style={"fontWeight": "500"})
            ], className="d-flex align-items-center"), width=True),
            dbc.Col([
                dbc.Button(html.I(className="fas fa-cog"), id={"type": "command-config-btn", "command_id": command_id, "command_type": "battery", "subtype": subtype}, color="light", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                dbc.Button(html.I(className="fas fa-trash"), id={"type": "delete-command-btn", "command_id": command_id}, color="danger", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"})
            ], width="auto")
        ], align="center")), color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

    def create_generic_logic_command_card_layout(self, command_info):
        command_id = command_info["id"]
        subtype = command_info.get("subtype", "Unknown")
        icon_class = self.DROPDOWN_ITEM_ICONS.get(f"logic_{subtype}", "fas fa-code-branch")
        color = "#6f42c1"
        return dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col(html.Div([
                html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                html.Span(f"Logic: {subtype.capitalize()}", style={"fontWeight": "500"})
            ], className="d-flex align-items-center"), width=True),
            dbc.Col([
                dbc.Button(html.I(className="fas fa-cog"), id={"type": "command-config-btn", "command_id": command_id, "command_type": "logic", "subtype": subtype}, color="light", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                dbc.Button(html.I(className="fas fa-trash"), id={"type": "delete-command-btn", "command_id": command_id}, color="danger", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"})
            ], width="auto")
        ], align="center")), color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

    def create_measure_command_card_layout(self, command_info):
        command_id = command_info["id"]
        subtype = command_info.get("subtype", "Unknown")
        icon_class = self.DROPDOWN_ITEM_ICONS.get(f"measure_{subtype}", "fas fa-ruler")
        color = "#007bff"
        return dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col(html.Div([
                html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                html.Span(f"Measure: {subtype.capitalize().replace('_', ' ')}", style={"fontWeight": "500"})
            ], className="d-flex align-items-center"), width=True),
            dbc.Col([
                dbc.Button(html.I(className="fas fa-cog"), id={"type": "command-config-btn", "command_id": command_id, "command_type": "measure", "subtype": subtype}, color="light", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                dbc.Button(html.I(className="fas fa-trash"), id={"type": "delete-command-btn", "command_id": command_id}, color="danger", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"})
            ], width="auto")
        ], align="center")), color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

    def create_plc_command_card_layout(self, command_info):
        command_id = command_info["id"]
        subtype = command_info.get("subtype", "Unknown")
        icon_class = self.DROPDOWN_ITEM_ICONS.get(f"plc_{subtype}", "fas fa-cogs")
        color = "#ffc107"
        return dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col(html.Div([
                html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                html.Span(f"PLC: {subtype.replace('_', ' ').capitalize()}", style={"fontWeight": "500"})
            ], className="d-flex align-items-center"), width=True),
            dbc.Col([
                dbc.Button(html.I(className="fas fa-cog"), id={"type": "command-config-btn", "command_id": command_id, "command_type": "plc", "subtype": subtype}, color="light", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                dbc.Button(html.I(className="fas fa-trash"), id={"type": "delete-command-btn", "command_id": command_id}, color="danger", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"})
            ], width="auto")
        ], align="center")), color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

    def create_email_command_card_layout(self, command_info):
        command_id = command_info["id"]
        subtype = command_info.get("subtype", "Unknown")
        icon_class = self.DROPDOWN_ITEM_ICONS.get(f"email_{subtype}", "fas fa-envelope")
        color = "#e83e8c"
        return dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col(html.Div([
                html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                html.Span(f"Email: {subtype.capitalize()}", style={"fontWeight": "500"})
            ], className="d-flex align-items-center"), width=True),
            dbc.Col([
                dbc.Button(html.I(className="fas fa-cog"), id={"type": "command-config-btn", "command_id": command_id, "command_type": "email", "subtype": subtype}, color="light", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                dbc.Button(html.I(className="fas fa-trash"), id={"type": "delete-command-btn", "command_id": command_id}, color="danger", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"})
            ], width="auto")
        ], align="center")), color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

    def create_programming_command_card_layout(self, command_info):
        command_id = command_info["id"]
        subtype = command_info.get("subtype", "custom_code")
        display_text = ""
        icon_class = ""
        color = "#343a40"

        if subtype == "call_program":
            called_program_name = command_info.get("config", {}).get("called_program_name", "N/A")
            display_text = f"Call Program: {called_program_name}"
            icon_class = self.DROPDOWN_ITEM_ICONS.get("programming_call_program", "fas fa-project-diagram")
        elif subtype == "custom_code":
            display_text = "Custom Code Block"
            icon_class = self.DROPDOWN_ITEM_ICONS.get("programming_custom_code", "fas fa-code")
        else:
            display_text = f"Programming: {str(subtype).replace('_', ' ').capitalize()}"
            icon_class = self.DROPDOWN_ITEM_ICONS.get(f"programming_{subtype}", "fas fa-terminal")

        return dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col(html.Div([
                html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}),
                html.Span(display_text, style={"fontWeight": "500"})
            ], className="d-flex align-items-center"), width=True),
            dbc.Col([
                dbc.Button(html.I(className="fas fa-cog"),
                           id={"type": "command-config-btn", "command_id": command_id, "command_type": "programming", "subtype": subtype},
                           color="light", outline=True, size="sm",
                           style={"borderRadius": "50%", "width": "35px", "height": "35px"}),
                dbc.Button(html.I(className="fas fa-trash"),
                           id={"type": "delete-command-btn", "command_id": command_id},
                           color="danger", outline=True, size="sm",
                           style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"})
            ], width="auto")
        ], align="center")), color="light", outline=False, style={"borderWidth": "1px", "borderRadius": "12px", "background": "rgba(255,255,255,0.85)"}, className="mb-2 shadow-sm")

    def _create_programming_dropdown_items(self, target_parent_id=None, target_block_spec_json=None):
        base_id_params = {"type": "add-programming-command-action"}
        if target_parent_id and target_block_spec_json:
            base_id_params["target_parent_id"] = target_parent_id
            base_id_params["target_block_spec"] = target_block_spec_json

        items = [
            dbc.DropdownMenuItem(
                self.create_dropdown_item_with_icon("Add Custom Code Block", self.DROPDOWN_ITEM_ICONS.get('programming_custom_code', 'fas fa-code')),
                id={**base_id_params, "subtype": "custom_code"}
            )
        ]
        current_programs = self.programs_data
        if current_programs:
            items.append(dbc.DropdownMenuItem(divider=True))
            items.append(dbc.DropdownMenuItem("Call Existing Program:", header=True))
            for prog in current_programs:
                if isinstance(prog, dict) and "name" in prog:
                    items.append(dbc.DropdownMenuItem(
                        self.create_dropdown_item_with_icon(
                            f"{prog['name']}",
                            self.DROPDOWN_ITEM_ICONS.get('programming_call_program', 'fas fa-project-diagram')
                        ),
                        id={**base_id_params, "subtype": "call_program", "program_name_to_call": prog["name"]}
                    ))
        else:
            items.append(dbc.DropdownMenuItem(divider=True))
            items.append(dbc.DropdownMenuItem("No programs available to call", disabled=True))
        return items

    def create_add_command_palette(self, target_parent_id, target_block_spec_json):
        add_move_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(m.get("name", f"Unnamed: {m['id']}"), self.DROPDOWN_ITEM_ICONS['move_default']), id={"type": "add-move-command-action", "marker_id": m.get("id"), "target_parent_id": target_parent_id, "target_block_spec": target_block_spec_json}) for m in self.position_markers] if self.position_markers else [dbc.DropdownMenuItem("No positions available", disabled=True)]
        battery_subtypes = [("Docking", "docking"), ("Charging", "charging"), ("Status Battery", "status")]
        battery_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(text, self.DROPDOWN_ITEM_ICONS[f'battery_{subtype}']), id={"type": "add-battery-command-action", "subtype": subtype, "target_parent_id": target_parent_id, "target_block_spec": target_block_spec_json}) for text, subtype in battery_subtypes]
        logic_subtypes_for_palette = [("If", "if"), ("Loop", "loop"), ("While", "while"), ("Break", "break"), ("Continue", "continue"), ("Pause", "pause"), ("Return", "return"), ("Wait", "wait")]
        logic_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(text, self.DROPDOWN_ITEM_ICONS[f'logic_{subtype}']), id={"type": "add-logic-command-action", "subtype": subtype, "target_parent_id": target_parent_id, "target_block_spec": target_block_spec_json}) for text, subtype in logic_subtypes_for_palette]

        math_subtypes_data = [
            ("Less Than (<)", "less_than"), ("Less Than or Equal To (<=)", "less_than_or_equal_to"),
            ("Greater Than (>)", "greater_than"), ("Greater Than or Equal To (>=)", "greater_than_or_equal_to"),
            ("Equal To (==)", "equal_to"), ("Not Equal To (!=)", "not_equal_to")
        ]
        math_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(text, self.DROPDOWN_ITEM_ICONS.get(f"math_{subtype}", "fas fa-calculator")), id={"type": "add-math-command-action", "subtype": subtype, "target_parent_id": target_parent_id, "target_block_spec": target_block_spec_json}) for text, subtype in math_subtypes_data]

        measure_subtypes = [("Distance", "distance"), ("Area", "area"), ("Angle", "angle"), ("Object Detection", "object_detection")]
        measure_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(text, self.DROPDOWN_ITEM_ICONS.get(f"measure_{subtype}", "fas fa-ruler")), id={"type": "add-measure-command-action", "subtype": subtype, "target_parent_id": target_parent_id, "target_block_spec": target_block_spec_json}) for text, subtype in measure_subtypes]
        plc_subtypes = [("Set PLC Register", "set_register"), ("Set and Reset PLC Register", "set_reset_register"), ("Wait for PLC Register", "wait_register")]
        plc_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(text, self.DROPDOWN_ITEM_ICONS.get(f"plc_{subtype}", "fas fa-cogs")), id={"type": "add-plc-command-action", "subtype": subtype, "target_parent_id": target_parent_id, "target_block_spec": target_block_spec_json}) for text, subtype in plc_subtypes]
        email_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon("Send Email", self.DROPDOWN_ITEM_ICONS['email_send']), id={"type": "add-email-command-action", "subtype": "send", "target_parent_id": target_parent_id, "target_block_spec": target_block_spec_json})]

        programming_dropdown_items = self._create_programming_dropdown_items(target_parent_id, target_block_spec_json)

        return dbc.Nav([
            dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-walking me-2"), "Move"]), children=add_move_dropdown_items, nav=True, toggleClassName="fw-bold btn-sm")),
            dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-battery-full me-2"), "Battery"]), children=battery_dropdown_items, nav=True, toggleClassName="fw-bold btn-sm")),
            dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-brain me-2"), "Logic"]), children=logic_dropdown_items, nav=True, toggleClassName="fw-bold btn-sm")),
            dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-calculator me-2"), "Math"]), children=math_dropdown_items, nav=True, toggleClassName="fw-bold btn-sm")),
            dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-ruler-combined me-2"), "Measure"]), children=measure_dropdown_items, nav=True, toggleClassName="fw-bold btn-sm")),
            dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-microchip me-2"), "PLC"]), children=plc_dropdown_items, nav=True, toggleClassName="fw-bold btn-sm")),
            dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-envelope me-2"), "Email"]), children=email_dropdown_items, nav=True, toggleClassName="fw-bold btn-sm")),
            dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-tasks me-2"), "Programming"]), children=programming_dropdown_items, nav=True, toggleClassName="fw-bold btn-sm")),
        ], pills=True, className="mb-3 command-palette-condensed")

    def create_command_block_layout(self, title_text, commands_list, parent_command_id, block_specifier_dict, limit_one=False):
        command_cards = [self.render_single_command(cmd) for cmd in commands_list if cmd]
        block_specifier_json = json.dumps(block_specifier_dict)
        add_palette_disabled = limit_one and len(command_cards) >= 1
        add_palette = self.create_add_command_palette(parent_command_id, block_specifier_json)
        block_content = []
        if not add_palette_disabled:
            block_content.append(add_palette)
        else:
            block_content.append(dbc.Alert("This block can only contain one command.", color="info", className="text-center fst-italic p-1 small"))
        block_content.append(html.Div(command_cards if command_cards else dbc.Alert("No commands in this block.", color="light", className="text-center fst-italic p-2"), className="command-list-container"))
        return html.Div([html.H6(title_text, className="fw-bold text-primary border-bottom pb-2 mb-3"), *block_content], style=self.CUSTOM_STYLES['nested_command_block'])

    def create_if_logic_command_card_layout(self, command_info):
        if_command_id = command_info["id"]
        icon_class = self.DROPDOWN_ITEM_ICONS.get("logic_if", "fas fa-question-circle")
        condition_block = self.create_command_block_layout(html.Span([html.I(className="fas fa-question-circle me-2"), "Conditions"]), command_info.get("conditions", []), if_command_id, {"type": "if_conditions"})
        then_block = self.create_command_block_layout(html.Span([html.I(className="fas fa-check-circle me-2"), "Then"]), command_info.get("then_commands", []), if_command_id, {"type": "if_then"})
        else_if_blocks_layouts = []
        for i, else_if_block_data in enumerate(command_info.get("else_if_blocks", [])):
            else_if_block_id = else_if_block_data["id"]
            delete_else_if_btn = dbc.Button([html.I(className="fas fa-times"), " Remove Else If"], id={"type": "delete-else-if-block", "if_command_id": if_command_id, "else_if_block_id": else_if_block_id}, color="danger", outline=True, size="sm", className="ms-auto float-end")
            else_if_conditions = self.create_command_block_layout(html.Span([html.I(className="fas fa-question-circle me-2"), f"Else If ({i+1}) Conditions"]), else_if_block_data.get("conditions", []), if_command_id, {"type": "elseif_conditions", "block_id": else_if_block_id})
            else_if_then = self.create_command_block_layout(html.Span([html.I(className="fas fa-check-circle me-2"), f"Else If ({i+1}) Then"]), else_if_block_data.get("then_commands", []), if_command_id, {"type": "elseif_then", "block_id": else_if_block_id})
            else_if_blocks_layouts.append(dbc.Card([dbc.CardHeader(html.Div([f"Else If Block {i+1}", delete_else_if_btn]), className="bg-light py-2"), dbc.CardBody([else_if_conditions, else_if_then])], className="mb-3"))
        else_block_layout = None
        has_else_block = command_info.get("else_commands") is not None
        if has_else_block:
            delete_else_btn = dbc.Button([html.I(className="fas fa-times"), " Remove Else"], id={"type": "delete-else-block", "if_command_id": if_command_id}, color="danger", outline=True, size="sm", className="ms-auto float-end")
            actual_else_block_content = self.create_command_block_layout(html.Span([html.I(className="fas fa-arrow-right me-2"), "Else"]), command_info.get("else_commands", []), if_command_id, {"type": "if_else"})
            else_block_layout = dbc.Card([dbc.CardHeader(html.Div(["Else Block", delete_else_btn]), className="bg-light py-2"), dbc.CardBody(actual_else_block_content)], className="mb-3")
        if_card_header = dbc.Row([
            dbc.Col(html.Div([html.I(className=f"{icon_class} fa-lg me-3", style={"color": "#6f42c1"}), html.Span(f"Logic: If", style={"fontWeight": "600", "fontSize": "1.1rem"})], className="d-flex align-items-center"), width=True),
            dbc.Col(dbc.Button(html.I(className="fas fa-trash"), id={"type": "delete-command-btn", "command_id": if_command_id}, color="danger", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}), width="auto")
        ], align="center", className="p-2")
        return dbc.Card([dbc.CardHeader(if_card_header, style={"background": "rgba(173, 216, 230, 0.2)"}), dbc.CardBody([condition_block, then_block, html.Div(else_if_blocks_layouts) if else_if_blocks_layouts else "", html.Div(else_block_layout) if else_block_layout else "", dbc.ButtonGroup([dbc.Button([html.I(className="fas fa-plus-circle me-1"), "Add Else If"], id={"type": "add-else-if-block", "if_command_id": if_command_id}, color="info", outline=True, size="sm"), dbc.Button([html.I(className="fas fa-plus-circle me-1"), "Add Else"], id={"type": "add-else-block", "if_command_id": if_command_id}, color="info", outline=True, size="sm", disabled=has_else_block)], className="mt-3")])], className="mb-3 shadow-lg border border-info")

    def create_loop_logic_command_card_layout(self, command_info):
        loop_command_id = command_info["id"]
        icon_class = self.DROPDOWN_ITEM_ICONS.get("logic_loop", "fas fa-sync-alt")
        config = command_info.get("config", {"loop_type": "count", "iterations": 1})
        loop_type = config.get("loop_type", "count")
        iterations = config.get("iterations", 1)
        loop_config_section = html.Div([dbc.Row([dbc.Col(dbc.Label("Loop Type:", html_for=f"loop-type-{loop_command_id}", width="auto"), width=3), dbc.Col(dbc.Select(id={"type": "loop-config-type", "command_id": loop_command_id}, options=[{"label": "Repeat N Times", "value": "count"}, {"label": "Loop Forever", "value": "forever"}], value=loop_type, size="sm"), width=9)], className="mb-2 align-items-center"), dbc.Row([dbc.Col(dbc.Label("Iterations:", html_for=f"loop-iterations-{loop_command_id}", width="auto"), width=3), dbc.Col(dbc.Input(id={"type": "loop-config-iterations", "command_id": loop_command_id}, type="number", min=1, step=1, value=iterations, size="sm", disabled=(loop_type == "forever")), width=9)], style={'display': 'flex' if loop_type == 'count' else 'none'})], style=self.CUSTOM_STYLES['config_section'])
        body_block = self.create_command_block_layout(html.Span([html.I(className="fas fa-cogs me-2"), "Loop Body"]), command_info.get("body_commands", []), loop_command_id, {"type": "loop_body"})
        loop_card_header = dbc.Row([dbc.Col(html.Div([html.I(className=f"{icon_class} fa-lg me-3", style={"color": "#58D68D"}), html.Span(f"Logic: Loop", style={"fontWeight": "600", "fontSize": "1.1rem"})], className="d-flex align-items-center"), width=True), dbc.Col(dbc.Button(html.I(className="fas fa-trash"), id={"type": "delete-command-btn", "command_id": loop_command_id}, color="danger", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}), width="auto")], align="center", className="p-2")
        return dbc.Card([dbc.CardHeader(loop_card_header, style={"background": "rgba(169, 223, 191, 0.3)"}), dbc.CardBody([loop_config_section, body_block])], className="mb-3 shadow-lg border border-success")

    def create_while_logic_command_card_layout(self, command_info):
        while_command_id = command_info["id"]
        icon_class = self.DROPDOWN_ITEM_ICONS.get("logic_while", "fas fa-redo-alt")
        condition_block = self.create_command_block_layout(html.Span([html.I(className="fas fa-question-circle me-2"), "While Condition is True"]), command_info.get("condition_commands", []), while_command_id, {"type": "while_condition"})
        body_block = self.create_command_block_layout(html.Span([html.I(className="fas fa-cogs me-2"), "Do Body"]), command_info.get("body_commands", []), while_command_id, {"type": "while_body"})
        while_card_header = dbc.Row([dbc.Col(html.Div([html.I(className=f"{icon_class} fa-lg me-3", style={"color": "#F5B041"}), html.Span(f"Logic: While", style={"fontWeight": "600", "fontSize": "1.1rem"})], className="d-flex align-items-center"), width=True), dbc.Col(dbc.Button(html.I(className="fas fa-trash"), id={"type": "delete-command-btn", "command_id": while_command_id}, color="danger", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}), width="auto")], align="center", className="p-2")
        return dbc.Card([dbc.CardHeader(while_card_header, style={"background": "rgba(245, 176, 65, 0.2)"}), dbc.CardBody([condition_block, body_block])], className="mb-3 shadow-lg border border-warning")

    def create_logic_command_card_layout(self, command_info):
        subtype = command_info.get("subtype")
        if subtype == "if":
            return self.create_if_logic_command_card_layout(command_info)
        elif subtype == "loop":
            return self.create_loop_logic_command_card_layout(command_info)
        elif subtype == "while":
            return self.create_while_logic_command_card_layout(command_info)
        else:
            return self.create_generic_logic_command_card_layout(command_info)

    def create_math_command_card_layout(self, command_info):
        command_id = command_info["id"]
        subtype = command_info.get("subtype", "Unknown")
        config = command_info.get("config", {"value_a_commands": [], "value_b": 0})
        value_a_commands = config.get("value_a_commands", [])
        value_b = config.get("value_b", 0)
        icon_class = self.DROPDOWN_ITEM_ICONS.get(f"math_{subtype}", self.DROPDOWN_ITEM_ICONS["math_generic"])
        color = "#884EA0"
        subtype_operator_map = {"less_than": "<", "less_than_or_equal_to": "<=", "greater_than": ">", "greater_than_or_equal_to": ">=", "equal_to": "==", "not_equal_to": "!="}
        operator_symbol = subtype_operator_map.get(subtype, "?")
        readable_subtype = subtype.replace('_', ' ').capitalize()
        value_a_block_title = html.Span([html.I(className="fas fa-cube me-2"), "Value A (Should be one value-producing command)"])
        value_a_block = self.create_command_block_layout(value_a_block_title, value_a_commands, command_id, {"type": "math_value_a"}, limit_one=True)
        math_comparison_layout = dbc.Row([dbc.Col(value_a_block, md=5), dbc.Col(html.Div(operator_symbol, style=self.CUSTOM_STYLES['operator_display']), md=2, className="d-flex align-items-center justify-content-center"), dbc.Col(dbc.InputGroup([dbc.Input(id={"type": "math-config-value-b", "command_id": command_id}, placeholder="Value B (Constant)", value=value_b, type="number", size="sm", debounce=True, className="text-center")]), md=5, className="d-flex align-items-center")], align="center", className="my-2")
        math_card_header = dbc.Row([dbc.Col(html.Div([html.I(className=f"{icon_class} fa-lg me-3", style={"color": color}), html.Span(f"Math: {readable_subtype}", style={"fontWeight": "500"})], className="d-flex align-items-center"), width=True), dbc.Col(dbc.Button(html.I(className="fas fa-trash"), id={"type": "delete-command-btn", "command_id": command_id}, color="danger", outline=True, size="sm", style={"borderRadius": "50%", "width": "35px", "height": "35px", "marginLeft": "5px"}), width="auto")], align="center", className="p-2")
        return dbc.Card([dbc.CardHeader(math_card_header, style={"background": "rgba(215, 189, 226, 0.3)"}), dbc.CardBody(math_comparison_layout)], className="mb-2 shadow-lg border", style={"borderColor": color})

    def render_single_command(self, command_info):
        command_type = command_info.get("type")
        if command_type == "move":
            return self.create_move_command_card_layout(command_info)
        if command_type == "battery":
            return self.create_battery_command_card_layout(command_info)
        if command_type == "logic":
            return self.create_logic_command_card_layout(command_info)
        if command_type == "measure":
            return self.create_measure_command_card_layout(command_info)
        if command_type == "plc":
            return self.create_plc_command_card_layout(command_info)
        if command_type == "email":
            return self.create_email_command_card_layout(command_info)
        if command_type == "programming":
            return self.create_programming_command_card_layout(command_info)
        if command_type == "math":
            return self.create_math_command_card_layout(command_info)
        return dbc.Alert(f"Unknown command type '{command_type}' for ID: {command_info.get('id', 'N/A')}", color="danger", className="my-2")

    def create_program_editor_layout(self):
        add_move_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(m.get("name", f"Unnamed: {m['id']}"), self.DROPDOWN_ITEM_ICONS['move_default']), id={"type": "add-move-command-action", "marker_id": m.get("id")}) for m in self.position_markers] if self.position_markers else [dbc.DropdownMenuItem("No positions available", disabled=True)]
        battery_subtypes = [("Docking", "docking"), ("Charging", "charging"), ("Status Battery", "status")]
        battery_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(text, self.DROPDOWN_ITEM_ICONS[f'battery_{subtype}']), id={"type": "add-battery-command-action", "subtype": subtype}) for text, subtype in battery_subtypes]
        logic_subtypes_main = [("If", "if"),("Loop", "loop"), ("While", "while"),("Break", "break"), ("Continue", "continue"), ("Pause", "pause"), ("Return", "return"), ("Wait", "wait")]
        logic_dropdown_items_main = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(text, self.DROPDOWN_ITEM_ICONS[f'logic_{subtype}']), id={"type": "add-logic-command-action", "subtype": subtype}) for text, subtype in logic_subtypes_main]
        math_subtypes_data = [("Less Than (<)", "less_than"), ("Less Than or Equal To (<=)", "less_than_or_equal_to"), ("Greater Than (>)", "greater_than"), ("Greater Than or Equal To (>=)", "greater_than_or_equal_to"), ("Equal To (==)", "equal_to"), ("Not Equal To (!=)", "not_equal_to")]
        math_dropdown_items_main = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(text, self.DROPDOWN_ITEM_ICONS.get(f"math_{subtype}", "fas fa-calculator")), id={"type": "add-math-command-action", "subtype": subtype}) for text, subtype in math_subtypes_data]
        measure_subtypes = [("Distance", "distance"), ("Area", "area"), ("Angle", "angle"), ("Object Detection", "object_detection")]
        measure_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(text, self.DROPDOWN_ITEM_ICONS.get(f"measure_{subtype}", "fas fa-ruler")), id={"type": "add-measure-command-action", "subtype": subtype}) for text, subtype in measure_subtypes]
        plc_subtypes = [("Set PLC Register", "set_register"), ("Set and Reset PLC Register", "set_reset_register"), ("Wait for PLC Register", "wait_register")]
        plc_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon(text, self.DROPDOWN_ITEM_ICONS.get(f"plc_{subtype}", "fas fa-cogs")), id={"type": "add-plc-command-action", "subtype": subtype}) for text, subtype in plc_subtypes]
        email_dropdown_items = [dbc.DropdownMenuItem(self.create_dropdown_item_with_icon("Send Email", self.DROPDOWN_ITEM_ICONS['email_send']), id={"type": "add-email-command-action", "subtype": "send"})]
        programming_dropdown_items_main = self._create_programming_dropdown_items()

        return html.Div([
            html.Div([dbc.Container([dbc.Row([dbc.Col([html.H2([html.I(className="fas fa-code me-3"), "Programming"], className="text-white mb-2", style={"fontWeight": "300"}), html.P("Advanced program configuration", className="text-white-50")], width=6), dbc.Col([dbc.ButtonGroup([dbc.Button([html.I(className="fas fa-arrow-left me-2"), "Go Back"], id="go-back-btn", color="light", outline=True), dbc.Button([html.I(className="fas fa-save me-2"), "Save"], id="save-program-btn", color="success")], className="float-end")], width=6)])])], style={"background": "linear-gradient(135deg, #77B5FE 0%, #4A90E2 100%)", "padding": "2rem 0", "marginBottom": "2rem"}),
            dbc.Row([dbc.Col([html.Label("Program Name:", style={"fontWeight": "500", "color": "#2C3E50", "marginBottom": "5px"}), dbc.Input(id="program-name-input", placeholder="Enter program name", type="text", style=self.CUSTOM_STYLES['input_group'])], width=6)], className="mb-4"),
            dbc.Card([dbc.CardHeader([dbc.Nav([
                        dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-walking me-2"), "Move"]), children=add_move_dropdown_items, nav=True, toggleClassName="fw-bold")),
                        dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-battery-full me-2"), "Battery"]), children=battery_dropdown_items, nav=True, toggleClassName="fw-bold")),
                        dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-brain me-2"), "Logic"]), children=logic_dropdown_items_main, nav=True, toggleClassName="fw-bold")),
                        dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-calculator me-2"), "Math"]), children=math_dropdown_items_main, nav=True, toggleClassName="fw-bold")),
                        dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-ruler-combined me-2"), "Measure"]), children=measure_dropdown_items, nav=True, toggleClassName="fw-bold")),
                        dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-microchip me-2"), "PLC"]), children=plc_dropdown_items, nav=True, toggleClassName="fw-bold")),
                        dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-envelope me-2"), "Email"]), children=email_dropdown_items, nav=True, toggleClassName="fw-bold")),
                        dbc.NavItem(dbc.DropdownMenu(label=html.Span([html.I(className="fas fa-tasks me-2"), "Programming"]), children=programming_dropdown_items_main, nav=True, toggleClassName="fw-bold")),
                    ], pills=True)], style={"background": "#f8f9fa"})], style={**self.CUSTOM_STYLES['card'], "position": "sticky", "top":"10px", "zIndex": 1020}, className="mb-4"),
            dbc.Card([dbc.CardHeader([dbc.Row([dbc.Col(html.H5([html.I(className="fas fa-stream me-2", style={"color": "#77B5FE"}), "Program Flow"], className="mb-0", style={"fontWeight": "600"}))])], style={"background": "linear-gradient(45deg, #e3f2fd, #77B5FE)"}), dbc.CardBody([html.H6("Program Commands:", className="mb-3 mt-4", style={"fontWeight": "600"}), html.Div(id="program-commands-container", children=[])])], style={**self.CUSTOM_STYLES['card'], "position": "relative", "zIndex": 1}, className="mb-4")
        ], style=self.CUSTOM_STYLES['main_content'])