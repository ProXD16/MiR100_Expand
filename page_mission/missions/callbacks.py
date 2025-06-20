from dash import Output, Input, State, ctx, ALL, no_update
from dash import html
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify
import requests
import json
import os
import sys
import random
from datetime import datetime
from .layout import mission_queue_layout, create_mission_row
from get_ip_address import load_ip_from_json

# Cấu hình
ip = load_ip_from_json("database_json/ip_address.json")
host = f'http://{ip}/api/v2.0.0/'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='
}
mission_list_json_file = "static/mission_groups.json"
mission_queue_json_file = "static/mission_queue.json"
TEMP_ACTIONS = []

# Kiểm tra chế độ mô phỏng
is_simulation = 'simulation' in sys.argv

def generate_simulation_mission_groups():
    """Tạo dữ liệu giả lập cho mission groups"""
    return {
        "Group1": f"mirconst-guid-{random.randint(1000, 9999)}-missiongroup",
        "Group2": f"mirconst-guid-{random.randint(1000, 9999)}-missiongroup",
        "Group3": f"mirconst-guid-{random.randint(1000, 9999)}-missiongroup"
    }

def generate_simulation_missions(group_id):
    """Tạo dữ liệu giả lập cho danh sách missions"""
    return [
        {
            "guid": f"mission-{random.randint(1000, 9999)}",
            "name": f"Mission {i}",
            "description": f"Description for Mission {i}",
            "group_id": group_id
        } for i in range(1, 4)
    ]

def generate_simulation_mission_queue():
    """Tạo dữ liệu giả lập cho mission queue"""
    states = ["Pending", "Executing"]
    return [
        {
            "id": f"queue-{random.randint(1000, 9999)}",
            "mission_id": f"mission-{random.randint(1000, 9999)}",
            "state": random.choice(states),
            "created_at": datetime.now().isoformat()
        } for _ in range(3)
    ]

