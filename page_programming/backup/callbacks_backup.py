import dash
from dash import dcc, html, Input, Output, callback, State, ALL, MATCH, ctx
import dash_bootstrap_components as dbc
import json
import uuid
import copy
import os 

# MODIFIED: Import LayoutManager class
from layout_backup import LayoutManager

# MODIFIED: Instantiate LayoutManager
layout_manager = LayoutManager()

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME], suppress_callback_exceptions=True)

# Main app layout
app.layout = html.Div([
    dcc.Location(id="url_program", refresh=False),
    html.Div(id="page-content-program"),
    dcc.Store(id="page-state", data={"current_page": "main"}),
    dcc.Store(id="program-commands-store", data=[]),
    dcc.Store(id="editing-program-name-store", data=None), 
    dcc.Store(id="save-status-store"), 
    html.Div(id="toast-container", style={"position": "fixed", "top": 20, "right": 20, "zIndex": 1050}),
    
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Confirm Deletion")),
            dbc.ModalBody(id="delete-modal-body-content"), 
            dbc.ModalFooter([
                dbc.Button("Cancel", id="cancel-delete-modal-btn", color="secondary", className="ms-auto"),
                dbc.Button("Confirm Delete", id="confirm-delete-modal-btn", color="danger"),
            ]),
        ],
        id="delete-program-confirm-modal", is_open=False,
    ),
    dcc.Store(id="program-to-delete-store", data=None), 
    dcc.Store(id="programs-list-refresh-flag", data=0),

    # Modal for Play Program action
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Queue Program Action")),
            dbc.ModalBody(id="play-modal-body-content"),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="cancel-play-modal-btn", color="secondary", outline=True),
                dbc.Button("Append to Queue", id="append-to-queue-btn", color="primary", className="ms-auto"),
                dbc.Button("Clear & Append to Queue", id="clear-and-append-to-queue-btn", color="warning"),
            ]),
        ],
        id="play-program-action-modal", is_open=False,
    ),
    dcc.Store(id="program-to-play-store", data=None),
    dcc.Store(id="queue-refresh-flag", data=0),
])

# --- Navigation Callbacks ---
@callback(
    Output("programs-list", "children"), 
    [Input("url_program", "pathname"), Input("programs-list-refresh-flag", "data")]
)
def update_programs_list(pathname, refresh_flag): 
    if pathname == "/" or pathname == "/main": 
        # MODIFIED: Access programs_data via layout_manager instance
        current_programs_list = layout_manager.programs_data 
        if not current_programs_list:
             return dbc.Alert("No programs found or error loading programs.", color="warning", className="mt-3 text-center")
        # MODIFIED: Use layout_manager method
        return [layout_manager.create_program_card(program) for program in current_programs_list]
    return [] 

@callback(
    [Output("page-content-program", "children"), Output("page-state", "data")],
    [Input("url_program", "pathname")], [State("page-state", "data")],
    prevent_initial_call=False 
)
def display_page(pathname, page_state_data):
    current_view = page_state_data.get("current_page", "main") if page_state_data else "main"
    # MODIFIED: Use layout_manager method
    if pathname == "/" or pathname is None: return layout_manager.create_main_layout(), {"current_page": "main"}
    elif pathname == "/editor": 
        if current_view == "editor": return dash.no_update, dash.no_update 
        # MODIFIED: Use layout_manager method
        else: return layout_manager.create_main_layout(), {"current_page": "main"} # Fallback to main if navigated directly
    # MODIFIED: Use layout_manager method
    return layout_manager.create_main_layout(), {"current_page": "main"} 

@callback(
    [Output("page-content-program", "children", allow_duplicate=True), Output("page-state", "data", allow_duplicate=True), Output("program-commands-store", "data", allow_duplicate=True), Output("editing-program-name-store", "data", allow_duplicate=True)],
    [Input("create-program-btn", "n_clicks")],
    prevent_initial_call=True
)
def go_to_editor_for_new_program(n_clicks):
    if n_clicks:
        # MODIFIED: Use layout_manager method
        return (layout_manager.create_program_editor_layout(), {"current_page": "editor"}, [], None)
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update

@callback(
    [Output("url_program", "pathname", allow_duplicate=True), Output("page-state", "data", allow_duplicate=True), Output("editing-program-name-store", "data", allow_duplicate=True)],
    [Input("go-back-btn", "n_clicks")],
    prevent_initial_call=True
)
def go_back_to_main_and_clear_edit_state(n_clicks):
    if n_clicks: return "/", {"current_page": "main"}, None 
    return dash.no_update, dash.no_update, dash.no_update

