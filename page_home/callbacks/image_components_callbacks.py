import dash, time, random, os
from dash import Input, Output
from page_draw_mode.function_draw_mode import *
from dash.exceptions import PreventUpdate
from database_json import *

@callback(
    Output("lidar-image", "src"),
    Input("interval-component", "n_intervals")
)
def update_lidar_image(n):
    timestamp = int(time.time())
    return f"/static/lidar_image.png?{timestamp}"

@callback(
    [Output("lidar-f-image", "src"), Output("lidar-b-image", "src")],
    Input("interval-component", "n_intervals")
)
def update_lidar_images(n):
    timestamp = int(time.time())
    return (
        f"/static/f_scan_image.png?{timestamp}",
        f"/static/b_scan_image.png?{timestamp}"
    )

@callback(
    [Output("path-image", "src")],
    Input("interval-component", "n_intervals")
)
def update_path_image(n):
    random_value = random.randint(1, 100000)
    return (
        f"/static/path_image.png?random={random_value}",
    )

@callback(
    Output("paths-image", "src"),
    Input("interval-component", "n_intervals")
)
def update_lines_image(n):
    timestamp = int(time.time())
    return f"/static/path_img.png?{timestamp}"

@callback(
    Output("markers-image", "src"),
    Input("interval-component", "n_intervals")
)
def update_markers_image(n):
    timestamp = int(time.time())
    return f"/static/all_markers.png?{timestamp}"

@callback(
    Output("dockers-image", "src"),
    Input("interval-component", "n_intervals")
)
def update_markers_image(n):
    timestamp = int(time.time())
    return f"/static/dockers.png?{timestamp}"

@callback(
    Output("map-image", "src"),
    Input("interval-component", "n_intervals")
)
def update_map_image(n):
    timestamp = int(time.time())
    return f"/static/map_image.png?{timestamp}"

last_modified_time = 0

@callback(
    [Output("robot-image", "src")],
    Input("interval-component", "n_intervals")
)
def update_robot_image(n):
    global last_modified_time
    image_path = "static/robot_image.png"
    try:
        modified_time = os.path.getmtime(image_path)
    except FileNotFoundError:
        print(f"Error: Image file not found: {image_path}")
        return [dash.no_update]
    except Exception as e:
        print(f"Other error getting modified time: {e}")
        return [dash.no_update]
    if modified_time > last_modified_time:
        last_modified_time = modified_time
        #print("dash- callback updating img with: " + image_path + "?time=" + str(modified_time))
        return [f"/static/robot_image.png?time={modified_time}"]
    else:
        raise PreventUpdate

@callback(
    Output("costmap-image", "src"),
    Input("interval-component", "n_intervals")
)
def update_costmap_image(n):
    timestamp = int(time.time())
    return f"/static/cost_map_image.png?{timestamp}"