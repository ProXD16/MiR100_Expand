import json, rospy, threading, queue, math
import rospy
from dash import Input, Output, State, no_update
from page_draw_mode.function_draw_mode import *
from make_marker_with_json import *
from geometry_msgs.msg import PoseWithCovarianceStamped, Pose
from tf.transformations import euler_from_quaternion

PATH_GUIDE_JSON = "database_json/path_guide.json"
MARKER_POSITION_JSON = "database_json/position_marker.json"

def read_pose(timeout=5.0):
    pose_queue = queue.Queue()
    stop_event = threading.Event()
    
    def amcl_pose_callback(msg):
        if not stop_event.is_set():
            x = msg.pose.pose.position.x
            y = msg.pose.pose.position.y
            orientation = msg.pose.pose.orientation
            quaternion = [orientation.x, orientation.y, orientation.z, orientation.w]
            _, _, yaw = euler_from_quaternion(quaternion)
            pose_queue.put((x, y, yaw))
            stop_event.set()
            
    def robot_pose_callback(msg):
        if not stop_event.is_set():
            x = msg.position.x
            y = msg.position.y
            orientation = msg.orientation
            quaternion = [orientation.x, orientation.y, orientation.z, orientation.w]
            _, _, yaw = euler_from_quaternion(quaternion)
            pose_queue.put((x, y, yaw))
            stop_event.set()
    
    try:
        rospy.init_node('pose_reader', anonymous=True)
    except rospy.exceptions.ROSException:
        pass 
    
    sub_amcl = rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, amcl_pose_callback)
    sub_robot = rospy.Subscriber('/robot_pose', Pose, robot_pose_callback)
    
    start_time = rospy.get_time()
    while not stop_event.is_set() and (rospy.get_time() - start_time) < timeout:
        rospy.sleep(0.1)
    
    sub_amcl.unregister()
    sub_robot.unregister()
    
    try:
        return pose_queue.get_nowait()
    except queue.Empty:
        rospy.logwarn("Không nhận được dữ liệu từ /amcl_pose hoặc /robot_pose.")
        return None
    
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def load_path_guide():
    try:
        with open(PATH_GUIDE_JSON, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        rospy.logwarn(f"Không thể đọc {PATH_GUIDE_JSON}: {str(e)}")
        return {"start_positions": [], "waypoints": [], "goal_positions": []}

@callback(
    [Output("delete-marker-modal", "is_open"),
     Output("marker-dropdown", "options")],
    Input("delete-marker-btn", "n_clicks"),
    prevent_initial_call=True
)
def show_marker_list(n_clicks):
    markers = load_markers()
    if not markers:
        return True, [] 
    options = [{"label": f"Marker {m['id']}", "value": m['id']} for m in markers]
    return True, options 

@callback(
    Output("delete-marker-modal", "is_open", allow_duplicate=True),
    Input("confirm-delete-btn", "n_clicks"),
    State("marker-dropdown", "value"),
    prevent_initial_call=True
)
def delete_marker(n_clicks, selected_marker):
    if selected_marker is None:
        return no_update  
    markers = load_markers()
    markers = [m for m in markers if m["id"] != selected_marker]
    with open(MARKER_POSITION_JSON, "w") as file:
        json.dump(markers, file, indent=4)
    generate_marker_image()  
    return False  

@callback(
    [Output("add-mission-marker-modal", "is_open", allow_duplicate=True),
     Output("mission-marker-dropdown", "options")],
     Input("add-mission-marker-btn", "n_clicks"),
     prevent_initial_call=True
)
def show_mission_marker_list(n_clicks):
    markers = load_markers()
    if not markers:
        return True, []
    options = [{"label": f"Marker {m['id']}", "value": m['id']} for m in markers]
    return True, options 

@callback(
    Output("add-mission-marker-modal", "is_open", allow_duplicate=True),
    Input("append-mission-btn", "n_clicks"),
    State("mission-marker-dropdown", "value"),
    prevent_initial_call=True
)
def append_marker_to_mission(n_clicks, selected_marker):
    if selected_marker is None:
        return no_update
    
    robot_pose = read_pose(timeout=5.0)
    if not robot_pose:
        rospy.logwarn("Không thể lấy vị trí robot.")
        return True
    
    markers = load_markers()
    selected_marker_data = next((m for m in markers if m["id"] == selected_marker), None)
    if not selected_marker_data:
        rospy.logwarn(f"Marker {selected_marker} không tồn tại.")
        return True

    path_guide = load_path_guide()
    robot_x, robot_y, _ = robot_pose
    robot_near_start = False
    start_positions = path_guide.get("start_positions", [])
    for start_id in start_positions:
        start_marker = next((m for m in markers if m["id"] == start_id), None)
        if start_marker:
            distance = calculate_distance(robot_x, robot_y, start_marker["x"], start_marker["y"])
            if distance <= 0.5:
                robot_near_start = True
                break
    
    is_goal_position = selected_marker in path_guide.get("goal_positions", [])
    markers_to_add = [selected_marker]
    
    if robot_near_start and is_goal_position:
        waypoints = path_guide.get("waypoints", [])
        markers_to_add = waypoints + [selected_marker]
    
    try:
        for marker_id in markers_to_add:
            save_marker_to_json(marker_id, clear=False)
        return False  
    except Exception as e:
        rospy.logwarn(f"Lỗi khi thêm mission: {str(e)}")
        return True 

@callback(
    Output("add-mission-marker-modal", "is_open", allow_duplicate=True),
    Input("clear-and-append-btn", "n_clicks"),
    State("mission-marker-dropdown", "value"),
    prevent_initial_call=True
)
def clear_and_append_marker(n_clicks, selected_marker):
    if selected_marker is None:
        return no_update
    
    robot_pose = read_pose(timeout=5.0)
    if not robot_pose:
        rospy.logwarn("Không thể lấy vị trí robot.")
        return True

    markers = load_markers()
    selected_marker_data = next((m for m in markers if m["id"] == selected_marker), None)
    if not selected_marker_data:
        rospy.logwarn(f"Marker {selected_marker} không tồn tại.")
        return True

    path_guide = load_path_guide()
    robot_x, robot_y, _ = robot_pose
    robot_near_start = False
    start_positions = path_guide.get("start_positions", [])
    for start_id in start_positions:
        start_marker = next((m for m in markers if m["id"] == start_id), None)
        if start_marker:
            distance = calculate_distance(robot_x, robot_y, start_marker["x"], start_marker["y"])
            if distance <= 0.5:
                robot_near_start = True
                break
    
    is_goal_position = selected_marker in path_guide.get("goal_positions", [])
    markers_to_add = [selected_marker]

    if robot_near_start and is_goal_position:
        waypoints = path_guide.get("waypoints", [])
        markers_to_add = waypoints + [selected_marker]
    
    try:
        save_marker_to_json(markers_to_add[0], clear=True)
        for marker_id in markers_to_add[1:]:
            save_marker_to_json(marker_id, clear=False)
        return False  
    except Exception as e:
        rospy.logwarn(f"Lỗi khi thêm mission: {str(e)}")
        return True 