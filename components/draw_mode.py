from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from components import button_style, button_secondary_style

def read_map_info(file_path):
    """
    Đọc thông tin bản đồ từ tệp .info
    """
    map_info = {}
    with open(file_path, 'r') as file:
        for line in file:
            key, value = line.strip().split(': ')
            if key in ['resolution', 'origin_x', 'origin_y']:
                map_info[key] = float(value)
            else:
                map_info[key] = int(float(value))  
    return map_info

def real_to_map_coords(x, y, map_info):
    """
    Chuyển đổi tọa độ thực tế sang tọa độ bản đồ
    """
    map_x = (x - map_info['origin_x']) / map_info['resolution']
    map_y = (y - map_info['origin_y']) / map_info['resolution']
    return map_x, map_y

def create_draw_mode_layout():
    map_info = read_map_info('static/map_image.info')
    grid_size = 1  
    grid_color = "#E0E0E0"  # Lighter grid
    axis_color = "#333333" 
    grid_lines = []
    max_x = map_info['width'] * map_info['resolution']
    max_y = map_info['height'] * map_info['resolution']
    invisible_x_range = np.linspace(0, max_x, 80)
    invisible_y_range = np.linspace(0, max_y, 80)
    invisible_df = pd.DataFrame([(x, y) for x in invisible_x_range for y in invisible_y_range], columns=["x", "y"])
    invisible_scatter = go.Scatter(
        x=invisible_df["x"],
        y=invisible_df["y"],
        mode="markers",
        marker=dict(size=1, opacity=0),  # Invisible
        showlegend=False,
        hoverinfo="none"
    )
    for i in range(0, int(max_x), grid_size): 
        grid_lines.append(
            go.Scatter(
                x=[i, i],
                y=[0, max_y], 
                mode="lines",
                line=dict(color=grid_color, width=1),
                hoverinfo="none",
                showlegend=False,
            )
        )
        grid_lines.append(
            go.Scatter(
                x=[0, max_x],
                y=[i, i],
                mode="lines",
                line=dict(color=grid_color, width=1),
                hoverinfo="none",
                showlegend=False,
            )
        )
    axis_lines = [
        go.Scatter(
            x=[0, max_x],
            y=[0, 0],
            mode="lines",
            line=dict(color=axis_color, width=2),
            hoverinfo="none",
            showlegend=False,
        ),
        go.Scatter(
            x=[0, 0],
            y=[0, max_y],
            mode="lines",
            line=dict(color=axis_color, width=2),
            hoverinfo="none",
            showlegend=False,
        ),
    ]
    map_image = go.layout.Image(
        source="/static/map_for_figure.png",  
        xref="x",
        yref="y",
        x=0,
        y=max_y, 
        sizex=max_x, 
        sizey=max_y, 
        sizing="stretch",
        layer="below",  
    )

    map_layout = go.Layout(
        xaxis=dict(showgrid=True, range=[0, max_x], fixedrange=False, zeroline=False, gridcolor=grid_color),  # Hide zeroline and customize grid
        yaxis=dict(showgrid=True, range=[0, max_y], scaleanchor="x", scaleratio=1, fixedrange=False, zeroline=False, gridcolor=grid_color),
        plot_bgcolor="white",  # Set plot background to white
        margin=dict(l=0, r=0, t=0, b=0),
        images=[map_image],
        shapes=[],  
        dragmode=False,
        clickmode="none",
        meta={"figure_id": "map-draw-figure"}
    ) 
    map_figure = go.Figure(data=grid_lines + axis_lines + [invisible_scatter], layout=map_layout)

    draw_mode_layout = html.Div(  # Thêm div bao bọc
        style={'backgroundColor': '#F5F5F5', 'height': '100vh', 'fontFamily': 'Arial, sans-serif'},  # Light background and font
        children=[
            html.Div( # Div bên trong, chứa nội dung thực
                [
                    html.H3("DRAW", className="mb-3", style={"color": "#34495E", "fontWeight": "bold"}),
                    html.P("Edit and draw the map.", className="text-muted", style={"fontSize": "1.1em"}),
                    dbc.ButtonGroup(
                        [
                            html.Button(
                                "line",
                                id="draw-line-button",
                                style=button_style,
                                className="fas fa-pen-nib me-2",
                                n_clicks=0,
                            ),
                            html.Button(
                                'polyline',
                                id="draw-polyline-button",
                                style=button_style,
                                className="fas fa-draw-polygon me-2",
                                n_clicks=0,
                            ),
                            html.Button(
                                "arc",
                                id="draw-arc-button",
                                style=button_style,
                                className="fas fa-circle-notch me-2",
                                n_clicks=0,
                            ),
                            html.Button(
                                "spline 3",
                                id="draw-spline3-button",
                                style=button_style,
                                className="fas fa-wave-square me-2",
                                n_clicks=0,
                            ),
                            html.Button(
                                "spline 5",
                                id="draw-spline5-button",
                                style=button_style,
                                className="fas fa-bezier-curve me-2",
                                n_clicks=0,
                            ),

                        ],
                    ),
                    html.Button(
                        "save",
                        id="save-lines-button",
                        className="fas fa-save me-2",
                        style=button_style,
                        n_clicks=0,
                    ),
                    html.Button(
                        "clear",
                        id="clear-lines-button",
                        className="fas fa-eraser me-2",
                        style=button_style,
                        n_clicks=0,
                    ),
                    html.Button(
                        "clear data",
                        id="clear-all-lines-button",
                        className="fas fa-trash me-2",
                        style=button_style,
                        n_clicks=0,
                    ),

                    dcc.Store(id='draw-line-mode', data=False), 
                    dcc.Store(id='draw-arc-mode', data=False),
                    dcc.Store(id='draw-polyline-mode', data=False),
                    dcc.Store(id='draw-spline3-mode', data=False),
                    dcc.Store(id='draw-spline5-mode', data=False),
                    dcc.Store(id='line-coordinates', data={}),  
                    dcc.Store(id='arc-coordinates', data={}),
                    dcc.Store(id='spline3-coordinates', data={}),
                    dcc.Store(id='spline5-coordinates', data={}),
                    dcc.Store(id='polyline-coordinates', data={}),
                    dcc.Store(id='draw-method', data='manual'), 
                    dcc.Store(id='draw-arc-method', data='manual'),
                    dcc.Store(id='draw-polyline-method', data='manual'),
                    dcc.Store(id='draw-spline3-method', data='manual'),
                    dcc.Store(id='draw-spline5-method', data='manual'),

                    dcc.Graph(
                        id="map-image-draw-mode",
                        figure=map_figure,
                        style={"width": "100%", "height": "600px", "border": "1px solid #CED4DA", "borderRadius": "8px"}, #Rounded corners and softer border
                        config={"scrollZoom": True, 'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'drawline', 'drawrect', 'erasedata', 'drawclosedpath', 'drawcircle', 'drawrect']},  # Cho phép zoom bằng scroll, remove select2d and lasso2d and disable default drawing tool
                    ),
                    html.P("The map is ready for your work.", className="text-info mt-2", style={"fontStyle": "italic"}),  # Italic status message
                    html.Div(id='draw-mode-output'), 
                    dbc.Modal(  
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Choose Drawing Method (Line)")),
                            dbc.ModalBody(
                                [
                                    dbc.Button("Manual Draw", id="manual-draw-button", color="primary", className="me-2", style=button_style),
                                    dbc.Button("Enter Coordinates", id="coordinate-draw-button", color="secondary", style=button_style),
                                ]
                            ),
                        ],
                        id="draw-method-modal",
                        is_open=False,
                    ),
                    dbc.Modal(  
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Choose Drawing Method (Polyline)")),
                            dbc.ModalBody(
                                [
                                    dbc.Button("Manual Draw", id="manual-draw-polyline-button", color="primary", className="me-2", style=button_style),
                                    dbc.Button("Enter Coordinates", id="coordinate-draw-polyline-button", color="secondary", style=button_style),
                                ]
                            ),
                        ],
                        id="draw-polyline-method-modal",
                        is_open=False,
                    ),
                    dbc.Modal(  
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Choose Drawing Method (Arc)")),
                            dbc.ModalBody(
                                [
                                    dbc.Button("Manual Draw", id="manual-draw-arc-button", color="primary", className="me-2", style=button_style),
                                    dbc.Button("Enter Coordinates", id="coordinate-draw-arc-button", color="secondary", style=button_style),
                                ]
                            ),
                        ],
                        id="draw-arc-method-modal",
                        is_open=False,
                    ),
                    dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Choose Drawing Method (Spline 3)")),
                            dbc.ModalBody(
                                [
                                    dbc.Button("Manual Draw", id="manual-draw-spline3-button", color="primary", className="me-2", style=button_style),
                                    dbc.Button("Enter Coordinates", id="coordinate-draw-spline3-button", color="secondary", style=button_style),
                                ]
                            ),
                        ],
                        id="draw-spline3-method-modal",
                        is_open=False,
                    ),
                    dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Choose Drawing Method (Spline 5)")),
                            dbc.ModalBody(
                                [
                                    dbc.Button("Manual Draw", id="manual-draw-spline5-button", color="primary", className="me-2", style=button_style),
                                    dbc.Button("Enter Coordinates", id="coordinate-draw-spline5-button", color="secondary", style=button_style),
                                ]
                            ),
                        ],
                        id="draw-spline5-method-modal",
                        is_open=False,
                    ),
                    dbc.Modal(  
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Enter Coordinates (Line)")),
                            dbc.ModalBody(
                                [
                                    dbc.Label("Start X:", style={"fontWeight": "bold"}), #Bold labels
                                    dbc.Input(type="number", id="start-x", className="mb-2"), #Margin bottom
                                    dbc.Label("Start Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="start-y", className="mb-2"),
                                    dbc.Label("End X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="end-x", className="mb-2"),
                                    dbc.Label("End Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="end-y", className="mb-2"),
                                ]
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button("Draw", id="draw-button", color="primary", style=button_style),
                                    dbc.Button("Cancel", id="cancel-button", style=button_style),
                                ]
                            ),
                        ],
                        id="coordinate-modal",
                        is_open=False,
                    ),
                    dbc.Modal(  
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Enter Coordinates (Polyline)")),
                            dbc.ModalBody(
                                [
                                    dbc.Label("Start X:", style={"fontWeight": "bold"}), #Bold labels
                                    dbc.Input(type="number", id="polyline-start-x", className="mb-2"), #Margin bottom
                                    dbc.Label("Start Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="polyline-start-y", className="mb-2"),
                                    dbc.Label("End X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="polyline-end-x", className="mb-2"),
                                    dbc.Label("End Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="polyline-end-y", className="mb-2"),
                                ]
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button("Draw", id="draw-polyline-button", color="primary", style=button_style),
                                    dbc.Button("Cancel", id="cancel-polyline-button", style=button_style),
                                ]
                            ),
                        ],
                        id="coordinate-polyline-modal",
                        is_open=False,
                    ),
                    dbc.Modal(  
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Enter Coordinates (Arc - 3 Points)")),
                            dbc.ModalBody(
                                [
                                    dbc.Label("Point 1 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="point1-x", className="mb-2"),
                                    dbc.Label("Point 1 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="point1-y", className="mb-2"),
                                    dbc.Label("Point 2 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="point2-x", className="mb-2"),
                                    dbc.Label("Point 2 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="point2-y", className="mb-2"),
                                    dbc.Label("Point 3 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="point3-x", className="mb-2"),
                                    dbc.Label("Point 3 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="point3-y", className="mb-2"),
                                ]
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button("Draw", id="draw-arc-button-coordinate", color="primary", style=button_style),
                                    dbc.Button("Cancel", id="cancel-arc-button", style=button_style),
                                ]
                            ),
                        ],
                        id="coordinate-arc-modal",
                        is_open=False,
                    ),
                    dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Enter Coordinates (Spline 3 - 4 Points)")),
                            dbc.ModalBody(
                                [
                                    dbc.Label("Point 1 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline3-point1-x", className="mb-2"),
                                    dbc.Label("Point 1 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline3-point1-y", className="mb-2"),
                                    dbc.Label("Point 2 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline3-point2-x", className="mb-2"),
                                    dbc.Label("Point 2 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline3-point2-y", className="mb-2"),
                                    dbc.Label("Point 3 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline3-point3-x", className="mb-2"),
                                    dbc.Label("Point 3 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline3-point3-y", className="mb-2"),
                                    dbc.Label("Point 4 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline3-point4-x", className="mb-2"),
                                    dbc.Label("Point 4 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline3-point4-y", className="mb-2"),
                                ]
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button("Draw", id="draw-spline3-button-coordinate", color="primary", style=button_style),
                                    dbc.Button("Cancel", id="cancel-spline3-button", style=button_style),
                                ]
                            ),
                        ],
                        id="coordinate-spline3-modal",
                        is_open=False,
                    ),
                    dbc.Modal(
                        [
                            dbc.ModalHeader(dbc.ModalTitle("Enter Coordinates (Spline 5 - 6 Points)")),
                            dbc.ModalBody(
                                [
                                    dbc.Label("Point 1 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point1-x", className="mb-2"),
                                    dbc.Label("Point 1 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point1-y", className="mb-2"),
                                    dbc.Label("Point 2 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point2-x", className="mb-2"),
                                    dbc.Label("Point 2 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point2-y", className="mb-2"),
                                    dbc.Label("Point 3 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point3-x", className="mb-2"),
                                    dbc.Label("Point 3 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point3-y", className="mb-2"),
                                    dbc.Label("Point 4 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point4-x", className="mb-2"),
                                    dbc.Label("Point 4 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point4-y", className="mb-2"),
                                     dbc.Label("Point 5 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point5-x", className="mb-2"),
                                    dbc.Label("Point 5 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point5-y", className="mb-2"),
                                     dbc.Label("Point 6 X:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point6-x", className="mb-2"),
                                    dbc.Label("Point 6 Y:", style={"fontWeight": "bold"}),
                                    dbc.Input(type="number", id="spline5-point6-y", className="mb-2"),
                                ]
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button("Draw", id="draw-spline5-button-coordinate", color="primary", style=button_style),
                                    dbc.Button("Cancel", id="cancel-spline5-button", style=button_style),
                                ]
                            ),
                        ],
                        id="coordinate-spline5-modal",
                        is_open=False,
                    ),

                    html.Div(id="pixel-coordinates"),
                    html.Div(id="real-world-coordinates"),
                    dcc.Store(id="button-style-store", data={"draw_line_button": button_style, "draw_arc_button": button_style,
                                                             "draw_spline3_button": button_style, "draw_spline5_button": button_style,
                                                             "draw_polyline_button": button_style}),
                ],
                style={  # Giữ style cũ, nhưng loại bỏ background
                    "padding": "30px",
                    "flex": "1",
                    #"background": "#ECF0F1",  # Loại bỏ dòng này
                    "marginLeft": "auto",   #Centered content
                    "marginRight": "auto",
                    "marginTop": "50px",
                    "maxWidth": "1200px",      #Limit width
                    "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.1)",   #More prominent shadow
                    "borderRadius": "12px",        #Rounded corners
                    "overflowY": "auto",
                },
            )
        ]
    )
    return draw_mode_layout