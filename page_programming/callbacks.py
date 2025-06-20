import dash
from dash import dcc, html, Input, Output, callback, State, ALL, MATCH, ctx
import dash_bootstrap_components as dbc
import json
import uuid
import copy
import os 

from page_programming.layout import LayoutManager

layout_manager = LayoutManager()


# --- Navigation Callbacks ---
@callback(
    Output("programs-list", "children"), 
    [Input("url_program", "pathname"), Input("programs-list-refresh-flag", "data")]
)
def update_programs_list(pathname, refresh_flag): 
    if pathname in ["/", "/main", None, "/programming"]: 
        current_programs_list = layout_manager.programs_data 
        if not current_programs_list:
             return dbc.Alert("No programs found or error loading programs.", color="warning", className="mt-3 text-center")
        return [layout_manager.create_program_card(program) for program in current_programs_list]
    return [] 

@callback(
    [Output("page-content-program", "children"), Output("page-state", "data")],
    [Input("url_program", "pathname")], [State("page-state", "data")],
    prevent_initial_call=False 
)
def display_page(pathname, page_state_data): 
    current_view = page_state_data.get("current_page", "main") if page_state_data else "main"
    if pathname in ["/", None, "/main", "/programming"]:
        if current_view == "editor":
            return dash.no_update, dash.no_update 
        return layout_manager.create_main_layout(), {"current_page": "main"}
    elif pathname == "/editor": 
        if current_view == "editor": 
            return dash.no_update, dash.no_update 
        else: 
            return layout_manager.create_main_layout(), {"current_page": "main"}
    return layout_manager.create_main_layout(), {"current_page": "main"}

@callback(
    [Output("page-content-program", "children", allow_duplicate=True), Output("page-state", "data", allow_duplicate=True), Output("program-commands-store", "data", allow_duplicate=True), Output("editing-program-name-store", "data", allow_duplicate=True)],
    [Input("create-program-btn", "n_clicks")],
    prevent_initial_call=True
)
def go_to_editor_for_new_program(n_clicks):
    if n_clicks:
        return (layout_manager.create_program_editor_layout(), {"current_page": "editor"}, [], None)
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update

@callback(
    [Output("url_program", "pathname", allow_duplicate=True), Output("page-state", "data", allow_duplicate=True), Output("editing-program-name-store", "data", allow_duplicate=True)],
    [Input("go-back-btn", "n_clicks")],
    prevent_initial_call=True
)
def go_back_to_main_and_clear_edit_state(n_clicks):
    if n_clicks: 
        return "/", {"current_page": "main"}, None 
    return dash.no_update, dash.no_update, dash.no_update

@callback(
    [Output("page-content-program", "children", allow_duplicate=True), Output("page-state", "data", allow_duplicate=True), Output("program-commands-store", "data", allow_duplicate=True), Output("editing-program-name-store", "data", allow_duplicate=True)],
    [Input({"type": "edit-program-btn", "program_name": ALL}, "n_clicks")],
    prevent_initial_call=True
)
def load_editor_for_existing_program(n_clicks_edit_buttons):
    if not ctx.triggered_id or not ctx.triggered[0]['value']: return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    program_name_to_edit = ctx.triggered_id["program_name"]
    current_programs_list = layout_manager.programs_data
    program_to_edit = next((p for p in current_programs_list if isinstance(p, dict) and p.get("name") == program_name_to_edit), None)
    if program_to_edit:
        commands_to_load = program_to_edit.get("commands", [])
        return (layout_manager.create_program_editor_layout(), {"current_page": "editor"}, commands_to_load, program_name_to_edit)
    else: 
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

# --- Recursive Helper Functions for Command Store ---
def find_command_recursive(commands_list, command_id): 
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

def update_command_recursive(commands_list, command_id_to_update, update_func): 
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

def delete_command_recursive(commands_list, command_id_to_delete): 
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

# callbacks.py
# ... (các phần khác của callbacks.py) ...

