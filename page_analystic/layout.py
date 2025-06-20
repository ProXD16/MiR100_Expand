import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from datetime import date, datetime, timedelta
import plotly.graph_objs as go
from dash.dependencies import Input, Output
import requests
import json
from collections import defaultdict
import sys
import random
from get_ip_address import load_ip_from_json

class DistanceMonitorApp:
    def __init__(self, mir_ip=load_ip_from_json("database_json/ip_address.json")):
        # Kiểm tra chế độ mô phỏng
        self.is_simulation = 'simulation' in sys.argv
        self.mir_ip = None if self.is_simulation else mir_ip
        self.host = f"http://{mir_ip}/api/v2.0.0" if self.mir_ip else None
        self.headers = {
            "Authorization": "Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA==",
            "Content-Type": "application/json"
        }
        self.app = dash.Dash(__name__, external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
        ])
        self.date = []
        self.distance_date = []
        self.start_date = None
        self.end_date = None

        # Khởi tạo dữ liệu
        if self.is_simulation:
            print("🏭 Chạy ở chế độ mô phỏng, sử dụng dữ liệu giả lập")
            self.generate_simulation_data()
        else:
            self.fetch_and_save_distance()
        self.app.layout = self.setup_layout()
        self.register_callbacks()

    def generate_simulation_data(self, start_date=None, end_date=None):
        """Tạo dữ liệu giả lập cho chế độ mô phỏng"""
        if end_date is None:
            end_date = datetime.now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        self.date = [(start_date + timedelta(days=i)).isoformat() for i in range((end_date - start_date).days + 1)]
        # Tạo khoảng cách ngẫu nhiên từ 0.5 đến 5.0 km mỗi ngày
        self.distance_date = [round(random.uniform(0.5, 5.0), 2) for _ in self.date]

    def fetch_and_save_distance(self, start_date=None, end_date=None):
        if end_date is None:
            end_date = datetime.now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        try:
            response = requests.get(f"{self.host}/statistics/distance", headers=self.headers, timeout=5)
            response.raise_for_status()

            try:
                data = response.json()
                # Chuyển date từ string sang datetime
                for entry in data:
                    entry['date'] = datetime.fromisoformat(entry['date'])

                # Lọc theo khoảng thời gian start_date → end_date
                filtered_data = [
                    entry for entry in data
                    if start_date <= entry['date'].date() <= end_date
                ]

                # Tính tổng theo ngày
                distance_summary = self.distance_per_day(filtered_data)

                # Cập nhật thuộc tính class
                self.date = sorted(distance_summary.keys())
                self.distance_date = [distance_summary[day] for day in self.date]

            except json.JSONDecodeError:
                print("❌ Dữ liệu phản hồi không hợp lệ (không phải JSON)")
                self.generate_simulation_data(start_date, end_date)  # Dùng dữ liệu giả lập nếu JSON lỗi

        except (requests.ConnectionError, requests.RequestException) as e:
            print(f"🚫 Không kết nối được tới {self.host}: {e}")
            self.generate_simulation_data(start_date, end_date)  # Dùng dữ liệu giả lập

    def distance_per_day(self, data):
        distance_per_day = defaultdict(float)
        for entry in data:
            if isinstance(entry['date'], str):
                date_only = entry['date'][:10]
            else:
                date_only = entry['date'].date().isoformat()
            distance = entry.get('distance', 0)
            distance_per_day[date_only] += distance
        return dict(distance_per_day)

    def build_distance_figure(self):
        return {
            'data': [
                go.Bar(
                    name='Distance driven', 
                    x=self.date, 
                    y=self.distance_date, 
                    marker_color='rgba(0,255,0,0.3)',
                    marker_line=dict(color='rgba(0,200,0,0.8)', width=1),
                    hovertemplate='<b>Date:</b> %{x}<br><b>Distance:</b> %{y:.2f} km<extra></extra>'
                ),
                go.Scatter(
                    name='Accumulated distance', 
                    x=self.date, 
                    y=self.distance_date, 
                    mode='lines+markers',
                    line=dict(color='lightblue', width=3),
                    marker=dict(size=8, color='lightblue', line=dict(color='white', width=2)),
                    hovertemplate='<b>Date:</b> %{x}<br><b>Distance:</b> %{y:.2f} km<extra></extra>'
                )
            ],
            'layout': go.Layout(
                xaxis=dict(
                    title='Date',
                    title_font=dict(size=14, color='#2c3e50'),
                    tickfont=dict(size=11, color='#34495e'),
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True
                ),
                yaxis=dict(
                    title='Distance (km)',
                    title_font=dict(size=14, color='#2c3e50'),
                    tickfont=dict(size=11, color='#34495e'),
                    gridcolor='rgba(0,0,0,0.1)',
                    showgrid=True
                ),
                barmode='group',
                title=dict(
                    text="📈 Distance Driven per Day",
                    x=0.5,
                    font=dict(size=18, color='#2c3e50', family='Arial Black')
                ),
                plot_bgcolor='rgba(248,249,250,0.8)',
                paper_bgcolor='white',
                font=dict(family='Arial', color='#2c3e50'),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(t=80, b=60, l=60, r=60),
                hovermode='x unified'
            )
        }

    def setup_layout(self):
        custom_styles = {
            'header': {
                'background': 'linear-gradient(135deg, #77B5FE 0%, #4A90E2 100%)',
                'minHeight': '100%',
                'height': '100%',
                'padding': '2rem 1rem',
                'borderRadius': '0 20px 20px 0',
                'boxShadow': '0 10px 30px rgba(0,0,0,0.1)',
                'color': 'white',
                'overflowY': 'auto'
            },
            'date-card': {
                'background': 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
                'border-radius': '15px',
                'padding': '1.5rem',
                'box-shadow': '0 5px 15px rgba(0,0,0,0.1)',
                'border': '1px solid rgba(255,255,255,0.2)',
                'margin-bottom': '1rem'
            },
            'button-container': {
                'background': 'white',
                'border-radius': '15px',
                'padding': '1.5rem',
                'box-shadow': '0 5px 15px rgba(0,0,0,0.1)',
                'margin-bottom': '2rem'
            },
            'chart-container': {
                'background': 'white',
                'border-radius': '15px',
                'padding': '1rem',
                'box-shadow': '0 10px 30px rgba(0,0,0,0.1)',
                'border': '1px solid rgba(0,0,0,0.05)'
            }
        }

        return dbc.Container([
            html.Div([
                html.H1([
                    html.I(className="fas fa-chart-line me-3"),
                    "ANALYTICS DASHBOARD"
                ], className="mb-0", style={'font-weight': 'bold', 'letter-spacing': '2px'})
            ], style=custom_styles['header']),

            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="fas fa-calendar-alt me-2"),
                        "Date Range Selection"
                    ], className="mb-4 text-center text-primary"),
                    dbc.Row([
                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-play me-2"),
                                "Start Date"
                            ], className="fw-bold text-secondary mb-2"),
                            dcc.DatePickerSingle(
                                id='start-date',
                                date=date.today()-timedelta(days=30),
                                display_format='DD-MM-YYYY',
                                style={
                                    "width": "100%",
                                    "border-radius": "10px",
                                    "border": "2px solid #e9ecef",
                                    "font-size": "14px"
                                }
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-stop me-2"),
                                "End Date"
                            ], className="fw-bold text-secondary mb-2"),
                            dcc.DatePickerSingle(
                                id='end-date',
                                date=date.today(),
                                display_format='DD-MM-YYYY',
                                style={
                                    "width": "100%",
                                    "border-radius": "10px",
                                    "border": "2px solid #e9ecef",
                                    "font-size": "14px"
                                }
                            )
                        ], width=6),
                    ])
                ])
            ], style=custom_styles['date-card']),

            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="fas fa-clock me-2"),
                        "Quick Time Periods"
                    ], className="mb-4 text-center text-primary"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-calendar-week me-2"),
                                "Current Week"
                            ], id="btn-week-now", color="primary", outline=True, 
                            className="w-100 mb-2", size="sm")
                        ], width=4),
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-step-backward me-2"),
                                "Last Week"
                            ], id="btn-week-last", color="primary", outline=True, 
                            className="w-100 mb-2", size="sm")
                        ], width=4),
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-calendar-day me-2"),
                                "Latest 7 Days"
                            ], id="btn-7", color="success", outline=True, 
                            className="w-100 mb-2", size="sm")
                        ], width=4),
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-calendar me-2"),
                                "Current Month"
                            ], id="btn-month-now", color="info", outline=True, 
                            className="w-100 mb-2", size="sm")
                        ], width=4),
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-step-backward me-2"),
                                "Last Month"
                            ], id="btn-month-last", color="info", outline=True, 
                            className="w-100 mb-2", size="sm")
                        ], width=4),
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-calendar-day me-2"),
                                "Latest 30 Days"
                            ], id="btn-30", color="warning", outline=True, 
                            className="w-100 mb-2", size="sm")
                        ], width=4),
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-calendar-alt me-2"),
                                "Current Year"
                            ], id="btn-year-now", color="danger", outline=True, 
                            className="w-100 mb-2", size="sm")
                        ], width=4),
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-step-backward me-2"),
                                "Last Year"
                            ], id="btn-year-last", color="danger", outline=True, 
                            className="w-100 mb-2", size="sm")
                        ], width=4),
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-calendar-day me-2"),
                                "Latest 365 Days"
                            ], id="btn-365", color="secondary", outline=True, 
                            className="w-100 mb-2", size="sm")
                        ], width=4),
                    ])
                ])
            ], style=custom_styles['button-container']),

            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(
                        id='distance-chart',
                        figure=self.build_distance_figure(),
                        config={
                            'displayModeBar': True,
                            'displaylogo': False,
                            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                            'toImageButtonOptions': {
                                'format': 'png',
                                'filename': 'distance_chart',
                                'height': 600,
                                'width': 1200,
                                'scale': 1
                            }
                        }
                    )
                ])
            ], style=custom_styles['chart-container'])
        ], fluid=True, style={
            'background': 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
            'min-height': '100vh',
            'padding': '2rem 1rem'
        })

    def register_callbacks(self):
        @self.app.callback(
            Output('distance-chart', 'figure'),
            [
                Input('start-date', 'date'),
                Input('end-date', 'date'),
                Input('btn-week-now', 'n_clicks'),
                Input('btn-week-last', 'n_clicks'),
                Input('btn-7', 'n_clicks'),
                Input('btn-month-now', 'n_clicks'),
                Input('btn-month-last', 'n_clicks'),
                Input('btn-30', 'n_clicks'),
                Input('btn-year-now', 'n_clicks'),
                Input('btn-year-last', 'n_clicks'),
                Input('btn-365', 'n_clicks'),
            ]
        )
        def update_distance_chart(start_date, end_date, *btn_clicks):
            ctx = dash.callback_context
            if not ctx.triggered:
                start_date = datetime.now().date() - timedelta(days=30)
                end_date = datetime.now().date()
            else:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                today = datetime.now().date()
                
                if button_id == 'btn-week-now':
                    start_date = today - timedelta(days=today.weekday())
                    end_date = today
                elif button_id == 'btn-week-last':
                    end_date = today - timedelta(days=today.weekday() + 1)
                    start_date = end_date - timedelta(days=6)
                elif button_id == 'btn-7':
                    start_date = today - timedelta(days=7)
                    end_date = today
                elif button_id == 'btn-month-now':
                    start_date = today.replace(day=1)
                    end_date = today
                elif button_id == 'btn-month-last':
                    end_date = today.replace(day=1) - timedelta(days=1)
                    start_date = end_date.replace(day=1)
                elif button_id == 'btn-30':
                    start_date = today - timedelta(days=30)
                    end_date = today
                elif button_id == 'btn-year-now':
                    start_date = today.replace(month=1, day=1)
                    end_date = today
                elif button_id == 'btn-year-last':
                    end_date = today.replace(month=1, day=1) - timedelta(days=1)
                    start_date = end_date.replace(month=1, day=1)
                elif button_id == 'btn-365':
                    start_date = today - timedelta(days=365)
                    end_date = today
                else:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else today - timedelta(days=30)
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else today

            self.fetch_and_save_distance(start_date, end_date)
            return self.build_distance_figure()