@callback(
    [Output("page-content-program", "children", allow_duplicate=True), Output("page-state", "data", allow_duplicate=True), Output("program-commands-store", "data", allow_duplicate=True), Output("editing-program-name-store", "data", allow_duplicate=True)],
    [Input({"type": "edit-program-btn", "program_name": ALL}, "n_clicks")],
    prevent_initial_call=True
)
def load_editor_for_existing_program(n_clicks_edit_buttons):
    if not ctx.triggered_id or not ctx.triggered[0]['value']: return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    program_name_to_edit = ctx.triggered_id["program_name"]
    # MODIFIED: Access programs_data via layout_manager instance
    current_programs_list = layout_manager.programs_data
    program_to_edit = next((p for p in current_programs_list if isinstance(p, dict) and p.get("name") == program_name_to_edit), None)
    if program_to_edit:
        commands_to_load = program_to_edit.get("commands", [])
        # MODIFIED: Use layout_manager method
        return (layout_manager.create_program_editor_layout(), {"current_page": "editor"}, commands_to_load, program_name_to_edit)
    else: 
        # MODIFIED: Use layout_manager method
        return (layout_manager.create_program_editor_layout(), {"current_page": "editor", "error_message": f"Program '{program_name_to_edit}' not found."}, [], None)

@callback(
    Output("program-name-input", "value"), 
    [Input("editing-program-name-store", "data"), Input("page-state", "data")], 
    prevent_initial_call=True
)
def update_program_name_input_on_editor_load(editing_program_name, page_state_data):
    if page_state_data and page_state_data.get("current_page") == "editor":
        return editing_program_name if editing_program_name is not None else ""
    return dash.no_update

# --- Recursive Helper Functions for Command Store (Unchanged) ---
def find_command_recursive(commands_list, command_id): # ... (same)
    for cmd in commands_list:
        if not cmd: continue
        if cmd.get("id") == command_id: return cmd
        cmd_type = cmd.get("type"); cmd_subtype = cmd.get("subtype")
        if cmd_type == "logic":
            if cmd_subtype == "if":
                if (res := find_command_recursive(cmd.get("conditions", []), command_id)): return res
                if (res := find_command_recursive(cmd.get("then_commands", []), command_id)): return res
                for elseif_block in cmd.get("else_if_blocks", []):
                    if (res := find_command_recursive(elseif_block.get("conditions", []), command_id)): return res
                    if (res := find_command_recursive(elseif_block.get("then_commands", []), command_id)): return res
                if cmd.get("else_commands") is not None and (res := find_command_recursive(cmd.get("else_commands", []), command_id)): return res
            elif cmd_subtype == "loop" and (res := find_command_recursive(cmd.get("body_commands", []), command_id)): return res
            elif cmd_subtype == "while":
                if (res := find_command_recursive(cmd.get("condition_commands", []), command_id)): return res
                if (res := find_command_recursive(cmd.get("body_commands", []), command_id)): return res
        elif cmd_type == "math" and (res := find_command_recursive(cmd.get("config", {}).get("value_a_commands", []), command_id)): return res
    return None

def update_command_recursive(commands_list, command_id_to_update, update_func): # ... (same)
    for i, cmd in enumerate(commands_list):
        if not cmd: continue
        if cmd.get("id") == command_id_to_update:
            updated_cmd = update_func(copy.deepcopy(cmd))
            if updated_cmd: commands_list[i] = updated_cmd
            return True
        cmd_type = cmd.get("type"); cmd_subtype = cmd.get("subtype")
        if cmd_type == "logic" or cmd_type == "math": 
            current_cmd_copy = copy.deepcopy(cmd); updated_in_child = False
            if cmd_type == "logic":
                if cmd_subtype == "if":
                    if update_command_recursive(current_cmd_copy.setdefault("conditions", []), command_id_to_update, update_func): updated_in_child = True
                    elif update_command_recursive(current_cmd_copy.setdefault("then_commands", []), command_id_to_update, update_func): updated_in_child = True
                    else:
                        for elseif_block in current_cmd_copy.setdefault("else_if_blocks", []):
                            if update_command_recursive(elseif_block.setdefault("conditions", []), command_id_to_update, update_func): updated_in_child = True; break
                            if update_command_recursive(elseif_block.setdefault("then_commands", []), command_id_to_update, update_func): updated_in_child = True; break
                        if not updated_in_child and current_cmd_copy.get("else_commands") is not None and update_command_recursive(current_cmd_copy.setdefault("else_commands", []), command_id_to_update, update_func): updated_in_child = True
                elif cmd_subtype == "loop" and update_command_recursive(current_cmd_copy.setdefault("body_commands", []), command_id_to_update, update_func): updated_in_child = True
                elif cmd_subtype == "while":
                    if update_command_recursive(current_cmd_copy.setdefault("condition_commands", []), command_id_to_update, update_func): updated_in_child = True
                    elif update_command_recursive(current_cmd_copy.setdefault("body_commands", []), command_id_to_update, update_func): updated_in_child = True
            elif cmd_type == "math" and update_command_recursive(current_cmd_copy.get("config", {}).setdefault("value_a_commands", []), command_id_to_update, update_func): updated_in_child = True
            if updated_in_child: commands_list[i] = current_cmd_copy; return True
    return False