def add_command_to_target(commands_list, target_parent_id, target_block_spec, new_command): 
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
            
            # SỬA ĐỔI Ở ĐÂY: Logic cho math_value_a
            elif cmd_type == "math" and block_type == "math_value_a":
                # Đảm bảo 'config' và 'value_a_commands' tồn tại
                cmd.setdefault("config", {}).setdefault("value_a_commands", [])
                value_a_cmds_container = cmd["config"]["value_a_commands"]
                
                if not value_a_cmds_container: # Chỉ thêm nếu khối rỗng
                    value_a_cmds_container.append(new_command)
                    return True
                else: # Khối đã có lệnh, không thêm nữa
                    return False 
            return False # Nếu không phải là trường hợp xử lý được
        
        # Phần tìm kiếm đệ quy không thay đổi
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
        elif cmd_type == "math":
             # Đảm bảo 'config' và 'value_a_commands' tồn tại trước khi đệ quy
            math_config = cmd.get("config", {})
            if "value_a_commands" in math_config and add_command_to_target(math_config["value_a_commands"], target_parent_id, target_block_spec, new_command):
                target_found_in_child = True
        
        if target_found_in_child: return True
    return False

# ... (phần còn lại của callbacks.py) ...

# --- Generic Command Adder ---
def _add_command_to_store(n_clicks_all_tuple, current_commands_orig, command_type_being_added): 
    if not ctx.triggered_id or not any(n for n_list in n_clicks_all_tuple for n in n_list if n is not None): return dash.no_update
    item_id_dict = ctx.triggered_id; subtype_to_add = item_id_dict.get("subtype"); marker_id_to_add = item_id_dict.get("marker_id"); target_parent_id = item_id_dict.get("target_parent_id"); target_block_spec_json = item_id_dict.get("target_block_spec")
    if command_type_being_added == "move" and marker_id_to_add is None: return dash.no_update
    required_subtype_types = ["logic", "battery", "measure", "plc", "email", "programming", "math", "trajectory"]
    if command_type_being_added in required_subtype_types and subtype_to_add is None: return dash.no_update
    
    new_command_id = str(uuid.uuid4())
    new_command = {"id": new_command_id, "type": command_type_being_added, "config": {}}

    if command_type_being_added == "move": 
        new_command["marker_id"] = marker_id_to_add
    elif command_type_being_added == "battery":
        new_command["subtype"] = subtype_to_add
        if subtype_to_add == "charging":
            new_command["config"] = {"target_battery_level": 80} # Default target level to 80%
        # Other battery subtypes (docking, status) might not need a 'config' initially.
    elif command_type_being_added == "logic":
        new_command["subtype"] = subtype_to_add
        if subtype_to_add == "if": new_command["conditions"], new_command["then_commands"], new_command["else_if_blocks"], new_command["else_commands"] = [], [], [], None
        elif subtype_to_add == "loop": new_command["config"] = {"loop_type": "count", "iterations": 1}; new_command["body_commands"] = []
        elif subtype_to_add == "while": new_command["condition_commands"], new_command["body_commands"] = [], []
        elif subtype_to_add == "wait": new_command["config"] = {"duration_seconds": 1} 
        elif subtype_to_add in ["true", "false"]: new_command["config"] = {} # No specific config needed for True/False
    elif command_type_being_added == "math": 
        new_command["subtype"] = subtype_to_add
        new_command["config"] = {"value_a_commands": [], "value_b": 0} 
    elif command_type_being_added == "programming": 
        new_command["subtype"] = subtype_to_add
        if subtype_to_add == "call_program":
            program_name_to_call = item_id_dict.get("program_name_to_call")
            if program_name_to_call: new_command["config"] = {"called_program_name": program_name_to_call}
            else: new_command["config"] = {"called_program_name": "Error: Program Name Missing"} 
        elif subtype_to_add == "custom_code": new_command["config"] = {"code": ""} 
        else: new_command["config"] = {} 
    elif command_type_being_added == "trajectory":
        new_command["subtype"] = subtype_to_add
        if subtype_to_add == "line":
            new_command["config"] = {"destination_marker_id": None}
        # Other trajectory subtypes might have their own config defaults.
    else: # General case for other command types that just need a subtype.
        # Check if subtype needs to be set (e.g., if not set by a more specific block above)
        if "subtype" not in new_command:
            new_command["subtype"] = subtype_to_add
    
    current_commands = copy.deepcopy(current_commands_orig or [])
    if target_parent_id and target_block_spec_json:
        try:
            target_block_spec = json.loads(target_block_spec_json)
            if not add_command_to_target(current_commands, target_parent_id, target_block_spec, new_command): return dash.no_update
        except json.JSONDecodeError: return dash.no_update
    else: current_commands.append(new_command)
    return current_commands

