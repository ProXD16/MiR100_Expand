from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import dash_bootstrap_components as dbc

class MiR100Manual:
    def __init__(self):
        # Màu chủ đạo
        self.primary_color = '#77B5FE'
        self.secondary_color = '#5A9FE8'
        self.accent_color = '#4A8BD8'
        
        # Dữ liệu thông số kỹ thuật
        self.specifications_data = {
            'Kích thước': '890 x 580 x 352 mm',
            'Trọng lượng': '67 kg',
            'Tải trọng tối đa': '100 kg',
            'Tốc độ tối đa': '1.5 m/s',
            'Thời gian sạc': '2-3 giờ',
            'Thời gian hoạt động': 'Lên đến 9 giờ',
            'Loại pin': 'Lithium-ion',
            'Cảm biến': 'Laser scanner, Camera 3D, Ultrasonic'
        }

    def create_mir100_app(self):
        """Tạo layout cho trang Help"""
        return html.Div([
            # CSS tùy chỉnh
            html.Style(self._get_custom_css()),
            
            # Header với gradient đẹp
            html.Div([
                html.Div([
                    html.H1("🤖 MiR100 Robot", 
                            className="text-center text-white mb-2",
                            style={'fontSize': '3rem', 'fontWeight': 'bold', 'textShadow': '2px 2px 4px rgba(0,0,0,0.3)'}),
                    html.P("Hệ thống hướng dẫn & thông tin toàn diện", 
                           className="text-center text-white-50",
                           style={'fontSize': '1.2rem', 'fontWeight': '300'})
                ], className="container py-5")
            ], style={
                'background': f'linear-gradient(135deg, {self.primary_color} 0%, {self.secondary_color} 50%, {self.accent_color} 100%)',
                'minHeight': '200px',
                'display': 'flex',
                'alignItems': 'center'
            }),
            
            # Navigation tabs với style đẹp
            html.Div([
                dcc.Tabs(id="tabs", value='overview', 
                        children=[
                            dcc.Tab(label='🏠 Tổng quan', value='overview', className='custom-tab'),
                            dcc.Tab(label='⚙️ Thông số kỹ thuật', value='specs', className='custom-tab'),
                            dcc.Tab(label='📖 Hướng dẫn vận hành', value='operation', className='custom-tab'),
                            dcc.Tab(label='🛠️ Khắc phục sự cố', value='troubleshooting', className='custom-tab')
                        ], className="custom-tabs")
            ], className="container mt-4"),
            
            # Nội dung chính với background đẹp
            html.Div([
                html.Div(id='tab-content', className="container py-4")
            ], style={'backgroundColor': '#f8f9fa', 'minHeight': '80vh'})
        ])

    def _get_custom_css(self):
        """CSS tùy chỉnh cho giao diện đẹp"""
        return f"""
        .custom-tabs .tab {{
            background-color: white !important;
            border: 2px solid {self.primary_color} !important;
            border-radius: 10px 10px 0 0 !important;
            margin-right: 5px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }}
        
        .custom-tabs .tab:hover {{
            background-color: {self.primary_color} !important;
            color: white !important;
            transform: translateY(-2px) !important;
        }}
        
        .custom-tabs .tab--selected {{
            background-color: {self.primary_color} !important;
            color: white !important;
            border-bottom: 2px solid {self.primary_color} !important;
        }}
        
        .feature-card {{
            background: white;
            border-radius: 15px;
            padding: 2rem;
            margin: 1rem 0;
            box-shadow: 0 8px 25px rgba(119, 181, 254, 0.15);
            border: 1px solid rgba(119, 181, 254, 0.2);
            transition: all 0.3s ease;
        }}
        
        .feature-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(119, 181, 254, 0.25);
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, {self.primary_color}, {self.secondary_color});
            color: white;
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
            margin: 1rem;
            box-shadow: 0 10px 30px rgba(119, 181, 254, 0.3);
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 20px 40px rgba(119, 181, 254, 0.4);
        }}
        
        .instruction-step {{
            background: white;
            border-left: 5px solid {self.primary_color};
            border-radius: 0 10px 10px 0;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 4px 15px rgba(119, 181, 254, 0.1);
        }}
        
        .alert-custom {{
            border-radius: 15px;
            border: none;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        
        .robot-illustration {{
            background: linear-gradient(45deg, #f0f8ff, #e6f3ff);
            border-radius: 20px;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 10px 30px rgba(119, 181, 254, 0.2);
        }}
        """

    def register_callbacks(self, app):
        """Đăng ký callbacks cho ứng dụng chính"""
        @app.callback(
            Output('tab-content', 'children'),
            Input('tabs', 'value')
        )
        def render_content(tab):
            if tab == 'overview':
                return self._render_overview()
            elif tab == 'specs':
                return self._render_specs()
            elif tab == 'operation':
                return self._render_operation()
            elif tab == 'troubleshooting':
                return self._render_troubleshooting()

    def _render_overview(self):
        """Render trang tổng quan"""
        return html.Div([
            # Hero section
            html.Div([
                html.Div([
                    html.H2("🚀 Robot MiR100 - Giải pháp vận chuyển tự động thông minh", 
                            className="mb-4", style={'color': self.primary_color, 'fontWeight': 'bold'}),
                    html.P("MiR100 là robot di động tự động (AMR) thế hệ mới được thiết kế để vận chuyển hàng hóa một cách an toàn, hiệu quả và thông minh trong mọi môi trường công nghiệp và văn phòng hiện đại.", 
                           className="lead", style={'fontSize': '1.2rem', 'lineHeight': '1.8'}),
                ], className="col-md-7"),
                
                html.Div([
                    html.Div([
                        html.Div("🤖", style={'fontSize': '8rem', 'color': self.primary_color}),
                        html.H4("MiR100", className="mt-3", style={'color': self.secondary_color, 'fontWeight': 'bold'}),
                        html.P("Autonomous Mobile Robot", className="text-muted")
                    ], className="robot-illustration")
                ], className="col-md-5")
            ], className="row mb-5"),
            
            # Tính năng chính
            html.H3("✨ Tính năng vượt trội", className="mb-4", style={'color': self.primary_color, 'fontWeight': 'bold'}),
            html.Div([
                html.Div([
                    html.Div([
                        html.Div("🧠", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                        html.H5("AI Navigation", className="mb-3", style={'color': self.primary_color}),
                        html.P("Hệ thống điều hướng AI tiên tiến với khả năng học hỏi và tối ưu hóa đường đi tự động")
                    ], className="feature-card text-center")
                ], className="col-md-4"),
                
                html.Div([
                    html.Div([
                        html.Div("🔋", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                        html.H5("Pin Bền Bỉ", className="mb-3", style={'color': self.primary_color}),
                        html.P("Pin Lithium-ion cao cấp với thời gian hoạt động lên đến 9 giờ liên tục")
                    ], className="feature-card text-center")
                ], className="col-md-4"),
                
                html.Div([
                    html.Div([
                        html.Div("🛡️", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                        html.H5("An Toàn Tuyệt Đối", className="mb-3", style={'color': self.primary_color}),
                        html.P("Hệ thống cảm biến 360° với công nghệ tránh va chạm thông minh")
                    ], className="feature-card text-center")
                ], className="col-md-4")
            ], className="row"),
            
            html.Div([
                html.Div([
                    html.Div([
                        html.Div("📱", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                        html.H5("Giao Diện Thân Thiện", className="mb-3", style={'color': self.primary_color}),
                        html.P("Web interface trực quan, dễ sử dụng với khả năng điều khiển từ xa")
                    ], className="feature-card text-center")
                ], className="col-md-4"),
                
                html.Div([
                    html.Div([
                        html.Div("🔧", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                        html.H5("Bảo Trì Đơn Giản", className="mb-3", style={'color': self.primary_color}),
                        html.P("Thiết kế modular giúp bảo trì dễ dàng và giảm thiểu thời gian ngừng hoạt động")
                    ], className="feature-card text-center")
                ], className="col-md-4"),
                
                html.Div([
                    html.Div([
                        html.Div("📊", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                        html.H5("Báo Cáo Chi Tiết", className="mb-3", style={'color': self.primary_color}),
                        html.P("Hệ thống phân tích dữ liệu với báo cáo hiệu suất chi tiết theo thời gian thực")
                    ], className="feature-card text-center")
                ], className="col-md-4")
            ], className="row mb-5"),
            
            # Thông số nổi bật
            html.H3("📊 Thông số nổi bật", className="mb-4", style={'color': self.primary_color, 'fontWeight': 'bold'}),
            html.Div([
                html.Div([
                    html.Div([
                        html.H2("100kg", className="mb-2"),
                        html.H6("Tải trọng tối đa", className="mb-0")
                    ], className="stat-card")
                ], className="col-md-3"),
                
                html.Div([
                    html.Div([
                        html.H2("1.5m/s", className="mb-2"),
                        html.H6("Tốc độ tối đa", className="mb-0")
                    ], className="stat-card")
                ], className="col-md-3"),
                
                html.Div([
                    html.Div([
                        html.H2("9 giờ", className="mb-2"),
                        html.H6("Thời gian hoạt động", className="mb-0")
                    ], className="stat-card")
                ], className="col-md-3"),
                
                html.Div([
                    html.Div([
                        html.H2("360°", className="mb-2"),
                        html.H6("Cảm biến an toàn", className="mb-0")
                    ], className="stat-card")
                ], className="col-md-3")
            ], className="row")
        ])

    def _render_specs(self):
        """Render trang thông số kỹ thuật"""
        return html.Div([
            html.H2("⚙️ Thông số kỹ thuật chi tiết", className="mb-4", 
                   style={'color': self.primary_color, 'fontWeight': 'bold'}),
            
            html.Div([
                html.Div([
                    html.Div([
                        html.H4("📐 Thông số vật lý", className="mb-4", style={'color': self.secondary_color}),
                        html.Table([
                            html.Tbody([
                                html.Tr([
                                    html.Td(k, className="fw-bold", style={'color': self.primary_color, 'width': '40%'}), 
                                    html.Td(v, style={'fontSize': '1.1rem'})
                                ]) for k, v in self.specifications_data.items()
                            ])
                        ], className="table table-hover", style={'fontSize': '1.1rem'})
                    ], className="feature-card")
                ], className="col-md-6"),
                
                html.Div([
                    html.Div([
                        html.H4("📏 Sơ đồ kích thước", className="mb-4", style={'color': self.secondary_color}),
                        dcc.Graph(
                            figure=go.Figure().add_shape(
                                type="rect", x0=0, y0=0, x1=890, y1=580,
                                line=dict(color=self.primary_color, width=4),
                                fillcolor=f"rgba(119, 181, 254, 0.1)"
                            ).add_annotation(
                                x=445, y=290, text="MiR100<br>890mm x 580mm",
                                showarrow=False, font=dict(size=16, color=self.primary_color)
                            ).update_layout(
                                title=dict(text="Kích thước MiR100 (mm)", 
                                         font=dict(size=18, color=self.primary_color)),
                                xaxis_title="Chiều dài (890mm)",
                                yaxis_title="Chiều rộng (580mm)",
                                showlegend=False,
                                height=400,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                        )
                    ], className="feature-card")
                ], className="col-md-6")
            ], className="row"),
            
            # Thông tin bổ sung
            html.Div([
                html.Div([
                    html.H4("🔧 Thông số kỹ thuật nâng cao", className="mb-4", style={'color': self.secondary_color}),
                    html.Div([
                        html.Div([
                            html.H6("🌡️ Điều kiện hoạt động", style={'color': self.primary_color}),
                            html.P("• Nhiệt độ: -10°C đến +50°C\n• Độ ẩm: 10% - 95% (không ngưng tụ)\n• Độ dốc tối đa: 5°", 
                                  style={'whiteSpace': 'pre-line'})
                        ], className="col-md-6"),
                        
                        html.Div([
                            html.H6("📡 Kết nối & Giao tiếp", style={'color': self.primary_color}),
                            html.P("• WiFi 802.11 a/b/g/n\n• Ethernet 10/100 Mbps\n• REST API\n• Modbus TCP", 
                                  style={'whiteSpace': 'pre-line'})
                        ], className="col-md-6")
                    ], className="row")
                ], className="feature-card")
            ], className="row mt-4")
        ])

    def _render_operation(self):
        """Render trang hướng dẫn vận hành"""
        return html.Div([
            html.H2("📖 Hướng dẫn vận hành chi tiết", className="mb-4", 
                   style={'color': self.primary_color, 'fontWeight': 'bold'}),
            
            html.Div([
                html.Div([
                    html.Div([
                        html.H4("🚀 1. Khởi động hệ thống", style={'color': self.secondary_color}),
                        html.Ol([
                            html.Li("Nhấn nút nguồn màu xanh trên robot", style={'marginBottom': '10px'}),
                            html.Li("Chờ hệ thống khởi động hoàn tất (2-3 phút)", style={'marginBottom': '10px'}),
                            html.Li("Kiểm tra đèn LED trạng thái chuyển sang màu xanh", style={'marginBottom': '10px'}),
                            html.Li("Kết nối với giao diện web qua địa chỉ IP của robot", style={'marginBottom': '10px'})
                        ], style={'fontSize': '1.1rem'})
                    ], className="instruction-step")
                ], className="col-12"),
                
                html.Div([
                    html.Div([
                        html.H4("🗺️ 2. Tạo bản đồ khu vực", style={'color': self.secondary_color}),
                        html.Ol([
                            html.Li("Truy cập giao diện web và chọn tab 'Mapping'", style={'marginBottom': '10px'}),
                            html.Li("Nhấn 'Start Mapping' để bắt đầu quá trình tạo bản đồ", style={'marginBottom': '10px'}),
                            html.Li("Điều khiển robot di chuyển chậm quanh toàn bộ khu vực làm việc", style={'marginBottom': '10px'}),
                            html.Li("Đảm bảo robot quét hết tất cả các góc và khu vực quan trọng", style={'marginBottom': '10px'}),
                            html.Li("Hoàn thành và lưu bản đồ với tên phù hợp", style={'marginBottom': '10px'})
                        ], style={'fontSize': '1.1rem'})
                    ], className="instruction-step")
                ], className="col-12"),
                
                html.Div([
                    html.Div([
                        html.H4("🎯 3. Thiết lập Mission và Waypoints", style={'color': self.secondary_color}),
                        html.Ol([
                            html.Li("Mở tab 'Missions' trong giao diện quản lý", style={'marginBottom': '10px'}),
                            html.Li("Tạo mission mới và đặt tên mô tả rõ ràng", style={'marginBottom': '10px'}),
                            html.Li("Thêm các waypoints (điểm dừng) trên bản đồ đã tạo", style={'marginBottom': '10px'}),
                            html.Li("Cấu hình hành động cụ thể tại mỗi waypoint", style={'marginBottom': '10px'}),
                            html.Li("Thiết lập thứ tự di chuyển và thời gian dừng", style={'marginBottom': '10px'}),
                            html.Li("Thử nghiệm mission ở chế độ test trước khi triển khai", style={'marginBottom': '10px'})
                        ], style={'fontSize': '1.1rem'})
                    ], className="instruction-step")
                ], className="col-12"),
                
                html.Div([
                    html.Div([
                        html.H4("⚡ 4. Vận hành tự động", style={'color': self.secondary_color}),
                        html.Ol([
                            html.Li("Chọn mission cần thực hiện từ danh sách", style={'marginBottom': '10px'}),
                            html.Li("Kiểm tra trạng thái pin và đảm bảo đủ năng lượng", style={'marginBottom': '10px'}),
                            html.Li("Nhấn 'Start Mission' để robot bắt đầu hoạt động", style={'marginBottom': '10px'}),
                            html.Li("Theo dõi tiến trình thực hiện qua giao diện real-time", style={'marginBottom': '10px'}),
                            html.Li("Robot sẽ tự động thực hiện và báo cáo kết quả", style={'marginBottom': '10px'})
                        ], style={'fontSize': '1.1rem'})
                    ], className="instruction-step")
                ], className="col-12")
            ], className="row"),
            
            # Lưu ý an toàn
            html.Div([
                html.Div([
                    html.H4("⚠️ Lưu ý an toàn quan trọng", className="text-center mb-4", 
                           style={'color': '#dc3545', 'fontWeight': 'bold'}),
                    html.Div([
                        html.Div([
                            html.H6("🔍 Trước khi vận hành:", style={'color': self.primary_color}),
                            html.Ul([
                                html.Li("Kiểm tra và dọn sạch đường đi"),
                                html.Li("Đảm bảo không có vật cản di động"),
                                html.Li("Kiểm tra mức pin trên 20%")
                            ])
                        ], className="col-md-6"),
                        
                        html.Div([
                            html.H6("🛠️ Trong quá trình hoạt động:", style={'color': self.primary_color}),
                            html.Ul([
                                html.Li("Giám sát robot qua camera"),
                                html.Li("Sẵn sàng nhấn nút dừng khẩn cấp"),
                                html.Li("Không can thiệp khi robot đang di chuyển")
                            ])
                        ], className="col-md-6")
                    ], className="row")
                ], className="alert alert-warning alert-custom p-4")
            ], className="row mt-4")
        ])

    def _render_troubleshooting(self):
        """Render trang khắc phục sự cố"""
        return html.Div([
            html.H2("🛠️ Khắc phục sự cố thường gặp", className="mb-4", 
                   style={'color': self.primary_color, 'fontWeight': 'bold'}),
            
            html.Div([
                # Sự cố 1
                html.Div([
                    html.Div([
                        html.H5("🔋 Robot không khởi động được", className="mb-3", 
                               style={'color': '#dc3545', 'fontWeight': 'bold'}),
                        html.H6("🔍 Nguyên nhân có thể:", style={'color': self.primary_color}),
                        html.Ul([
                            html.Li("Pin hết hoặc sạc không đầy"),
                            html.Li("Lỗi kết nối cáp nguồn"),
                            html.Li("Hệ thống bị treo hoặc lỗi firmware")
                        ]),
                        html.H6("✅ Cách khắc phục:", style={'color': '#28a745'}),
                        html.Ol([
                            html.Li("Kiểm tra và sạc đầy pin (LED sạc chuyển xanh)"),
                            html.Li("Kiểm tra chắc chắn tất cả cáp kết nối"),
                            html.Li("Thực hiện hard reset: nhấn giữ nút reset 15 giây"),
                            html.Li("Nếu vẫn lỗi, liên hệ bộ phận kỹ thuật")
                        ])
                    ], className="feature-card border-start border-danger border-4")
                ], className="col-12 mb-4"),
                
                # Sự cố 2  
                html.Div([
                    html.Div([
                        html.H5("🗺️ Không thể tạo bản đồ hoặc bản đồ không chính xác", className="mb-3", 
                               style={'color': '#fd7e14', 'fontWeight': 'bold'}),
                        html.H6("🔍 Nguyên nhân có thể:", style={'color': self.primary_color}),
                        html.Ul([
                            html.Li("Cảm biến laser bị bẩn hoặc bị che"),
                            html.Li("Môi trường có quá nhiều bề mặt phản xạ (kính, gương)"),
                            html.Li("Di chuyển quá nhanh khi mapping"),
                            html.Li("Ánh sáng quá yếu hoặc quá mạnh")
                        ]),
                        html.H6("✅ Cách khắc phục:", style={'color': '#28a745'}),
                        html.Ol([
                            html.Li("Vệ sinh cảm biến laser bằng khăn mềm, sạch"),
                            html.Li("Tránh các khu vực có kính lớn, gương trong quá trình mapping"),
                            html.Li("Di chuyển chậm và đều (0.3-0.5 m/s) khi tạo bản đồ"),
                            html.Li("Đảm bảo ánh sáng ổn định, tránh ánh sáng chói"),
                            html.Li("Xóa bản đồ cũ và tạo lại từ đầu nếu cần")
                        ])
                    ], className="feature-card border-start border-warning border-4")
                ], className="col-12 mb-4"),
                
                # Sự cố 3
                html.Div([
                    html.Div([
                        html.H5("🚫 Robot dừng đột ngột hoặc không di chuyển", className="mb-3", 
                               style={'color': '#6f42c1', 'fontWeight': 'bold'}),
                        html.H6("🔍 Nguyên nhân có thể:", style={'color': self.primary_color}),
                        html.Ul([
                            html.Li("Phát hiện vật cản trên đường đi"),
                            html.Li("Cảm biến an toàn bị kích hoạt"),
                            html.Li("Lỗi định vị hoặc mất bản đồ"),
                            html.Li("Firmware cần được cập nhật")
                        ]),
                        html.H6("✅ Cách khắc phục:", style={'color': '#28a745'}),
                        html.Ol([
                            html.Li("Kiểm tra và dọn sạch đường đi, loại bỏ vật cản"),
                            html.Li("Vệ sinh tất cả cảm biến (ultrasonic, camera, laser)"),
                            html.Li("Thực hiện relocalization trên bản đồ"),
                            html.Li("Cập nhật firmware lên phiên bản mới nhất"),
                            html.Li("Khởi động lại robot và thử mission đơn giản")
                        ])
                    ], className="feature-card border-start border-info border-4")
                ], className="col-12 mb-4"),
                
                # Liên hệ hỗ trợ
                html.Div([
                    html.Div([
                        html.H4("📞 Hỗ trợ kỹ thuật 24/7", className="text-center mb-4", 
                               style={'color': '#28a745', 'fontWeight': 'bold'}),
                        html.P("Khi không thể tự khắc phục, đội ngũ chuyên gia của chúng tôi luôn sẵn sàng hỗ trợ bạn:", 
                               className="text-center mb-4", style={'fontSize': '1.1rem'}),
                        html.Div([
                            html.Div([
                                html.Div("📱", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                                html.H6("Hotline", style={'color': self.primary_color}),
                                html.H5("1900-1234", className="fw-bold")
                            ], className="text-center col-md-3"),
                            
                            html.Div([
                                html.Div("✉️", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                                html.H6("Email", style={'color': self.primary_color}),
                                html.H6("support@mir-vietnam.com", className="fw-bold")
                            ], className="text-center col-md-3"),
                            
                            html.Div([
                                html.Div("🕒", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                                html.H6("Thời gian", style={'color': self.primary_color}),
                                html.H6("24/7 - Tất cả các ngày", className="fw-bold")
                            ], className="text-center col-md-3"),
                            
                            html.Div([
                                html.Div("🌐", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                                html.H6("Website", style={'color': self.primary_color}),
                                html.H6("www.mir-vietnam.com", className="fw-bold")
                            ], className="text-center col-md-3")
                        ], className="row")
                    ], className="feature-card text-center", 
                       style={'background': f'linear-gradient(135deg, {self.primary_color}15, {self.secondary_color}15)'})
                ], className="col-12")
            ], className="row")
        ])