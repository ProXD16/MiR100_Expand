# app.py
import dash
import dash_bootstrap_components as dbc

# Khởi tạo ứng dụng Dash và kích hoạt tính năng đa trang
# Sử dụng theme BOOTSTRAP từ dash-bootstrap-components cho giao diện đẹp hơn
app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout chính của ứng dụng
# dash.page_container sẽ là nơi nội dung của các trang con (trong thư mục 'pages') được hiển thị
app.layout = dbc.Container([
    dash.page_container
], fluid=True)

# Dòng này để chạy server khi bạn thực thi file python
if __name__ == '__main__':
    app.run(debug=True, port=1607)