# --- Specific Command Adder Callbacks ---
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
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-trajectory-command-action", "subtype": ALL, "target_parent_id": ALL, "target_block_spec": ALL}, "n_clicks"), Input({"type": "add-trajectory-command-action", "subtype": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_trajectory_command(n_nested, n_root, s): return _add_command_to_store((n_nested, n_root), s, "trajectory")

@callback(Output("program-commands-container", "children"), [Input("program-commands-store", "data")])
def render_program_commands_from_store(commands_data):
    if not commands_data: return dbc.Alert("No program commands added yet.", color="info", className="mt-3 text-center")
    return [layout_manager.render_single_command(cmd_data) for cmd_data in commands_data if cmd_data]

@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "change-position-marker", "command_id": ALL, "marker_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def change_command_position(n_clicks_all, current_commands_orig): 
    if not ctx.triggered_id or not any(n for n in n_clicks_all if n is not None) or not current_commands_orig: return dash.no_update
    item_id_dict, new_marker_id = ctx.triggered_id, ctx.triggered_id["marker_id"]; command_id_to_change = item_id_dict["command_id"]; current_commands = copy.deepcopy(current_commands_orig)
    def update_marker_in_cmd(cmd_to_update):
        if cmd_to_update.get("type") == "move": cmd_to_update["marker_id"] = new_marker_id
        return cmd_to_update
    if update_command_recursive(current_commands, command_id_to_change, update_marker_in_cmd): return current_commands
    return dash.no_update

@callback(
    Output("program-commands-store", "data", allow_duplicate=True),
    [Input({"type": "change-trajectory-line-destination", "command_id": ALL, "marker_id": ALL}, "n_clicks")],
    [State("program-commands-store", "data")],
    prevent_initial_call=True
)
def change_trajectory_line_destination(n_clicks_all, current_commands_orig):
    if not ctx.triggered_id or not any(n for n in n_clicks_all if n is not None) or not current_commands_orig:
        return dash.no_update
    command_id_to_change = ctx.triggered_id["command_id"]
    new_destination_marker_id = ctx.triggered_id["marker_id"]
    current_commands = copy.deepcopy(current_commands_orig)
    def update_destination_in_line_cmd(cmd_to_update):
        if cmd_to_update.get("type") == "trajectory" and cmd_to_update.get("subtype") == "line":
            cmd_to_update.setdefault("config", {})["destination_marker_id"] = new_destination_marker_id
        return cmd_to_update
    if update_command_recursive(current_commands, command_id_to_change, update_destination_in_line_cmd):
        return current_commands
    return dash.no_update


@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "delete-command-btn", "command_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def delete_program_command(n_clicks_all, current_commands_orig): 
    if not ctx.triggered_id or not any(n for n in n_clicks_all if n is not None) or not current_commands_orig: return dash.no_update
    command_id_to_delete = ctx.triggered_id["command_id"]; current_commands = copy.deepcopy(current_commands_orig)
    if delete_command_recursive(current_commands, command_id_to_delete): return current_commands
    return dash.no_update

