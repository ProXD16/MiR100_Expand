import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import random

# Khởi tạo ứng dụng Dash
app = dash.Dash(__name__)

# Dữ liệu bản đồ giả lập (có thể thay thế bằng dữ liệu từ MiR100)
map_data = {'x': [], 'y': []}

# Layout của ứng dụng
app.layout = html.Div([
    html.H1("Bản đồ cho Robot MiR100", style={'textAlign': 'center'}),
    dcc.Graph(id='map-graph', style={'height': '600px'}),
    html.Div([
        html.Button('Quét Bản đồ', id='scan-button', n_clicks=0),
        html.Button('Lưu Bản đồ', id='save-button', n_clicks=0),
        html.Button('Xóa Bản đồ', id='clear-button', n_clicks=0),
    ], style={'textAlign': 'center', 'margin': '20px'}),
    html.Div(id='output-message', style={'textAlign': 'center', 'marginTop': '20px'})
])

# Hàm tạo dữ liệu bản đồ giả lập
def generate_map_data():
    # Mô phỏng dữ liệu quét từ MiR100 (tọa độ x, y ngẫu nhiên)
    new_x = [random.uniform(0, 100) for _ in range(50)]
    new_y = [random.uniform(0, 100) for _ in range(50)]
    return new_x, new_y

# Callback để cập nhật bản đồ và xử lý các nút
@app.callback(
    [Output('map-graph', 'figure'),
     Output('output-message', 'children')],
    [Input('scan-button', 'n_clicks'),
     Input('save-button', 'n_clicks'),
     Input('clear-button', 'n_clicks')],
    [State('map-graph', 'figure')]
)
def update_map(scan_clicks, save_clicks, clear_clicks, current_figure):
    ctx = dash.callback_context
    message = ""

    if not ctx.triggered:
        trigger = None
    else:
        trigger = ctx.triggered[0]['prop_id'].split('.')[0]

    global map_data

    if trigger == 'scan-button':
        # Quét bản đồ mới
        map_data['x'], map_data['y'] = generate_map_data()
        message = "Đã quét bản đồ mới!"
    elif trigger == 'save-button':
        # Lưu bản đồ (mô phỏng, có thể thêm code để lưu vào file hoặc database)
        if map_data['x']:
            message = "Bản đồ đã được lưu!"
        else:
            message = "Không có dữ liệu để lưu."
    elif trigger == 'clear-button':
        # Xóa bản đồ
        map_data['x'] = []
        map_data['y'] = []
        message = "Bản đồ đã được xóa!"

    # Tạo figure cho Plotly
    figure = {
        'data': [
            go.Scatter(
                x=map_data['x'],
                y=map_data['y'],
                mode='markers',
                marker={'size': 5, 'color': 'blue'},
                name='Điểm bản đồ'
            )
        ],
        'layout': go.Layout(
            title='Bản đồ Robot MiR100',
            xaxis={'title': 'X (m)', 'range': [0, 100]},
            yaxis={'title': 'Y (m)', 'range': [0, 100]},
            showlegend=True
        )
    }

    return figure, message

# Chạy ứng dụng
if __name__ == '__main__':
    app.run(debug=True, port=1607)