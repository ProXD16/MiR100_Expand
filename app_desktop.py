import sys
from PySide2.QtWidgets import QApplication
from PySide2.QtWebEngineWidgets import QWebEngineView
from PySide2.QtCore import QUrl
from threading import Thread
import dash
from dash import html, dcc
import plotly.express as px
import pandas as pd

# Khởi tạo ứng dụng Dash
app = dash.Dash(__name__)

# Giao diện Dash (thay thế bằng code thực tế của bạn)
df = pd.DataFrame({
    "X": [1, 2, 3, 4],
    "Y": [10, 15, 13, 17]
})
fig = px.scatter(df, x="X", y="Y")

app.layout = html.Div([
    html.H1("Ứng dụng điều khiển MiR100"),
    dcc.Graph(figure=fig),
    # Thêm các thành phần điều khiển robot MiR100 (REST API, WebSocket, v.v.)
])

# Hàm chạy server Dash trong thread riêng
def run_dash():
    app.run(debug=False, port=8050)

# Khởi động server Dash
thread = Thread(target=run_dash)
thread.daemon = True
thread.start()

# Tạo ứng dụng PySide2
qt_app = QApplication(sys.argv)
web = QWebEngineView()
web.setWindowTitle("Ứng dụng điều khiển MiR100")
web.setGeometry(100, 100, 800, 600)  # Kích thước cửa sổ
web.load(QUrl("http://0.0.0.0:8050"))
web.show()

# Chạy ứng dụng
sys.exit(qt_app.exec_())