# --- Callbacks for IF Block Management ---
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-else-if-block", "if_command_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_else_if_block(n,s): 
    if not ctx.triggered_id or not any(_n for _n in n if _n): return dash.no_update
    s_copy=copy.deepcopy(s); id=ctx.triggered_id["if_command_id"]
    def fn(cmd): cmd.setdefault("else_if_blocks",[]).append({"id":str(uuid.uuid4()),"conditions":[],"then_commands":[]}); return cmd
    if update_command_recursive(s_copy,id,fn): return s_copy
    return dash.no_update
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "add-else-block", "if_command_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def add_else_block(n,s): 
    if not ctx.triggered_id or not any(_n for _n in n if _n): return dash.no_update
    s_copy=copy.deepcopy(s); id=ctx.triggered_id["if_command_id"]
    def fn(cmd):
        if cmd.get("else_commands") is None: cmd["else_commands"]=[]
        return cmd
    if update_command_recursive(s_copy,id,fn): return s_copy
    return dash.no_update
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "delete-else-if-block", "if_command_id": ALL, "else_if_block_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def delete_else_if_block(n,s): 
    if not ctx.triggered_id or not any(_n for _n in n if _n): return dash.no_update
    s_copy=copy.deepcopy(s); if_id=ctx.triggered_id["if_command_id"]; else_if_id=ctx.triggered_id["else_if_block_id"]
    def fn(cmd):
        if "else_if_blocks" in cmd: cmd["else_if_blocks"]=[b for b in cmd["else_if_blocks"] if b["id"]!=else_if_id]
        return cmd
    if update_command_recursive(s_copy,if_id,fn): return s_copy
    return dash.no_update
@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "delete-else-block", "if_command_id": ALL}, "n_clicks")], [State("program-commands-store", "data")], prevent_initial_call=True)
def delete_else_block(n,s): 
    if not ctx.triggered_id or not any(_n for _n in n if _n): return dash.no_update
    s_copy=copy.deepcopy(s); id=ctx.triggered_id["if_command_id"]
    def fn(cmd):
        if "else_commands" in cmd: cmd["else_commands"]=None
        return cmd
    if update_command_recursive(s_copy,id,fn): return s_copy
    return dash.no_update

@callback(Output("program-commands-store", "data", allow_duplicate=True), [Input({"type": "loop-config-type", "command_id": ALL}, "value"), Input({"type": "loop-config-iterations", "command_id": ALL}, "value")], [State("program-commands-store", "data")], prevent_initial_call=True)
def update_loop_configuration(loop_types, iter_values, s_orig): 
    if not ctx.triggered_id or not s_orig: return dash.no_update
    s=copy.deepcopy(s_orig); prop=ctx.triggered_id["type"]; cmd_id=ctx.triggered_id["command_id"]; val=ctx.triggered[0]['value']
    if val is None : return dash.no_update 
    def fn(cmd):
        if cmd.get("type")=="logic" and cmd.get("subtype")=="loop":
            cmd.setdefault("config",{})
            if prop=="loop-config-type": cmd["config"]["loop_type"]=val; (cmd["config"].pop("iterations", None) if val=="forever" else cmd["config"].setdefault("iterations",1)) 
            elif prop=="loop-config-iterations":
                try: cmd["config"]["iterations"]=int(val) if val is not None and str(val).strip()!="" else 1
                except ValueError: cmd["config"]["iterations"]=1 
        return cmd
    if update_command_recursive(s,cmd_id,fn): return s
    return dash.no_update