def delete_command_recursive(commands_list, command_id_to_delete): # ... (same)
    original_len = len(commands_list); commands_list[:] = [cmd for cmd in commands_list if cmd and cmd.get("id") != command_id_to_delete]; action_taken = len(commands_list) < original_len
    for cmd in commands_list:
        if not cmd: continue
        cmd_type = cmd.get("type"); cmd_subtype = cmd.get("subtype")
        if cmd_type == "logic":
            if cmd_subtype == "if":
                if delete_command_recursive(cmd.setdefault("conditions", []), command_id_to_delete): action_taken = True
                if delete_command_recursive(cmd.setdefault("then_commands", []), command_id_to_delete): action_taken = True
                for elseif_block in cmd.setdefault("else_if_blocks", []):
                    if delete_command_recursive(elseif_block.setdefault("conditions", []), command_id_to_delete): action_taken = True
                    if delete_command_recursive(elseif_block.setdefault("then_commands", []), command_id_to_delete): action_taken = True
                if cmd.get("else_commands") is not None and delete_command_recursive(cmd.setdefault("else_commands", []), command_id_to_delete): action_taken = True
            elif cmd_subtype == "loop" and delete_command_recursive(cmd.setdefault("body_commands", []), command_id_to_delete): action_taken = True
            elif cmd_subtype == "while":
                if delete_command_recursive(cmd.setdefault("condition_commands", []), command_id_to_delete): action_taken = True
                if delete_command_recursive(cmd.setdefault("body_commands", []), command_id_to_delete): action_taken = True
        elif cmd_type == "math" and delete_command_recursive(cmd.get("config", {}).setdefault("value_a_commands", []), command_id_to_delete): action_taken = True
    return action_taken

def add_command_to_target(commands_list, target_parent_id, target_block_spec, new_command): # ... (same)
    for cmd in commands_list:
        if not cmd: continue
        cmd_id, cmd_type, cmd_subtype = cmd.get("id"), cmd.get("type"), cmd.get("subtype")
        if cmd_id == target_parent_id:
            block_type = target_block_spec["type"]
            if cmd_type == "logic":
                if cmd_subtype == "if":
                    if block_type == "if_conditions": cmd.setdefault("conditions", []).append(new_command); return True
                    if block_type == "if_then": cmd.setdefault("then_commands", []).append(new_command); return True
                    if block_type == "if_else": cmd.setdefault("else_commands", []).append(new_command); return True
                    if block_type in ["elseif_conditions", "elseif_then"]:
                        block_id = target_block_spec["block_id"]
                        for elseif_block in cmd.setdefault("else_if_blocks", []):
                            if elseif_block["id"] == block_id:
                                if block_type == "elseif_conditions": elseif_block.setdefault("conditions", []).append(new_command); return True
                                if block_type == "elseif_then": elseif_block.setdefault("then_commands", []).append(new_command); return True
                        return False
                elif cmd_subtype == "loop" and block_type == "loop_body": cmd.setdefault("body_commands", []).append(new_command); return True
                elif cmd_subtype == "while":
                    if block_type == "while_condition": cmd.setdefault("condition_commands", []).append(new_command); return True
                    if block_type == "while_body": cmd.setdefault("body_commands", []).append(new_command); return True
            elif cmd_type == "math" and block_type == "math_value_a":
                value_a_cmds = cmd.get("config", {}).setdefault("value_a_commands", [])
                if not value_a_cmds: value_a_cmds.append(new_command); return True
                else: return False 
            return False
        target_found_in_child = False
        if cmd_type == "logic":
            if cmd_subtype == "if":
                if add_command_to_target(cmd.get("conditions", []), target_parent_id, target_block_spec, new_command): target_found_in_child = True
                elif add_command_to_target(cmd.get("then_commands", []), target_parent_id, target_block_spec, new_command): target_found_in_child = True
                else:
                    for elseif_block in cmd.get("else_if_blocks", []):
                        if add_command_to_target(elseif_block.get("conditions", []), target_parent_id, target_block_spec, new_command): target_found_in_child = True; break
                        if add_command_to_target(elseif_block.get("then_commands", []), target_parent_id, target_block_spec, new_command): target_found_in_child = True; break
                    if not target_found_in_child and cmd.get("else_commands") is not None and add_command_to_target(cmd.get("else_commands", []), target_parent_id, target_block_spec, new_command): target_found_in_child = True
            elif cmd_subtype == "loop" and add_command_to_target(cmd.get("body_commands", []), target_parent_id, target_block_spec, new_command): target_found_in_child = True
            elif cmd_subtype == "while":
                if add_command_to_target(cmd.get("condition_commands", []), target_parent_id, target_block_spec, new_command): target_found_in_child = True
                elif add_command_to_target(cmd.get("body_commands", []), target_parent_id, target_block_spec, new_command): target_found_in_child = True
        elif cmd_type == "math" and add_command_to_target(cmd.get("config", {}).get("value_a_commands", []), target_parent_id, target_block_spec, new_command): target_found_in_child = True
        if target_found_in_child: return True
    return False

