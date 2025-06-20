

from dash import dcc, html

button_style_ready = {
    'fontSize': '20px', 'width': '140px', 'height': '140px', 'borderRadius': '50%',
    'cursor': 'pointer', 'margin': '30px auto', 'display': 'block',
    'backgroundColor': '#4CAF50', 'color': 'white', 'border': 'none',
    'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)'
}
def setup_layout():
    page_layout= html.Div([
                    html.H1("Giao diện Điều khiển Robot bằng Giọng nói", style={'textAlign': 'center'}),
                    html.Button("Nói", id='speak-button', n_clicks=0, style=button_style_ready),
                    dcc.Loading(id="loading-indicator", type="circle", children=[
                        html.Div(id='status-output', children="Nhấn nút 'Nói' và ra lệnh...", style={
                            'marginTop': '20px', 'padding': '25px', 'border': '1px solid #ddd',
                            'borderRadius': '8px', 'minHeight': '200px', 'minWidth': '500px', 'textAlign': 'center',
                            'fontSize': '18px', 'backgroundColor': '#f9f9f9'
                        }),
                    ]),
                    html.Button(
                            'Run', # Đổi tên nút thành "Run" cho rõ ràng
                            id='run-voice',
                            n_clicks=0,
                            style={
                                'backgroundColor': '#007BFF', # Màu xanh dương
                                'color': 'white',
                                'padding': '12px 24px', # Tăng padding
                                'border': 'none',
                                'borderRadius': '5px',
                                'cursor': 'pointer',
                                'fontSize': '18px', # Tăng font size
                                'marginTop': '20px', # Giảm khoảng cách trên
                                'display': 'block', # Để căn giữa
                                'marginLeft': 'auto',
                                'marginRight': 'auto',
                                'width': '150px' # Đặt chiều rộng cố định
                            }
                        ),
                    # dcc.Interval(id='update-status-interval', interval=1000, n_intervals=0, disabled=False),
                    # dcc.Store(id='status-log-store', data=[]),
                    # html.Div(id='status-output')

                ], style={'fontFamily': 'Arial, sans-serif', 'maxWidth': '600px', 'margin': 'auto', 'padding': '20px'})
    return page_layout