@callback(Output("program-commands-store", "data", allow_duplicate=True), Input({"type": "math-config-value-b", "command_id": ALL}, "value"), State("program-commands-store", "data"), prevent_initial_call=True)
def update_math_command_value_b(value_b_inputs, current_commands_orig): 
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
    Output("program-commands-store", "data", allow_duplicate=True),
    [Input({"type": "wait-duration-hours", "command_id": ALL}, "value"),
     Input({"type": "wait-duration-minutes", "command_id": ALL}, "value"),
     Input({"type": "wait-duration-seconds", "command_id": ALL}, "value")],
    [State("program-commands-store", "data")],
    prevent_initial_call=True
)
def update_wait_command_duration(all_hours_inputs, all_minutes_inputs, all_seconds_inputs, current_commands_orig):
    if not ctx.triggered_id or not current_commands_orig:
        return dash.no_update
    triggered_prop_id_str = ctx.triggered[0]['prop_id']
    try:
        # Ensure robust parsing of the dictionary part of the prop_id string
        id_dict_str_match = triggered_prop_id_str.split.get(("prop_id", "."))[0]
        if not id_dict_str_match.endswith('}'): # Simple check, might need more robustness
             id_dict_str = id_dict_str_match + '}'
        else:
            id_dict_str = id_dict_str_match

        triggered_id_details = json.loads(id_dict_str)
    except (json.JSONDecodeError, IndexError, AttributeError) as e: # Added AttributeError
        print(f"Error parsing triggered_id for wait duration: {e}, prop_id: {triggered_prop_id_str}")
        return dash.no_update

    command_id_to_update = triggered_id_details.get("command_id")
    changed_input_type = triggered_id_details.get("type") 
    new_value_from_input_str = ctx.triggered[0]['value']

    if command_id_to_update is None or changed_input_type is None:
        return dash.no_update
    current_commands = copy.deepcopy(current_commands_orig)
    def update_duration_in_wait_cmd(wait_cmd):
        if wait_cmd.get("type") == "logic" and wait_cmd.get("subtype") == "wait":
            wait_cmd.setdefault("config", {"duration_seconds": 0})
            current_h, current_m, current_s = layout_manager._seconds_to_hms(wait_cmd["config"].get("duration_seconds", 0))
            try:
                new_val_int = int(new_value_from_input_str) if new_value_from_input_str is not None and str(new_value_from_input_str).strip() != "" else 0
                new_val_int = max(0, new_val_int) 
            except (ValueError, TypeError):
                new_val_int = 0 
            if changed_input_type == "wait-duration-hours": current_h = new_val_int
            elif changed_input_type == "wait-duration-minutes": current_m = min(new_val_int, 59) 
            elif changed_input_type == "wait-duration-seconds": current_s = min(new_val_int, 59) 
            wait_cmd["config"]["duration_seconds"] = layout_manager._hms_to_seconds(current_h, current_m, current_s)
        return wait_cmd
    if update_command_recursive(current_commands, command_id_to_update, update_duration_in_wait_cmd):
        return current_commands
    return dash.no_update