# --- Generic Command Adder ---
def _add_command_to_store(n_clicks_all_tuple, current_commands_orig, command_type_being_added): # ... (same)
    if not ctx.triggered_id or not any(n for n_list in n_clicks_all_tuple for n in n_list if n is not None): return dash.no_update
    item_id_dict = ctx.triggered_id; subtype_to_add = item_id_dict.get("subtype"); marker_id_to_add = item_id_dict.get("marker_id"); target_parent_id = item_id_dict.get("target_parent_id"); target_block_spec_json = item_id_dict.get("target_block_spec")
    if command_type_being_added == "move" and marker_id_to_add is None: return dash.no_update
    required_subtype_types = ["logic", "battery", "measure", "plc", "email", "programming", "math"]
    if command_type_being_added in required_subtype_types and subtype_to_add is None: return dash.no_update
    new_command_id = str(uuid.uuid4()); new_command = {"id": new_command_id, "type": command_type_being_added, "config": {}}
    if command_type_being_added == "move": new_command["marker_id"] = marker_id_to_add
    elif command_type_being_added == "logic":
        new_command["subtype"] = subtype_to_add
        if subtype_to_add == "if": new_command["conditions"], new_command["then_commands"], new_command["else_if_blocks"], new_command["else_commands"] = [], [], [], None
        elif subtype_to_add == "loop": new_command["config"] = {"loop_type": "count", "iterations": 1}; new_command["body_commands"] = []
        elif subtype_to_add == "while": new_command["condition_commands"], new_command["body_commands"] = [], []
    elif command_type_being_added == "math": new_command["subtype"] = subtype_to_add; new_command["config"] = {"value_a_commands": [], "value_b": 0} 
    elif command_type_being_added == "programming": 
        new_command["subtype"] = subtype_to_add
        if subtype_to_add == "call_program":
            program_name_to_call = item_id_dict.get("program_name_to_call")
            if program_name_to_call: new_command["config"] = {"called_program_name": program_name_to_call}
            else: new_command["config"] = {"called_program_name": "Error: Program Name Missing"} 
        elif subtype_to_add == "custom_code": new_command["config"] = {"code": ""} 
        else: new_command["config"] = {} 
    else: new_command["subtype"] = subtype_to_add
    current_commands = copy.deepcopy(current_commands_orig or [])
    if target_parent_id and target_block_spec_json:
        try:
            target_block_spec = json.loads(target_block_spec_json)
            if not add_command_to_target(current_commands, target_parent_id, target_block_spec, new_command): return dash.no_update
        except json.JSONDecodeError: return dash.no_update
    else: current_commands.append(new_command)
    return current_commands

