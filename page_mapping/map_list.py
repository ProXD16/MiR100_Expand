# pages/map_list.py
import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import pandas as pd

# Đăng ký trang này với ứng dụng Dash
# path='/' nghĩa là đây là trang chủ
dash.register_page(__name__, path='/', title='Maps List')

# --- Dữ liệu mẫu cho bảng ---
# Trong một ứng dụng thực tế, dữ liệu này sẽ được lấy từ database
data = {
    'Name': ['Maptest', 'New615', 'Sanhc7', 'Tang8', 'ghgh', 'lab_813_new', 'map', 'map1', 'map_moi', 'map_moi'],
    'Created by': ['Distributor', 'Administrator', 'Administrator', 'Distributor', 'Administrator', 'Distributor', 'Administrator', 'Administrator', 'Administrator', 'Administrator']
}
df = pd.DataFrame(data)

# Thêm cột 'Functions' với các icon (dạng text) để mô phỏng
# Để các nút này thực sự hoạt động, cần sử dụng callback phức tạp hơn
df['Functions'] = '✓  🗙'

# --- Layout của trang ---
layout = dbc.Container([
    # Tiêu đề và các nút chức năng chính
    dbc.Row([
        dbc.Col([
            html.H1("Maps", className="mt-4"),
            html.P("Create and edit maps", className="text-muted")
        ], width=6),
        dbc.Col(
            dbc.ButtonGroup([
                # Nút 'Create map' sẽ điều hướng đến trang editor
                dcc.Link(
                    dbc.Button("+ Create map", color="success", className="me-2"),
                    href="/map-editor"
                ),
                dbc.Button("Import site", color="success", outline=True, className="me-2"),
                dbc.Button("Clear filters", color="light")
            ], className="mt-4 float-end"),
            width=6
        )
    ], className="mb-4"),

    # Thanh Filter và phân trang
    dbc.Row([
        dbc.Col(
            dbc.Input(placeholder="Write name to filter by..."),
            width=4
        ),
        dbc.Col(
            html.Span("26 items found", className="align-middle"),
            width="auto",
            className="d-flex align-items-center"
        ),
        dbc.Col(
            dbc.Pagination(max_value=3, active_page=2, className="justify-content-end"),
            width=True
        )
    ], className="mb-3 p-3 bg-light border rounded"),

    # Header của bảng và nút Export
    dbc.Row([
        dbc.Col(html.H6("Default site"), width="auto"),
        dbc.Col(dbc.Button("EXPORT", size="sm", color="secondary", outline=True), width="auto", className="ms-auto")
    ], className="p-2 border-bottom"),
    
    # Bảng dữ liệu
    dash_table.DataTable(
        id='table',
        columns=[
            {'name': 'Name', 'id': 'Name'},
            {'name': 'Created by', 'id': 'Created by'},
            # Căn chỉnh cột Functions sang phải
            {'name': 'Functions', 'id': 'Functions', 'type': 'text'},
        ],
        data=df.to_dict('records'),
        style_cell={'textAlign': 'left', 'padding': '10px'},
        style_header={
            'backgroundColor': 'white',
            'fontWeight': 'bold',
            'border-bottom': '1px solid black'
        },
        style_table={'border': '1px solid #dee2e6'},
        style_data_conditional=[{
            'if': {'column_id': 'Functions'},
            'textAlign': 'right'
        }],
        style_as_list_view=True, # Bỏ các đường kẻ dọc
    )
], fluid=True, className="p-4")