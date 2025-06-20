from dash import Input, Output, State, callback, callback_context, no_update
import plotly.graph_objects as go
import numpy as np
import math
from page_draw_mode.function_draw_mode.save_lines import save_lines_to_json
from page_home.shared_data import *
from scipy.interpolate import CubicSpline

def draw_spline3(points, color="black"):
    if len(points) < 4:
        raise ValueError("Cần ít nhất 4 điểm để tạo spline bậc 3.")

    x_vals, y_vals = zip(*points)

    # Kiểm tra xem spline nên nội suy theo trục nào
    dx = max(x_vals) - min(x_vals)
    dy = max(y_vals) - min(y_vals)

    if dx >= dy:
        # Nội suy theo trục X (giống test_spine_3.py)
        sorted_points = sorted(points, key=lambda p: p[0])
        x_vals, y_vals = zip(*sorted_points)
        cs = CubicSpline(x_vals, y_vals)
        x_new = np.linspace(min(x_vals), max(x_vals), 100)
        y_new = cs(x_new)
    else:
        # Nội suy theo trục Y (dạng đứng)
        sorted_points = sorted(points, key=lambda p: p[1])
        x_vals, y_vals = zip(*sorted_points)
        cs = CubicSpline(y_vals, x_vals)
        y_new = np.linspace(min(y_vals), max(y_vals), 100)
        x_new = cs(y_new)

    return go.Scatter(
        x=x_new,
        y=y_new,
        mode="lines",
        line=dict(color=color, width=2),
        showlegend=False,
        name="user_object",
        meta={"type": "spline3"}
    )

@callback(
    Output("draw-spline3-method-modal", "is_open"),
    Input("draw-spline3-button", "n_clicks"),
    State("draw-spline3-mode", "data"),
    State("draw-spline3-method-modal", "is_open"),
    prevent_initial_call=True,
)
def open_draw_spline3_method_modal(n_clicks, draw_spline3_mode, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'draw-spline3-button' and draw_spline3_mode:
        return False
    return not is_open

@callback(
    Output("draw-spline3-method", "data"),
    Output("draw-spline3-method-modal", "is_open", allow_duplicate=True),
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Input("manual-draw-spline3-button", "n_clicks"),
    Input("coordinate-draw-spline3-button", "n_clicks"),
    State("draw-spline3-method-modal", "is_open"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def set_draw_spline3_method(manual_clicks, coordinate_clicks, is_open, figure):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "manual-draw-spline3-button":
        figure["layout"]["clickmode"] = "event"
        return "manual", False, figure
    elif button_id == "coordinate-draw-spline3-button":
        figure["layout"]["clickmode"] = "none"
        return "coordinate", False, figure
    return "", is_open

@callback(
    Output("coordinate-spline3-modal", "is_open"),
    Input("draw-spline3-method", "data"),
    State("coordinate-spline3-modal", "is_open"),
    prevent_initial_call=True,
)
def open_coordinate_spline3_modal(draw_spline3_method, is_open):
    if draw_spline3_method == "coordinate":
        return True
    return False

@callback(
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Output("coordinate-spline3-modal", "is_open", allow_duplicate=True),  
    Input("draw-spline3-button-coordinate", "n_clicks"),
    State("spline3-point1-x", "value"),
    State("spline3-point1-y", "value"),
    State("spline3-point2-x", "value"),
    State("spline3-point2-y", "value"),
    State("spline3-point3-x", "value"),
    State("spline3-point3-y", "value"),
    State("spline3-point4-x", "value"),
    State("spline3-point4-y", "value"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def draw_spline3_coordinate(n_clicks, x1, y1, x2, y2, x3, y3, x4, y4, figure):
    try:
        points = [(float(x1), float(y1)), (float(x2), float(y2)), (float(x3), float(y3)), (float(x4), float(y4))]
    except (ValueError, TypeError):
        print("Invalid coordinates entered for spline.")
        return figure, no_update
    spline_trace = draw_spline3(points)
    figure["data"].append(spline_trace)
    all_lines.append({
        "type": "spline3",
        "points": points
    })

    return figure, False

@callback(
    Output("spline3-coordinates", "data", allow_duplicate=True),
    Input("map-image-draw-mode", "clickData"),
    State("draw-spline3-mode", "data"),
    State("spline3-coordinates", "data"),
    prevent_initial_call=True,
)
def store_spline3_click_points(clickData, draw_mode, stored_points):
    if not draw_mode or not clickData:
        return stored_points or []
    x = clickData["points"][0]["x"]
    y = clickData["points"][0]["y"]
    if not isinstance(stored_points, list):
        stored_points = []
    stored_points.append((x, y))
    return stored_points[:4]  

@callback(
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Output("spline3-coordinates", "data", allow_duplicate=True),
    Input("spline3-coordinates", "data"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def draw_spline3_after_clicks(coord_data, figure):
    if not coord_data or len(coord_data) < 4:
        return no_update, coord_data

    try:
        spline_trace = draw_spline3(coord_data)
        figure["data"].append(spline_trace)
        all_lines.append({
            "type": "spline3",
            "points": coord_data
        })
        return figure, []
    except Exception as e:
        print(f"Error drawing spline3: {e}")
        return no_update, []

@callback(
    Output("draw-spline3-mode", "data"),
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Input("draw-spline3-button", "n_clicks"),
    State("draw-spline3-mode", "data"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def toggle_draw_spline3_mode(n_clicks, current_state, figure):
    figure["layout"]["clickmode"] = "none"
    return not current_state, figure

@callback(
    Output("draw-spline3-button", "style"),
    Input("draw-spline3-mode", "data"),
    State("button-style-store", "data"),
    prevent_initial_call=True
)
def update_button_spline3_style(is_active, button_style_store):
    default_style = button_style_store["draw_spline3_button"]
    active_button_style = {
        "padding": "8px 16px",
        "border": "1px solid #2ecc71",
        "color": "white",
        "background-color": "#2ecc71",
        "border-radius": "5px",
        "transition": "all 0.3s ease-in-out",
        "cursor": "pointer",
    }
    if is_active:
        return active_button_style
    else:
        return default_style
    