@callback(
    Output("program-commands-store", "data", allow_duplicate=True),
    Input({"type": "battery-charge-target-level", "command_id": ALL}, "value"),
    State("program-commands-store", "data"),
    prevent_initial_call=True
)
def update_battery_charge_target_level(target_level_inputs, current_commands_orig):
    if not ctx.triggered_id or not current_commands_orig:
        return dash.no_update

    command_id_to_update = ctx.triggered_id["command_id"]
    new_target_level_str = ctx.triggered[0]['value']
    current_commands = copy.deepcopy(current_commands_orig)

    def update_target_level_in_cmd(battery_cmd):
        if battery_cmd.get("type") == "battery" and battery_cmd.get("subtype") == "charging":
            battery_cmd.setdefault("config", {}) # Ensure config dict exists
            try:
                # Default to 80 if input is empty or invalid
                new_target_level = int(new_target_level_str) if new_target_level_str is not None and str(new_target_level_str).strip() != "" else 80
                # Clamp value between 0 and 100
                new_target_level = max(0, min(100, new_target_level))
                battery_cmd["config"]["target_battery_level"] = new_target_level
            except (ValueError, TypeError):
                # Fallback to a sensible default if conversion fails
                battery_cmd["config"]["target_battery_level"] = 80 
        return battery_cmd

    if update_command_recursive(current_commands, command_id_to_update, update_target_level_in_cmd):
        return current_commands
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
    file_path = layout_manager.programs_file_path
    db_path = os.path.dirname(file_path) 
    try:
        os.makedirs(db_path, exist_ok=True); all_progs = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
                if content.strip(): all_progs = json.loads(content)
                if not isinstance(all_progs, list): all_progs = []
            except (json.JSONDecodeError, Exception): all_progs = []
        if (original_program_name and original_program_name != program_name and any(p.get("name") == program_name for p in all_progs if isinstance(p, dict))) or \
           (not original_program_name and any(p.get("name") == program_name for p in all_progs if isinstance(p, dict))):
            return {"message": f"Program name '{program_name}' already exists.", "color": "warning", "icon": "exclamation-circle"}, dash.no_update
        new_data = {"name": program_name, "commands": commands_data if commands_data else []}; found = False
        if original_program_name:
            for i,p in enumerate(all_progs):
                if isinstance(p,dict) and p.get("name")==original_program_name: all_progs[i]=new_data; found=True; break
            if not found: all_progs.append(new_data) 
        else: all_progs.append(new_data)
        with open(file_path, 'w', encoding='utf-8') as f: json.dump(all_progs, f, indent=4)
        layout_manager.reload_programs_data(file_path) 
        return {"message": f"Program '{program_name}' saved successfully!", "color": "success", "icon": "check-circle"}, program_name
    except Exception as e: return {"message": f"Error saving program: {str(e)}", "color": "danger", "icon": "times-circle"}, dash.no_update

