from dash import Output, Input, State, ctx ,ALL, no_update
from dash import html
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify
import requests
from .layout import mission_queue_layout
from .layout import create_mission_row
import json
import os
ip = '192.168.0.173'
host = 'http://' + ip + '/api/v2.0.0/'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='
}
mission_list_json_file = "static/mission_groups.json"  # Tên file JSON lưu dữ liệu nhóm mission
mission_queue_json_file = "static/mission_queue.json"  # Tên file JSON lưu dữ liệu hàng đợi mission

# Lưu danh sách actions tạm thời
TEMP_ACTIONS = []

def create_new_mission(name, desc, group_id):
    """Gửi API tạo một nhiệm vụ mới"""
    url = f"{host}/missions"
    payload = {
        "name": name,
        "description": desc,
        "group_id": group_id
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 201:
        return "Mission created successfully!", response.json()
    return f"Failed to create mission. Status: {response.status_code}", None

def add_action_to_mission(mission_id, action_type, parameters):
    """Gửi API thêm action vào mission"""
    url = f"{host}/missions/{mission_id}/actions"
    payload = {
        "action_type": action_type,
        "parameters": parameters
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 201:
        return "Action added successfully!", response.json()
    return f"Failed to add action. Status: {response.status_code}", None
def add_mission_to_queue(mission_id):
    """Thêm nhiệm vụ vào hàng đợi"""
    url = f"{host}/mission_queue"
    payload = {"mission_id": mission_id}
    
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        return "Mission added successfully!"
    else:
        return 

def get_mission_groups():
    """Lấy danh sách mission groups từ API và lưu vào JSON"""
    response = requests.get(f"{host}/mission_groups", headers=headers)
    
    if response.status_code == 200:
        groups = response.json()
        group_dict = {group["name"]: group["guid"] for group in groups}

        # Lưu vào file JSON
        with open(mission_list_json_file, "w") as f:
            json.dump(group_dict, f)

        return group_dict
    else:
        print("Error fetching mission groups:", response.status_code)
        return {}
def get_mission_queue_status():
    """Lấy danh sách các nhiệm vụ trong hàng đợi nhưng chưa thực hiện và lưu vào JSON"""
    #response = requests.get(f"{host}/mission_queue", headers=headers)
    response = requests.get(f"{host}/mission_queue", headers=headers)
    if response.status_code == 200:
        all_missions = response.json()
        pending_missions = [mission for mission in all_missions if mission.get("state") == "Pending" or mission.get("state") == "Executing"]
        with open(mission_queue_json_file, "w") as f:
            json.dump(pending_missions, f)
        return pending_missions
    return []

def load_mission_queue():
    """Đọc danh sách nhiệm vụ trong hàng đợi từ JSON"""
    if os.path.exists(mission_queue_json_file):
        with open(mission_queue_json_file, "r") as f:
            return json.load(f)
    return get_mission_queue_status()

def load_mission_groups():
    """Đọc danh sách mission groups từ JSON"""
    if os.path.exists(mission_list_json_file):
        with open(mission_list_json_file, "r") as f:
            return json.load(f)
    else:
        return get_mission_groups()  # Nếu chưa có file, gọi API để lấy dữ liệu
def get_mission_list(selected_group):
    """Lấy danh sách mission từ API dựa trên nhóm được chọn"""
    groups = load_mission_groups()  # Đọc dữ liệu từ JSON
    group_id = groups.get(selected_group)  # Tìm ID nhóm từ JSON
    
    if not group_id:
        # print(f"Group '{selected_group}' not found. Using default.")
        group_id = "mirconst-guid-0000-0011-missiongroup"

    response = requests.get(f"{host}/mission_groups/{group_id}/missions", headers=headers)
    
    if response.status_code == 200:
        return response.json()  # Trả về danh sách mission của nhóm
    else:
        return []

def register_callbacks(app):
    
    @app.callback(
    Output("api-addmissions-response-message", "children"),
    Input({"type": "addmission-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
    def handle_add_mission(n_clicks):
        """Thêm nhiệm vụ khi nhấn nút Add"""
        
        if not n_clicks or all(v is None for v in n_clicks):
            return 

        # Xác định button nào được bấm
        triggered_id = ctx.triggered_id

        if not triggered_id:
            return 

        mission_id = triggered_id["index"]  # Lấy mission_id từ nút Add
        response_message = add_mission_to_queue(mission_id)

        return response_message  # Hiển thị trạng thái API

    @app.callback(
        Output("mission-config-modal", "is_open"),
        [Input("create-mission-btn", "n_clicks"), Input("close-config-btn", "n_clicks")],
        [State("mission-config-modal", "is_open")],
    )
    def toggle_modal(open_clicks, close_clicks, is_open):
        """Callback mở / đóng modal cấu hình Mission"""
        if open_clicks or close_clicks:
            return not is_open
        return is_open
    @app.callback(
        Output("configured-actions-container", "children"),
        Output("api-addaction-response-message", "children"),
        Input("add-action-btn", "n_clicks"),
        State("action-type-dropdown", "value"),
        State("action-params-input", "value"),
        prevent_initial_call=True
    )
    def add_action(n_clicks, action_type, params):
        """Thêm Action vào danh sách tạm thời"""
        if not action_type:
            return TEMP_ACTIONS, "❌ Action type is required!"

        try:
            parameters = json.loads(params) if params else {}
        except json.JSONDecodeError:
            return TEMP_ACTIONS, "❌ Invalid JSON format!"

        new_action = {"action_type": action_type, "parameters": parameters}
        TEMP_ACTIONS.append(new_action)

        # Hiển thị danh sách action đã thêm
        action_display = [html.Div(f"{a['action_type']}: {a['parameters']}", className="alert alert-info") for a in TEMP_ACTIONS]
        return action_display, "✅ Action added!"

    @app.callback(
        Output("api-finishmission-response-message", "children"),
        Input("finish-mission-btn", "n_clicks"),
        State("mission-name-input", "value"),
        State("mission-desc-input", "value"),
        State("mission-group-dropdown", "value"),
        prevent_initial_call=True
    )
    def finish_and_send(n_clicks, name, desc, group_id):
        """Gửi tất cả API khi nhấn Finish"""
        if not name or not group_id:
            return "❌ Mission name and group are required!"

        # Gửi API tạo mission
        message, mission_data = create_new_mission(name, desc, group_id)
        if not mission_data:
            return message

        mission_id = mission_data.get("guid")

        # Gửi tất cả action lên API
        for action in TEMP_ACTIONS:
            add_action_to_mission(mission_id, action["action_type"], action["parameters"])

        # Xóa danh sách tạm
        TEMP_ACTIONS.clear()

        return "✅ Mission & Actions added successfully!"
    @app.callback(
        Output("mission-dropdown", "options"),
        Input("mission-interval", "n_intervals"),
    )
    def update_mission_groups(n_intervals):
        """Cập nhật danh sách mission groups mỗi 5 giây"""
        groups = load_mission_groups()
        return [{"label": name, "value": name} for name in groups]
    @app.callback(
        Output("mission-list-container", "children"),
        Input("mission-interval", "n_intervals"),
        Input("mission-dropdown", "value"),
    )
    def update_mission_table(n_intervals,selected_group):
        missions = get_mission_list(selected_group)
        return [create_mission_row(mission) for mission in missions]
    @app.callback(
        Output("mission-queue-container", "children"),
        Input("interval-component", "n_intervals"),
    )
    def update_mission_queue(n_intervals):
        missions_in_queue = get_mission_queue_status()
        return [create_mission_row(mission) for mission in missions_in_queue]

    @app.callback(
    Output("mission-modal", "is_open"),
    [Input("create-btn", "n_clicks"), Input("close-modal-btn", "n_clicks")],
    [State("mission-modal", "is_open")],
    )
    def toggle_modal(start_clicks, close_clicks, is_open):
        if start_clicks or close_clicks:
            return not is_open
        return is_open
  
    @app.callback(
        Output("mission-queue-create", "rowData"),
        Output("store-missions", "data"),
        Input("mission-queue-table", "cellClicked"),
        State("store-missions", "data"),
        prevent_initial_call=True
    )
    def delete_mission(cell_click, missions):
        if cell_click and cell_click["colDef"]["field"] == "Action":
            mission_id = cell_click["data"]["ID"]
            missions = [m for m in missions if m["ID"] != mission_id]  # Xóa hàng có ID tương ứng
            return missions, missions
        return missions, missions
   
