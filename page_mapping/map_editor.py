# pages/map_editor.py
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# Đăng ký trang này với ứng dụng Dash
dash.register_page(__name__, path='/map-editor', title='Map Editor')

# --- Tạo một Figure trống để làm "bản vẽ" ---
fig = go.Figure()

# Tùy chỉnh layout để giống với hình ảnh
fig.update_layout(
    xaxis=dict(showgrid=False, zeroline=False, visible=False),
    yaxis=dict(showgrid=False, zeroline=False, visible=False),
    plot_bgcolor='#E9E9E9',  # Màu nền xám nhạt cho khu vực vẽ
    paper_bgcolor='#F0F0F0', # Màu nền xám cho toàn bộ component
    margin=dict(l=10, r=10, t=10, b=10),
    shapes=[
        # Vẽ một hình chữ nhật trắng ở giữa để làm canvas
        go.layout.Shape(
            type="rect",
            xref="paper", yref="paper",
            x0=0.1, y0=0.05, x1=0.9, y1=0.95,
            line=dict(color="Black", width=1),
            fillcolor="white",
        )
    ]
)

# --- Layout của trang ---
layout = dbc.Container([
    # Header và nút "Go back"
    dbc.Row([
        dbc.Col([
            html.H1("123", className="mt-3"), # Tên bản đồ, có thể làm động
            html.P("Edit and draw the map", className="text-muted")
        ], width=6),
        dbc.Col(
            dcc.Link(
                dbc.Button("Go back", outline=True, color="secondary"),
                href="/"
            ),
            width=6,
            className="d-flex justify-content-end align-items-center"
        )
    ], className="mb-3"),

    # Khu vực chính chứa bản đồ và các công cụ
    dbc.Row([
        # Cột bên trái chứa bản đồ
        dbc.Col([
            # Thông báo hướng dẫn
            html.Div(
                "Drag the map to move your view or use the zoom-in and -out buttons to zoom",
                style={
                    'position': 'absolute',
                    'top': '20px',
                    'left': '20px',
                    'zIndex': '10',
                    'backgroundColor': 'rgba(0, 0, 0, 0.7)',
                    'color': 'white',
                    'padding': '10px',
                    'borderRadius': '5px'
                }
            ),
            # Component Graph để vẽ
            dcc.Graph(
                id='map-canvas',
                figure=fig,
                style={'height': '75vh'}, # Chiều cao của khu vực vẽ
                # Cấu hình thanh công cụ (modebar)
                config={
                    'scrollZoom': True,
                    # Thêm các nút để vẽ hình
                    'modeBarButtonsToAdd': [
                        'drawline',
                        'drawopenpath',
                        'drawclosedpath',
                        'drawcircle',
                        'drawrect',
                        'eraseshape'
                    ]
                }
            )
        ], width=9, style={'position': 'relative'}),

        # Cột bên phải chứa các tùy chọn
        dbc.Col([
            dbc.Select(
                options=[
                    {"label": "No object-type selected", "value": "1"},
                ],
                value="1",
            ),
            html.Div([
                dbc.Button("[]", color="light", className="me-1 mt-2"),
                dbc.Button("🔍", color="light", className="me-1 mt-2"),
                dbc.Button("📄", color="light", className="mt-2")
            ], className="d-flex justify-content-end")
        ], width=3)
    ])

], fluid=True, className="p-4")