# --- Specific Command Adder Callbacks (Unchanged) ---
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-move-command-action", "marker_id": ALL, "target_parent_id": ALL, "target_block_spec": ALL}, "n_clicks"), Input({"type": "add-move-command-action", "marker_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_move_command(n_nested, n_root, s): return _add_command_to_store((n_nested, n_root), s, "move")
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-battery-command-action", "subtype": ALL, "target_parent_id": ALL, "target_block_spec": ALL}, "n_clicks"), Input({"type": "add-battery-command-action", "subtype": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_battery_command(n_nested, n_root, s): return _add_command_to_store((n_nested, n_root), s, "battery")
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-logic-command-action", "subtype": ALL, "target_parent_id": ALL, "target_block_spec": ALL}, "n_clicks"), Input({"type": "add-logic-command-action", "subtype": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_logic_command(n_nested, n_root, s): return _add_command_to_store((n_nested, n_root), s, "logic")
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-measure-command-action", "subtype": ALL, "target_parent_id": ALL, "target_block_spec": ALL}, "n_clicks"), Input({"type": "add-measure-command-action", "subtype": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_measure_command(n_nested, n_root, s): return _add_command_to_store((n_nested, n_root), s, "measure")
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-plc-command-action", "subtype": ALL, "target_parent_id": ALL, "target_block_spec": ALL}, "n_clicks"), Input({"type": "add-plc-command-action", "subtype": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_plc_command(n_nested, n_root, s): return _add_command_to_store((n_nested, n_root), s, "plc")
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-email-command-action", "subtype": ALL, "target_parent_id": ALL, "target_block_spec": ALL}, "n_clicks"), Input({"type": "add-email-command-action", "subtype": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_email_command(n_nested, n_root, s): return _add_command_to_store((n_nested, n_root), s, "email")
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-programming-command-action", "subtype": ALL, "program_name_to_call": ALL, "target_parent_id": ALL, "target_block_spec": ALL}, "n_clicks"), Input({"type": "add-programming-command-action", "subtype": ALL, "program_name_to_call": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_programming_command(n_nested, n_root, s): return _add_command_to_store((n_nested, n_root), s, "programming")
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-math-command-action", "subtype": ALL, "target_parent_id": ALL, "target_block_spec": ALL}, "n_clicks"), Input({"type": "add-math-command-action", "subtype": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_math_command(n_nested, n_root, s): return _add_command_to_store((n_nested, n_root), s, "math")

@callback(Output("program-commands-container", "children"), [Input("program-commands-store", "data")])
def render_program_commands_from_store(commands_data):
    if not commands_data: return dbc.Alert("No program commands added yet.", color="info", className="mt-3 text-center")
    # MODIFIED: Use layout_manager method
    return [layout_manager.render_single_command(cmd_data) for cmd_data in commands_data if cmd_data]

@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "change-position-marker", "command_id": ALL, "marker_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def change_command_position(n_clicks_all, current_commands_orig): # ... (same)
    if not ctx.triggered_id or not any(n for n in n_clicks_all if n is not None) or not current_commands_orig: return dash.no_update
    item_id_dict, new_marker_id = ctx.triggered_id, ctx.triggered_id["marker_id"]; command_id_to_change = item_id_dict["command_id"]; current_commands = copy.deepcopy(current_commands_orig)
    def update_marker_in_cmd(cmd_to_update):
        if cmd_to_update.get("type") == "move": cmd_to_update["marker_id"] = new_marker_id
        return cmd_to_update
    if update_command_recursive(current_commands, command_id_to_change, update_marker_in_cmd): return current_commands
    return dash.no_update

@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "delete-command-btn", "command_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def delete_program_command(n_clicks_all, current_commands_orig): # ... (same)
    if not ctx.triggered_id or not any(n for n in n_clicks_all if n is not None) or not current_commands_orig: return dash.no_update
    command_id_to_delete = ctx.triggered_id["command_id"]; current_commands = copy.deepcopy(current_commands_orig)
    if delete_command_recursive(current_commands, command_id_to_delete): return current_commands
    return dash.no_update

# --- Callbacks for IF Block Management (Unchanged) ---
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-else-if-block", "if_command_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_else_if_block(n,s): # ... (same)
    if not ctx.triggered_id or not any(_n for _n in n if _n): return dash.no_update
    s_copy=copy.deepcopy(s); id=ctx.triggered_id["if_command_id"]
    def fn(cmd): cmd.setdefault("else_if_blocks",[]).append({"id":str(uuid.uuid4()),"conditions":[],"then_commands":[]}); return cmd
    if update_command_recursive(s_copy,id,fn): return s_copy
    return dash.no_update
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-else-block", "if_command_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_else_block(n,s): # ... (same)
    if not ctx.triggered_id or not any(_n for _n in n if _n): return dash.no_update
    s_copy=copy.deepcopy(s); id=ctx.triggered_id["if_command_id"]
    def fn(cmd):
        if cmd.get("else_commands") is None: cmd["else_commands"]=[]
        return cmd
    if update_command_recursive(s_copy,id,fn): return s_copy
    return dash.no_update
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "delete-else-if-block", "if_command_id": ALL, "else_if_block_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def delete_else_if_block(n,s): # ... (same)
    if not ctx.triggered_id or not any(_n for _n in n if _n): return dash.no_update
    s_copy=copy.deepcopy(s); if_id=ctx.triggered_id["if_command_id"]; else_if_id=ctx.triggered_id["else_if_block_id"]
    def fn(cmd):
        if "else_if_blocks" in cmd: cmd["else_if_blocks"]=[b for b in cmd["else_if_blocks"] if b["id"]!=else_if_id]
        return cmd
    if update_command_recursive(s_copy,if_id,fn): return s_copy
    return dash.no_update
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "delete-else-block", "if_command_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def delete_else_block(n,s): # ... (same)
    if not ctx.triggered_id or not any(_n for _n in n if _n): return dash.no_update
    s_copy=copy.deepcopy(s); id=ctx.triggered_id["if_command_id"]
    def fn(cmd):
        if "else_commands" in cmd: cmd["else_commands"]=None
        return cmd
    if update_command_recursive(s_copy,id,fn): return s_copy
    return dash.no_update