# --- Callbacks for Program Deletion ---
@callback(
    [Output("delete-program-confirm-modal", "is_open"), Output("program-to-delete-store", "data"), Output("delete-modal-body-content", "children")],
    Input({"type": "delete-program-main-btn", "program_name": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def open_delete_confirmation_modal(n_clicks_delete_buttons): 
    if not ctx.triggered_id or not ctx.triggered[0]['value']: return False, None, ""
    program_name_to_delete = ctx.triggered_id["program_name"]
    modal_body = f"Are you sure you want to delete the program: '{program_name_to_delete}'? This action cannot be undone."
    return True, program_name_to_delete, modal_body

@callback(
    [Output("delete-program-confirm-modal", "is_open", allow_duplicate=True), Output("program-to-delete-store", "data", allow_duplicate=True)],
    Input("cancel-delete-modal-btn", "n_clicks"),
    prevent_initial_call=True
)
def close_delete_confirmation_modal(n_clicks_cancel): 
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
            layout_manager.reload_programs_data(file_path)
            toast_data = {"message": f"Program '{program_name_to_delete}' deleted successfully!", "color": "success", "icon": "check-circle"}
        else: toast_data = {"message": f"Program '{program_name_to_delete}' not found for deletion.", "color": "warning", "icon": "exclamation-circle"}
        new_refresh_flag = (current_refresh_flag or 0) + 1
        return False, None, toast_data, new_refresh_flag
    except Exception as e:
        toast_data = {"message": f"Error deleting program: {str(e)}", "color": "danger", "icon": "times-circle"}
        return False, program_name_to_delete, toast_data, dash.no_update

# --- Callbacks for Play Program (Queueing) ---
@callback(
    [Output("play-program-action-modal", "is_open"), Output("program-to-play-store", "data"), Output("play-modal-body-content", "children")],
    Input({"type": "run-program-main-btn", "program_name": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def open_play_action_modal(n_clicks_run_buttons):
    if not ctx.triggered_id or not ctx.triggered[0]['value']: return False, None, ""
    program_name_to_play = ctx.triggered_id["program_name"]
    modal_body = f"Choose an action for program: '{program_name_to_play}'."
    return True, program_name_to_play, modal_body

@callback(
    [Output("play-program-action-modal", "is_open", allow_duplicate=True), Output("program-to-play-store", "data", allow_duplicate=True)],
    Input("cancel-play-modal-btn", "n_clicks"),
    prevent_initial_call=True
)
def close_play_action_modal(n_clicks_cancel):
    if n_clicks_cancel: return False, None
    return dash.no_update, dash.no_update

@callback(
    [Output("play-program-action-modal", "is_open", allow_duplicate=True), Output("program-to-play-store", "data", allow_duplicate=True), Output("save-status-store", "data", allow_duplicate=True), Output("queue-refresh-flag", "data")],
    [Input("append-to-queue-btn", "n_clicks"), Input("clear-and-append-to-queue-btn", "n_clicks")],
    [State("program-to-play-store", "data"), State("queue-refresh-flag", "data")],
    prevent_initial_call=True
)
def handle_queue_program_action(n_append, n_clear_append, program_name_to_play, current_queue_refresh_flag):
    if not (n_append or n_clear_append) or not program_name_to_play: return False, None, dash.no_update, current_queue_refresh_flag 
    action = None
    if ctx.triggered_id == "append-to-queue-btn": action = "append"
    elif ctx.triggered_id == "clear-and-append-to-queue-btn": action = "clear_append"
    if not action: return False, program_name_to_play, {"message": "Invalid action.", "color": "danger", "icon": "times-circle"}, current_queue_refresh_flag
    queue_file_path = layout_manager.queue_file_path
    db_path = os.path.dirname(queue_file_path) 
    toast_data = {}
    try:
        all_programs = layout_manager.programs_data 
        program_data_to_queue = next((p for p in all_programs if isinstance(p, dict) and p.get("name") == program_name_to_play), None)
        if not program_data_to_queue:
            toast_data = {"message": f"Program '{program_name_to_play}' not found in library.", "color": "danger", "icon": "times-circle"}
            return False, None, toast_data, current_queue_refresh_flag
        current_queue = []
        if os.path.exists(queue_file_path):
            try:
                with open(queue_file_path, 'r', encoding='utf-8') as f: content = f.read()
                if content.strip(): current_queue = json.loads(content)
                if not isinstance(current_queue, list): current_queue = [] 
            except (json.JSONDecodeError, Exception) as e:
                print(f"Error reading queue file '{queue_file_path}', initializing empty queue: {e}")
                current_queue = []
        if action == "clear_append": current_queue = []
        current_queue.append(program_data_to_queue)
        os.makedirs(db_path, exist_ok=True) 
        with open(queue_file_path, 'w', encoding='utf-8') as f: json.dump(current_queue, f, indent=4)
        action_text = "appended to" if action == "append" else "cleared and program added to"
        toast_data = {"message": f"Program '{program_name_to_play}' {action_text} queue.", "color": "success", "icon": "check-circle"}
        new_refresh_flag = (current_queue_refresh_flag or 0) + 1
        return False, None, toast_data, new_refresh_flag
    except Exception as e:
        toast_data = {"message": f"Error queueing program: {str(e)}", "color": "danger", "icon": "times-circle"}
        return False, program_name_to_play, toast_data, current_queue_refresh_flag

# --- Callback to display program queue ---
@callback(
    Output("program-queue-list", "children"),
    [Input("url_program", "pathname"), Input("queue-refresh-flag", "data")]
)
def update_program_queue_display(pathname, refresh_flag):
    if pathname in ["/", "/main", None, "/programming"]: 
        queued_programs = layout_manager.load_queued_programs_from_file()
        if not queued_programs: return html.P("The queue is empty.", className="text-muted fst-italic text-center mt-2")
        queue_items_display = [layout_manager.create_queued_program_mini_card(prog, idx) for idx, prog in enumerate(queued_programs)]
        return dbc.ListGroup(queue_items_display, flush=True, style={"maxHeight": "400px", "overflowY": "auto", "borderTop": "1px solid #eee", "paddingTop": "10px"})
    return dash.no_update

# --- Callbacks for Deleting from Queue ---
@callback(
    [Output("delete-queue-item-confirm-modal", "is_open"), Output("item-index-to-delete-from-queue-store", "data"), Output("delete-queue-item-modal-body-content", "children")],
    Input({"type": "delete-queued-program-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def open_delete_queue_item_modal(n_clicks_delete_buttons):
    if not ctx.triggered_id or not ctx.triggered[0]['value']: return False, None, ""
    item_index_to_delete = ctx.triggered_id["index"]
    program_name_for_modal = f"program at index {item_index_to_delete + 1}" 
    try:
        queued_programs = layout_manager.load_queued_programs_from_file()
        if queued_programs and 0 <= item_index_to_delete < len(queued_programs):
            program_to_delete_data = queued_programs[item_index_to_delete]
            program_name_for_modal = program_to_delete_data.get("name", f"Unnamed Program at index {item_index_to_delete + 1}")
    except Exception as e: print(f"Error getting program name for queue deletion modal: {e}")
    modal_body = f"Are you sure you want to delete '{program_name_for_modal}' (item {item_index_to_delete + 1}) from the queue?"
    return True, item_index_to_delete, modal_body

@callback(
    [Output("delete-queue-item-confirm-modal", "is_open", allow_duplicate=True), Output("item-index-to-delete-from-queue-store", "data", allow_duplicate=True)],
    Input("cancel-delete-queue-item-modal-btn", "n_clicks"),
    prevent_initial_call=True
)
def close_delete_queue_item_modal(n_clicks_cancel):
    if n_clicks_cancel: return False, None
    return dash.no_update, dash.no_update

@callback(
    [Output("delete-queue-item-confirm-modal", "is_open", allow_duplicate=True), Output("item-index-to-delete-from-queue-store", "data", allow_duplicate=True), Output("save-status-store", "data", allow_duplicate=True), Output("queue-refresh-flag", "data", allow_duplicate=True)],
    Input("confirm-delete-queue-item-modal-btn", "n_clicks"),
    [State("item-index-to-delete-from-queue-store", "data"), State("queue-refresh-flag", "data")],
    prevent_initial_call=True
)
def handle_confirm_delete_queue_item(n_clicks_confirm, item_index_to_delete, current_queue_refresh_flag):
    if not n_clicks_confirm or item_index_to_delete is None: return False, None, dash.no_update, dash.no_update
    queue_file_path = layout_manager.queue_file_path
    toast_data = {}
    try:
        current_queue = []
        if os.path.exists(queue_file_path):
            try:
                with open(queue_file_path, 'r', encoding='utf-8') as f: content = f.read()
                if content.strip(): current_queue = json.loads(content)
                if not isinstance(current_queue, list): current_queue = []
            except (json.JSONDecodeError, Exception) as e:
                print(f"Error reading queue file '{queue_file_path}' for deletion, re-initializing: {e}")
                current_queue = []
        if 0 <= item_index_to_delete < len(current_queue):
            deleted_program = current_queue.pop(item_index_to_delete)
            deleted_program_name = deleted_program.get("name", "Unnamed Program")
            with open(queue_file_path, 'w', encoding='utf-8') as f: json.dump(current_queue, f, indent=4)
            toast_data = {"message": f"Program '{deleted_program_name}' removed from queue.", "color": "success", "icon": "check-circle"}
            new_refresh_flag = (current_queue_refresh_flag or 0) + 1
            return False, None, toast_data, new_refresh_flag
        else:
            toast_data = {"message": "Error: Item index out of bounds for deletion.", "color": "warning", "icon": "exclamation-circle"}
            return False, None, toast_data, dash.no_update
    except Exception as e:
        toast_data = {"message": f"Error deleting item from queue: {str(e)}", "color": "danger", "icon": "times-circle"}
        return False, None, toast_data, dash.no_update

# --- Toast Display Callback ---
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