from dash import Input, Output, State, callback, callback_context, no_update
import plotly.graph_objects as go
from page_home.shared_data import all_lines

polyline_points = []

def draw_polyline(points, color="black"):
    x_vals, y_vals = zip(*points)
    return go.Scatter(
        x=x_vals,
        y=y_vals,
        mode="lines",
        line=dict(color=color, width=2),
        showlegend=False,
        name="user_object",
        meta={"type": "polyline"}
    )

# Mở modal chọn phương thức
@callback(
    Output("draw-polyline-method-modal", "is_open"),
    Input("draw-polyline-button", "n_clicks"),
    State("draw-polyline-mode", "data"),
    State("draw-polyline-method-modal", "is_open"),
    prevent_initial_call=True,
)
def open_draw_polyline_method_modal(n_clicks, draw_polyline_mode, is_open):
    if draw_polyline_mode:
        return False
    return not is_open

# Chọn phương thức vẽ
@callback(
    Output("draw-polyline-method", "data", allow_duplicate=True),
    Output("draw-polyline-method-modal", "is_open", allow_duplicate=True),
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Input("manual-draw-polyline-button", "n_clicks"),
    Input("coordinate-draw-polyline-button", "n_clicks"),
    State("draw-polyline-method-modal", "is_open"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def set_draw_polyline_method(manual_clicks, coordinate_clicks, is_open, figure):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "manual-draw-polyline-button":
        figure["layout"]["clickmode"] = "event"
        return "manual", False, figure
    elif button_id == "coordinate-draw-polyline-button":
        figure["layout"]["clickmode"] = "none"
        return "coordinate", False, figure
    return no_update, no_update, figure

# Toggle chế độ vẽ polyline thủ công
@callback(
    Output("draw-polyline-mode", "data", allow_duplicate=True),
    Output("draw-polyline-method-modal", "is_open", allow_duplicate=True),
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Input("draw-polyline-button", "n_clicks"),
    State("draw-polyline-mode", "data"),
    State("draw-polyline-method", "data"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def toggle_draw_polyline(n_clicks, mode_active, method, figure):
    global polyline_points
    if method == "manual":
        if mode_active:
            if len(polyline_points) >= 2:
                trace = draw_polyline(polyline_points)
                figure["data"].append(trace)
                all_lines.append({"type": "polyline", "points": polyline_points.copy()})
            polyline_points.clear()
            return False, False, figure
        else:
            polyline_points.clear()
            return True, False, figure
    return False, True, figure


# Lưu từng đoạn khi click điểm mới
@callback(
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Input("map-image-draw-mode", "clickData"),
    State("map-image-draw-mode", "figure"),
    State("draw-polyline-mode", "data"),
    prevent_initial_call=True,
)
def store_polyline_point(click_data, figure, polyline_mode):
    if not polyline_mode or click_data is None:
        return no_update

    point = click_data["points"][0]
    x, y = point["x"], point["y"]
    polyline_points.append((x, y))

    if len(polyline_points) >= 2:
        x_vals = [polyline_points[-2][0], polyline_points[-1][0]]
        y_vals = [polyline_points[-2][1], polyline_points[-1][1]]
        new_trace = go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines",
            line=dict(color="black", width=2),
            showlegend=False,
            name="user_object",
            meta={"type": "polyline"}
        )
        figure["data"].append(new_trace)

    return figure

# Modal vẽ bằng tọa độ
@callback(
    Output("coordinate-polyline-modal", "is_open", allow_duplicate=True),
    Input("draw-polyline-method", "data"),
    State("coordinate-polyline-modal", "is_open"),
    prevent_initial_call=True,
)
def open_polyline_coordinate_modal(draw_polyline_method, is_open):
    if draw_polyline_method == "coordinate":
        return True
    return False

# Vẽ polyline từ input tọa độ
@callback(
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Output("coordinate-polyline-modal", "is_open", allow_duplicate=True),
    Input("draw-polyline-button-coordinate", "n_clicks"),
    State("polyline-start-x", "value"),
    State("polyline-start-y", "value"),
    State("polyline-end-x", "value"),
    State("polyline-end-y", "value"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def draw_polyline_coordinate(n_clicks, start_x, start_y, end_x, end_y, figure):
    try:
        start_x = float(start_x)
        start_y = float(start_y)
        end_x = float(end_x)
        end_y = float(end_y)
    except (ValueError, TypeError):
        return figure, no_update

    trace = go.Scatter(
        x=[start_x, end_x],
        y=[start_y, end_y],
        mode="lines",
        line=dict(color="black", width=2),
        showlegend=False,
        name="user_object",
        meta={"type": "line"}
    )
    figure["data"].append(trace)
    all_lines.append({"type": "polyline", "x": [start_x, end_x], "y": [start_y, end_y]})
    return figure, False

# @callback(
#     Output("draw-polyline-mode", "data", allow_duplicate=True),
#     Output("map-image-draw-mode", "figure", allow_duplicate=True),
#     Input("draw-polyline-button", "n_clicks"),
#     State("draw-polyline-mode", "data"),
#     State("map-image-draw-mode", "figure"),
#     prevent_initial_call=True,
# )
# def toggle_draw_polyline_mode(n_clicks, current_state, figure):
#     figure["layout"]["clickmode"] = "none"
#     return not current_state, figure

@callback(
    Output("draw-polyline-button", "style"),
    Input("draw-polyline-mode", "data"),
    State("button-style-store", "data"),
    prevent_initial_call=True
)
def update_button_polyline_style(is_active, button_style_store):
    default_style = button_style_store["draw_polyline_button"]
    active_button_style = {
        "padding": "8px 16px",
        "border": "1px solid #2ecc71",
        "color": "white",
        "background-color": "#2ecc71",
        "border-radius": "5px",
        "transition": "all 0.3s ease-in-out",
        "cursor": "pointer",
    }               
    if not is_active:
        return active_button_style
    else:
        return default_style