from dash import Input, Output, State, callback, callback_context, no_update
import plotly.graph_objects as go
import numpy as np
import math
from page_draw_mode.function_draw_mode.save_lines import save_lines_to_json
from page_home.shared_data import *
from scipy.interpolate import splrep, splev

def draw_spline5(points, color="black"):
    if len(points) < 6:
        raise ValueError("Cần ít nhất 6 điểm để tạo spline bậc 5.")

    x_vals, y_vals = zip(*points)

    # Tính độ dài cung giữa các điểm
    distances = np.cumsum(np.sqrt(np.diff(x_vals)**2 + np.diff(y_vals)**2))
    distances = np.insert(distances, 0, 0)

    # Tạo spline bậc 5 theo arclength
    tck_x = splrep(distances, x_vals, k=5, s=0)
    tck_y = splrep(distances, y_vals, k=5, s=0)

    t_new = np.linspace(0, distances[-1], 200)
    x_new = splev(t_new, tck_x)
    y_new = splev(t_new, tck_y)

    return go.Scatter(
        x=x_new,
        y=y_new,
        mode="lines",
        line=dict(color=color, width=2),
        showlegend=False,
        name="user_object",
        meta={"type": "spline5"}
    )

@callback(
    Output("draw-spline5-method-modal", "is_open"),
    Input("draw-spline5-button", "n_clicks"),
    State("draw-spline5-mode", "data"),
    State("draw-spline5-method-modal", "is_open"),
    prevent_initial_call=True,
)
def open_draw_spline5_method_modal(n_clicks, draw_spline5_mode, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'draw-spline5-button' and draw_spline5_mode:
        return False
    return not is_open

@callback(
    Output("draw-spline5-method", "data"),
    Output("draw-spline5-method-modal", "is_open", allow_duplicate=True),
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Input("manual-draw-spline5-button", "n_clicks"),
    Input("coordinate-draw-spline5-button", "n_clicks"),
    State("draw-spline5-method-modal", "is_open"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def set_draw_spline5_method(manual_clicks, coordinate_clicks, is_open, figure):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "manual-draw-spline5-button":
        figure["layout"]["clickmode"] = "event"
        return "manual", False, figure
    elif button_id == "coordinate-draw-spline5-button":
        figure["layout"]["clickmode"] = "none"
        return "coordinate", False, figure
    return "", is_open

@callback(
    Output("coordinate-spline5-modal", "is_open"),
    Input("draw-spline5-method", "data"),
    State("coordinate-spline5-modal", "is_open"),
    prevent_initial_call=True,
)
def open_coordinate_spline5_modal(draw_spline5_method, is_open):
    if draw_spline5_method == "coordinate":
        return True
    return False

@callback(
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Output("coordinate-spline5-modal", "is_open", allow_duplicate=True),  
    Input("draw-spline5-button-coordinate", "n_clicks"),
    State("spline5-point1-x", "value"),
    State("spline5-point1-y", "value"),
    State("spline5-point2-x", "value"),
    State("spline5-point2-y", "value"),
    State("spline5-point3-x", "value"),
    State("spline5-point3-y", "value"),
    State("spline5-point4-x", "value"),
    State("spline5-point4-y", "value"),
    State("spline5-point5-x", "value"),
    State("spline5-point5-y", "value"),
    State("spline5-point6-x", "value"),
    State("spline5-point6-y", "value"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def draw_spline5_coordinate(n_clicks, x1, y1, x2, y2, x3, y3, x4, y4, x5, y5, x6, y6, figure):

    try:
        points = [(float(x1), float(y1)), (float(x2), float(y2)), 
                  (float(x3), float(y3)), (float(x4), float(y4)),
                  (float(x5), float(y5)), (float(x6), float(y6))]
    except (ValueError, TypeError):
        print("Invalid coordinates entered for spline.")
        return figure, no_update
    spline_trace = draw_spline5(points)
    figure["data"].append(spline_trace)
    all_lines.append({
        "type": "spline5",
        "points": points
    })

    return figure, False

@callback(
    Output("spline5-coordinates", "data", allow_duplicate=True),
    Input("map-image-draw-mode", "clickData"),
    State("draw-spline5-mode", "data"),
    State("spline5-coordinates", "data"),
    prevent_initial_call=True,
)
def store_spline5_click_points(clickData, draw_mode, stored_points):
    if not draw_mode or not clickData:
        return stored_points or []

    x = clickData["points"][0]["x"]
    y = clickData["points"][0]["y"]

    if not isinstance(stored_points, list):
        stored_points = []

    stored_points.append((x, y))
    return stored_points[:6]  

@callback(
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Output("spline5-coordinates", "data", allow_duplicate=True),
    Input("spline5-coordinates", "data"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def draw_spline5_after_clicks(coord_data, figure):
    if not coord_data or len(coord_data) < 6:
        return no_update, coord_data
    spline_trace = draw_spline5(coord_data)
    figure["data"].append(spline_trace)
    all_lines.append({
        "type": "spline5",
        "points": coord_data
    })
    return figure, []  

@callback(
    Output("draw-spline5-mode", "data"),
    Output("map-image-draw-mode", "figure", allow_duplicate=True),
    Input("draw-spline5-button", "n_clicks"),
    State("draw-spline5-mode", "data"),
    State("map-image-draw-mode", "figure"),
    prevent_initial_call=True,
)
def toggle_draw_spline5_mode(n_clicks, current_state, figure):
    figure["layout"]["clickmode"] = "none"
    return not current_state, figure

@callback(
    Output("draw-spline5-button", "style"),
    Input("draw-spline5-mode", "data"),
    State("button-style-store", "data"),
    prevent_initial_call=True
)
def update_button_spline5_style(is_active, button_style_store):
    default_style = button_style_store["draw_spline5_button"]
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
    