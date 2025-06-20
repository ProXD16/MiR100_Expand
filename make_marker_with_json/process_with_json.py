import json
import os
import rospy
from move_base_msgs.msg import MoveBaseActionResult

JSON_FILE_PATH = "database_json/position_marker.json"
MAP_JSON_PATH = "static/map_image.json"
MISSION_JSON_PATH = "database_json/marker_mission.json"
DOCKER_JSON_PATH = "database_json/docker.json"

def load_map_data():
    with open(MAP_JSON_PATH, "r") as file:
        map_data = json.load(file)
    return map_data

def load_markers():
    if os.path.exists(JSON_FILE_PATH):
        try:
            with open(JSON_FILE_PATH, "r") as file:
                data = json.load(file)
                return data
        except json.JSONDecodeError:
            return []
    return []

def show_marker_list(n_clicks):
    markers = load_markers()
    if not markers:
        return True, [] 
    options = [{"label": f"Marker {m['id']}", "value": m["id"]} for m in markers]
    return True, options  

def save_position_to_json(name, x, y, z, w):
    os.makedirs(os.path.dirname(JSON_FILE_PATH), exist_ok=True)
    data = []
    if os.path.exists(JSON_FILE_PATH):
        with open(JSON_FILE_PATH, "r") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    new_id = len(data) + 1 
    new_marker = {"id": new_id, "name": name,"x": x, "y": y, "z": z, "w": w}
    data.append(new_marker)
    with open(JSON_FILE_PATH, "w") as file:
        json.dump(data, file, indent=4)

def save_docker_to_json(name, x, y, z, w):
    os.makedirs(os.path.dirname(DOCKER_JSON_PATH), exist_ok=True)
    data = []
    if os.path.exists(DOCKER_JSON_PATH):
        with open(DOCKER_JSON_PATH, "r") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    new_id = len(data) + 1 
    new_docker = {"id": new_id, "name": name, "x": x, "y": y, "z": z, "w": w}
    data.append(new_docker)
    with open(DOCKER_JSON_PATH, "w") as file:
        json.dump(data, file, indent=4)

def convert_to_pixel(x, y):
    map_data = load_map_data()
    map_width = map_data["width"]  
    map_height = map_data["height"]
    resolution_x = map_data["resolution_x"] 
    resolution_y = map_data["resolution_y"]
    origin_x = map_data["origin_x"] 
    origin_y = map_data["origin_y"]
    pixel_x = int((x - origin_x) / resolution_x)
    pixel_y = int((y - origin_y) / resolution_y)
    pixel_y = map_height - pixel_y  
    return pixel_x, pixel_y

def check_goal_status():
    goal_status = rospy.wait_for_message('/move_base/result', MoveBaseActionResult)
    return goal_status.status.status == 3 

def remove_completed_mission(mission_id):
    if os.path.exists(MISSION_JSON_PATH):
        try:
            with open(MISSION_JSON_PATH, "r") as file:
                missions = json.load(file)
            missions = [m for m in missions if m["id"] != mission_id]
            with open(MISSION_JSON_PATH, "w") as file:
                json.dump(missions, file, indent=4)
        except json.JSONDecodeError:
            rospy.logwarn("Lỗi đọc file JSON!")

def save_marker_to_json(marker_id, clear=False):
    os.makedirs(os.path.dirname(MISSION_JSON_PATH), exist_ok=True)
    
    if clear or not os.path.exists(MISSION_JSON_PATH):  
        data = []  
    else:
        try:
            with open(MISSION_JSON_PATH, "r") as file:
                data = json.load(file)
        except json.JSONDecodeError:
            data = []
    markers = load_markers()
    marker = next((m for m in markers if m["id"] == marker_id), None)
    if marker:
        data.append(marker)  
    with open(MISSION_JSON_PATH, "w") as file:
        json.dump(data, file, indent=4)

def load_mission_data():
    if os.path.exists(MISSION_JSON_PATH):
        try:
            with open(MISSION_JSON_PATH, "r") as file:
                data = json.load(file)
                return data
        except json.JSONDecodeError:
            return []
    return []