@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "loop-config-type", "command_id": ALL}, "value"), Input({"type": "loop-config-iterations", "command_id": ALL}, "value")], [State("program-commands-store", "data")], prevent_initial_call=True)
def update_loop_configuration(loop_types, iter_values, s_orig): # ... (same)
    if not ctx.triggered_id or not s_orig: return dash.no_update
    s=copy.deepcopy(s_orig); prop=ctx.triggered_id["type"]; cmd_id=ctx.triggered_id["command_id"]; val=ctx.triggered[0]['value']
    if val is None : return dash.no_update 
    def fn(cmd):
        if cmd.get("type")=="logic" and cmd.get("subtype")=="loop":
            cmd.setdefault("config",{})
            if prop=="loop-config-type": cmd["config"]["loop_type"]=val; (cmd["config"].pop("iterations", None) if val=="forever" else None) # remove iterations if forever
            elif prop=="loop-config-iterations":
                try: cmd["config"]["iterations"]=int(val) if val is not None and str(val).strip()!="" else 1
                except ValueError: cmd["config"]["iterations"]=1 
        return cmd
    if update_command_recursive(s,cmd_id,fn): return s
    return dash.no_update

@callback(Output("program-commands-store", "data", allow_duplicate=True), Input({"type": "math-config-value-b", "command_id": ALL}, "value"), State("program-commands-store", "data"), prevent_initial_call=True)
def update_math_command_value_b(value_b_inputs, current_commands_orig): # ... (same)
    if not ctx.triggered_id or not current_commands_orig: return dash.no_update
    command_id_to_update = ctx.triggered_id["command_id"]; new_value_b = ctx.triggered[0]['value']; current_commands = copy.deepcopy(current_commands_orig)
    def update_math_value_b_in_cmd(math_cmd):
        if math_cmd.get("type") == "math":
            math_cmd.setdefault("config", {"value_a_commands": [], "value_b": 0})
            try: math_cmd["config"]["value_b"] = float(new_value_b) if new_value_b is not None and str(new_value_b).strip() != "" else 0
            except (ValueError, TypeError): math_cmd["config"]["value_b"] = 0
        return math_cmd
    if update_command_recursive(current_commands, command_id_to_update, update_math_value_b_in_cmd): return current_commands
    return dash.no_update

@callback(
    [Output("save-status-store", "data"), Output("editing-program-name-store", "data", allow_duplicate=True)], 
    Input("save-program-btn", "n_clicks"),
    [State("program-name-input", "value"), State("program-commands-store", "data"), State("editing-program-name-store", "data")],
    prevent_initial_call=True
)
def save_program_to_file(n_clicks, program_name_input, commands_data, original_program_name):
    if not n_clicks: return dash.no_update, dash.no_update
    program_name = program_name_input.strip() if program_name_input else ""
    if not program_name: return {"message": "Program name cannot be empty.", "color": "warning", "icon": "exclamation-circle"}, dash.no_update
    
    # Use file path from layout_manager instance for consistency
    file_path = layout_manager.programs_file_path
    db_path = os.path.dirname(file_path) # Get db_path from the file_path

    try:
        os.makedirs(db_path, exist_ok=True); all_progs = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
                if content.strip(): all_progs = json.loads(content)
                if not isinstance(all_progs, list): all_progs = []
            except (json.JSONDecodeError, Exception): all_progs = []
        
        if (original_program_name and original_program_name != program_name and any(p.get("name") == program_name for p in all_progs)) or \
           (not original_program_name and any(p.get("name") == program_name for p in all_progs)):
            return {"message": f"Program name '{program_name}' already exists.", "color": "warning", "icon": "exclamation-circle"}, dash.no_update
        
        new_data = {"name": program_name, "commands": commands_data if commands_data else []}; found = False
        if original_program_name:
            for i,p in enumerate(all_progs):
                if isinstance(p,dict) and p.get("name")==original_program_name: all_progs[i]=new_data; found=True; break
            if not found: all_progs.append(new_data) 
        else: all_progs.append(new_data)
        
        with open(file_path, 'w', encoding='utf-8') as f: json.dump(all_progs, f, indent=4)
        
        # MODIFIED: Use layout_manager method to reload its internal data
        layout_manager.reload_programs_data(file_path) 
        
        return {"message": f"Program '{program_name}' saved successfully!", "color": "success", "icon": "check-circle"}, program_name
    except Exception as e: return {"message": f"Error saving program: {str(e)}", "color": "danger", "icon": "times-circle"}, dash.no_update

