from dash import Input, Output, State, callback, callback_context, no_update
import plotly.graph_objects as go
import numpy as np
import math
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

@callback(
    Output("draw-polyline-method-modal", "is_open"),
    Input("draw-polyline-button", "n_clicks"),
    State("draw-polyline-mode", "data"),
    State("draw-polyline-method-modal", "is_open"),
    prevent_initial_call=True,
)
def open_draw_polyline_method_modal(n_clicks, draw_polyline_mode, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'draw-polyline-button' and draw_polyline_mode:
        return False
    return not is_open

@callback(
    Output("draw-polyline-method", "data"),
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
    return no_update, is_open, figure

@callback(
    Output("coordinate-polyline-modal", "is_open"),
    Input("draw-polyline-method", "data"),
    State("coordinate-polyline-modal", "is_open"),
    prevent_initial_call=True,
)
def open_polyline_coordinate_modal(draw_polyline_method, is_open):
    if draw_polyline_method == "coordinate":
        return True
    return False

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
    from page_home.shared_data import all_lines
    if n_clicks is None:
        return no_update, no_update

    try:
        start_x = float(start_x)
        start_y = float(start_y)
        end_x = float(end_x)
        end_y = float(end_y)
    except (ValueError, TypeError):
        print("Invalid coordinates entered.")
        return figure, no_update

    line_data = go.Scatter(
        x=[start_x, end_x],
        y=[start_y, end_y],
        mode="lines",
        line=dict(color="black", width=4),
        showlegend=False,
    )
    figure["data"].append(line_data)
    all_lines.append({"type": "line", "x": [start_x, end_x], "y": [start_y, end_y]})
    return figure, False

@callback(
    Output("draw-polyline-mode", "data"),
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
            return True, False, figure
    return False, True, figure

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

    # Vẽ từng đoạn giữa các điểm liên tiếp
    if len(polyline_points) >= 2:
        x_vals = [polyline_points[-2][0], polyline_points[-1][0]]
        y_vals = [polyline_points[-2][1], polyline_points[-1][1]]
        new_trace = {
            "type": "scatter",
            "x": x_vals,
            "y": y_vals,
            "mode": "lines",
            "line": {"color": "black", "width": 2},
            "showlegend": False,
            "meta": {"type": "polyline"},
            "name": "user_object"
        }
        figure["data"].append(new_trace)

    return figure