def create_new_mission(name, desc, group_id):
    """Gửi API tạo mission hoặc giả lập trong mô phỏng"""
    if is_simulation:
        print("🏭 Mô phỏng: Tạo mission giả lập")
        return "Mission created successfully!", {"guid": f"mission-{random.randint(1000, 9999)}"}
    
    url = f"{host}/missions"
    payload = {
        "name": name,
        "description": desc,
        "group_id": group_id
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 201:
            return "Mission created successfully!", response.json()
        return f"Failed to create mission. Status: {response.status_code}", None
    except (requests.ConnectionError, requests.RequestException) as e:
        print(f"🚫 Không kết nối được tới {host}: {e}")
        return "🏭 Mô phỏng: Tạo mission giả lập", {"guid": f"mission-{random.randint(1000, 9999)}"}

def add_action_to_mission(mission_id, action_type, parameters):
    """Gửi API thêm action hoặc giả lập trong mô phỏng"""
    if is_simulation:
        print("🏭 Mô phỏng: Thêm action giả lập")
        return "Action added successfully!", {"action_id": f"action-{random.randint(1000, 9999)}"}
    
    url = f"{host}/missions/{mission_id}/actions"
    payload = {
        "action_type": action_type,
        "parameters": parameters
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 201:
            return "Action added successfully!", response.json()
        return f"Failed to add action. Status: {response.status_code}", None
    except (requests.ConnectionError, requests.RequestException) as e:
        print(f"🚫 Không kết nối được tới {host}: {e}")
        return "🏭 Mô phỏng: Thêm action giả lập", {"action_id": f"action-{random.randint(1000, 9999)}"}

def add_mission_to_queue(mission_id):
    """Thêm nhiệm vụ vào hàng đợi hoặc giả lập trong mô phỏng"""
    if is_simulation:
        print("🏭 Mô phỏng: Thêm mission vào queue giả lập")
        return "Mission added successfully!"
    
    url = f"{host}/mission_queue"
    payload = {"mission_id": mission_id}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 201:
            return "Mission added successfully!"
        return f"Failed to add mission to queue. Status: {response.status_code}"
    except (requests.ConnectionError, requests.RequestException) as e:
        print(f"🚫 Không kết nối được tới {host}: {e}")
        return "🏭 Mô phỏng: Thêm mission vào queue giả lập"

def get_mission_groups():
    """Lấy danh sách mission groups từ API hoặc giả lập"""
    if is_simulation:
        print("🏭 Mô phỏng: Lấy mission groups giả lập")
        groups = generate_simulation_mission_groups()
        with open(mission_list_json_file, "w") as f:
            json.dump(groups, f)
        return groups
    
    try:
        response = requests.get(f"{host}/mission_groups", headers=headers, timeout=5)
        if response.status_code == 200:
            groups = response.json()
            group_dict = {group["name"]: group["guid"] for group in groups}
            with open(mission_list_json_file, "w") as f:
                json.dump(group_dict, f)
            return group_dict
        print(f"Error fetching mission groups: {response.status_code}")
        return generate_simulation_mission_groups()  # Dùng dữ liệu giả lập nếu API lỗi
    except (requests.ConnectionError, requests.RequestException) as e:
        print(f"🚫 Không kết nối được tới {host}: {e}")
        return generate_simulation_mission_groups()

def get_mission_queue_status():
    """Lấy danh sách mission queue từ API hoặc giả lập"""
    if is_simulation:
        print("🏭 Mô phỏng: Lấy mission queue giả lập")
        missions = generate_simulation_mission_queue()
        with open(mission_queue_json_file, "w") as f:
            json.dump(missions, f)
        return missions
    
    try:
        response = requests.get(f"{host}/mission_queue", headers=headers, timeout=5)
        if response.status_code == 200:
            all_missions = response.json()
            pending_missions = [mission for mission in all_missions if mission.get("state") in ["Pending", "Executing"]]
            with open(mission_queue_json_file, "w") as f:
                json.dump(pending_missions, f)
            return pending_missions
        print(f"Error fetching mission queue: {response.status_code}")
        return generate_simulation_mission_queue()
    except (requests.ConnectionError, requests.RequestException) as e:
        print(f"🚫 Không kết nối được tới {host}: {e}")
        return generate_simulation_mission_queue()

def load_mission_queue():
    """Đọc danh sách mission queue từ JSON hoặc giả lập"""
    if os.path.exists(mission_queue_json_file):
        with open(mission_queue_json_file, "r") as f:
            return json.load(f)
    return get_mission_queue_status()

def load_mission_groups():
    """Đọc danh sách mission groups từ JSON hoặc giả lập"""
    if os.path.exists(mission_list_json_file):
        with open(mission_list_json_file, "r") as f:
            return json.load(f)
    return get_mission_groups()

def get_mission_list(selected_group):
    """Lấy danh sách mission từ API hoặc giả lập dựa trên nhóm được chọn"""
    groups = load_mission_groups()
    group_id = groups.get(selected_group, "mirconst-guid-0000-0011-missiongroup")
    
    if is_simulation:
        print("🏭 Mô phỏng: Lấy mission list giả lập")
        return generate_simulation_missions(group_id)
    
    try:
        response = requests.get(f"{host}/mission_groups/{group_id}/missions", headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        print(f"Error fetching missions for group {selected_group}: {response.status_code}")
        return generate_simulation_missions(group_id)
    except (requests.ConnectionError, requests.RequestException) as e:
        print(f"🚫 Không kết nối được tới {host}: {e}")
        return generate_simulation_missions(group_id)

def register_callbacks(app):
    @app.callback(
        Output("api-addmissions-response-message", "children"),
        Input({"type": "addmission-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def handle_add_mission(n_clicks):
        """Thêm nhiệm vụ khi nhấn nút Add"""
        if not n_clicks or all(v is None for v in n_clicks):
            return no_update

        triggered_id = ctx.triggered_id
        if not triggered_id:
            return no_update

        mission_id = triggered_id["index"]
        response_message = add_mission_to_queue(mission_id)
        return response_message

    @app.callback(
        Output("mission-config-modal", "is_open"),
        [Input("create-mission-btn", "n_clicks"), Input("close-config-btn", "n_clicks")],
        [State("mission-config-modal", "is_open")],
    )
    def toggle_modal(open_clicks, close_clicks, is_open):
        """Callback mở/đóng modal cấu hình Mission"""
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

        message, mission_data = create_new_mission(name, desc, group_id)
        if not mission_data:
            return message

        mission_id = mission_data.get("guid")
        for action in TEMP_ACTIONS:
            add_action_to_mission(mission_id, action["action_type"], action["parameters"])
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
    def update_mission_table(n_intervals, selected_group):
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
            missions = [m for m in missions if m["ID"] != mission_id]
            return missions, missions
        return missions, missions