# --- Callbacks for Program Deletion ---
@callback(
    [Output("delete-program-confirm-modal", "is_open"), Output("program-to-delete-store", "data"), Output("delete-modal-body-content", "children")],
    Input({"type": "delete-program-main-btn", "program_name": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def open_delete_confirmation_modal(n_clicks_delete_buttons): # ... (same)
    if not ctx.triggered_id or not ctx.triggered[0]['value']: return False, None, ""
    program_name_to_delete = ctx.triggered_id["program_name"]
    modal_body = f"Are you sure you want to delete the program: '{program_name_to_delete}'? This action cannot be undone."
    return True, program_name_to_delete, modal_body

@callback(
    [Output("delete-program-confirm-modal", "is_open", allow_duplicate=True), Output("program-to-delete-store", "data", allow_duplicate=True)],
    Input("cancel-delete-modal-btn", "n_clicks"),
    prevent_initial_call=True
)
def close_delete_confirmation_modal(n_clicks_cancel): # ... (same)
    if n_clicks_cancel: return False, None
    return dash.no_update, dash.no_update

@callback(
    [Output("delete-program-confirm-modal", "is_open", allow_duplicate=True), Output("program-to-delete-store", "data", allow_duplicate=True), Output("save-status-store", "data", allow_duplicate=True), Output("programs-list-refresh-flag", "data")],
    Input("confirm-delete-modal-btn", "n_clicks"),
    [State("program-to-delete-store", "data"), State("programs-list-refresh-flag", "data")],
    prevent_initial_call=True
)
def handle_confirm_delete_program(n_clicks_confirm, program_name_to_delete, current_refresh_flag):
    if not n_clicks_confirm or not program_name_to_delete: return False, None, dash.no_update, dash.no_update
    
    # Use file path from layout_manager instance
    file_path = layout_manager.programs_file_path
    toast_data = {}
    try:
        all_programs = [];
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
                if content.strip(): all_programs = json.loads(content)
                if not isinstance(all_programs, list): all_programs = [] 
            except (json.JSONDecodeError, Exception) as e: all_programs = [] 
        
        updated_programs = [prog for prog in all_programs if isinstance(prog, dict) and prog.get("name") != program_name_to_delete]
        if len(updated_programs) < len(all_programs): 
            with open(file_path, 'w', encoding='utf-8') as f: json.dump(updated_programs, f, indent=4)
            
            # MODIFIED: Use layout_manager method to reload its internal data
            layout_manager.reload_programs_data(file_path)
            
            toast_data = {"message": f"Program '{program_name_to_delete}' deleted successfully!", "color": "success", "icon": "check-circle"}
        else: toast_data = {"message": f"Program '{program_name_to_delete}' not found for deletion.", "color": "warning", "icon": "exclamation-circle"}
        return False, None, toast_data, current_refresh_flag + 1
    except Exception as e:
        toast_data = {"message": f"Error deleting program: {str(e)}", "color": "danger", "icon": "times-circle"}
        return False, program_name_to_delete, toast_data, dash.no_update


# --- Callbacks for Play Program (Queueing) ---
@callback(
    [Output("play-program-action-modal", "is_open"),
     Output("program-to-play-store", "data"),
     Output("play-modal-body-content", "children")],
    Input({"type": "run-program-main-btn", "program_name": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def open_play_action_modal(n_clicks_run_buttons):
    if not ctx.triggered_id or not ctx.triggered[0]['value']:
        return False, None, ""

    program_name_to_play = ctx.triggered_id["program_name"]
    modal_body = f"Choose an action for program: '{program_name_to_play}'."
    
    return True, program_name_to_play, modal_body

@callback(
    [Output("play-program-action-modal", "is_open", allow_duplicate=True),
     Output("program-to-play-store", "data", allow_duplicate=True)],
    Input("cancel-play-modal-btn", "n_clicks"),
    prevent_initial_call=True
)
def close_play_action_modal(n_clicks_cancel):
    if n_clicks_cancel:
        return False, None
    return dash.no_update, dash.no_update

@callback(
    [Output("play-program-action-modal", "is_open", allow_duplicate=True),
     Output("program-to-play-store", "data", allow_duplicate=True),
     Output("save-status-store", "data", allow_duplicate=True), 
     Output("queue-refresh-flag", "data")],
    [Input("append-to-queue-btn", "n_clicks"),
     Input("clear-and-append-to-queue-btn", "n_clicks")],
    [State("program-to-play-store", "data"),
     State("queue-refresh-flag", "data")],
    prevent_initial_call=True
)
def handle_queue_program_action(n_append, n_clear_append, program_name_to_play, current_queue_refresh_flag):
    if not (n_append or n_clear_append) or not program_name_to_play:
        return False, None, dash.no_update, current_queue_refresh_flag 

    action = None
    if ctx.triggered_id == "append-to-queue-btn":
        action = "append"
    elif ctx.triggered_id == "clear-and-append-to-queue-btn":
        action = "clear_append"
    
    if not action:
        return False, program_name_to_play, {"message": "Invalid action.", "color": "danger", "icon": "times-circle"}, current_queue_refresh_flag

    # Use file paths from layout_manager for consistency
    queue_file_path = layout_manager.queue_file_path
    db_path = os.path.dirname(queue_file_path) # Infer db_path
    toast_data = {}

    try:
        # MODIFIED: Access programs_data from layout_manager
        all_programs = layout_manager.programs_data
        
        program_data_to_queue = next((p for p in all_programs if isinstance(p, dict) and p.get("name") == program_name_to_play), None)

        if not program_data_to_queue:
            toast_data = {"message": f"Program '{program_name_to_play}' not found in library.", "color": "danger", "icon": "times-circle"}
            return False, None, toast_data, current_queue_refresh_flag

        current_queue = []
        if os.path.exists(queue_file_path):
            try:
                with open(queue_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        current_queue = json.loads(content)
                if not isinstance(current_queue, list):
                    current_queue = [] 
            except (json.JSONDecodeError, Exception) as e:
                print(f"Error reading queue file '{queue_file_path}', initializing empty queue: {e}")
                current_queue = []
        
        if action == "clear_append":
            current_queue = []
        
        current_queue.append(program_data_to_queue)

        os.makedirs(db_path, exist_ok=True) 
        with open(queue_file_path, 'w', encoding='utf-8') as f:
            json.dump(current_queue, f, indent=4)

        action_text = "appended to" if action == "append" else "cleared and program added to"
        toast_data = {"message": f"Program '{program_name_to_play}' {action_text} queue.", "color": "success", "icon": "check-circle"}
        print(f"Program '{program_name_to_play}' {action_text} queue at '{queue_file_path}'.")
        
        return False, None, toast_data, current_queue_refresh_flag + 1

    except Exception as e:
        print(f"Error queueing program '{program_name_to_play}': {e}")
        toast_data = {"message": f"Error queueing program: {str(e)}", "color": "danger", "icon": "times-circle"}
        return False, program_name_to_play, toast_data, current_queue_refresh_flag


# --- NEW Callback to display program queue ---
@callback(
    Output("program-queue-list", "children"),
    [Input("url_program", "pathname"), Input("queue-refresh-flag", "data")]
)
def update_program_queue_display(pathname, refresh_flag):
    if pathname == "/" or pathname == "/main": 
        # MODIFIED: Use layout_manager method
        queued_programs = layout_manager.load_queued_programs_from_file()
        
        if not queued_programs:
            return html.P("The queue is empty.", className="text-muted fst-italic text-center mt-2")
        
        # MODIFIED: Use layout_manager method
        queue_items_display = [
            layout_manager.create_queued_program_mini_card(prog, idx) for idx, prog in enumerate(queued_programs)
        ]
        return dbc.ListGroup(queue_items_display, flush=True, style={"maxHeight": "400px", "overflowY": "auto", "borderTop": "1px solid #eee", "paddingTop": "10px"})
    return dash.no_update


# --- Toast Display Callback (Unchanged) ---
@callback(
    Output("toast-container", "children"),
    Input("save-status-store", "data"),
    prevent_initial_call=True
)
def show_save_toast(status_data):
    if status_data:
        message = status_data.get("message", "An error occurred."); color = status_data.get("color", "danger"); icon = status_data.get("icon", "info-circle") 
        return dbc.Toast(message, id="save-toast", header="Program Status", is_open=True, dismissable=True, duration=4000, icon=f"fas fa-{icon}", color=color, style={"maxWidth": "350px"})
    return dash.no_update


if __name__ == "__main__":
    app.run(debug=True, port=8050)