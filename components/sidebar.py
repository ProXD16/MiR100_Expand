from dash import dcc, html
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify

class Sidebar:
    def create_sidebar(self):
        # Danh sách liên kết lấy từ ui_callbacks.py
        nav_links = [
            {"href": "/", "id": "index-link", "label": "Home", "icon": "mdi:home"},
            {"href": "/draw-mode", "id": "draw-mode-link", "label": "Draw Mode", "icon": "mdi:draw-pen"},
            {"href": "/rviz", "id": "rviz-link", "label": "RViz", "icon": "mdi:cube-outline"},
            {"href": "/missions", "id": "mission-link", "label": "Missions", "icon": "mdi:target"},
            {"href": "/map-api", "id": "map-api-link", "label": "Maps", "icon": "mdi:map"},
            {"href": "/path-guides", "id": "path-guides-link", "label": "Path Guides", "icon": "mdi:compass-outline"},
            {"href": "/programming", "id": "programming-link", "label": "Programming", "icon": "mdi:code-braces"},
            {"href": "/analystic", "id": "analystic-link", "label": "Analystic", "icon": "mdi:chart-line"},
            {"href": "#", "id": "user-groups-link", "label": "User Groups", "icon": "mdi:account-group"},
            {"href": "#", "id": "paths-link", "label": "Paths", "icon": "mdi:map-marker-path"},
            {"href": "#", "id": "marker-types-link", "label": "Marker Types", "icon": "mdi:map-marker"},
            {"href": "#", "id": "help-link", "label": "Helps", "icon": "mdi:help-circle"},
            {"href": "/change-password", "id": "change-password-link", "label": "Change Password", "icon": "mdi:lock-reset"},
        ]

        # Tạo các liên kết điều hướng
        nav_items = []
        # Thêm liên kết Home
        nav_items.append(
            dbc.NavLink(
                [
                    DashIconify(
                        icon=nav_links[0]["icon"],
                        width=20,
                        height=20,
                        style={"marginRight": "12px"}
                    ),
                    nav_links[0]["label"]
                ],
                href=nav_links[0]["href"],
                id=nav_links[0]["id"],
                className="nav-item-enhanced text-white",
                style=self._get_nav_style(),
                active="exact"
            )
        )

        # Thêm các liên kết chính (Draw Mode, RViz, Missions, Maps, Path Guides, Programming, Analystic)
        for link_info in nav_links[1:8]:
            nav_items.append(
                dbc.NavLink(
                    [
                        DashIconify(
                            icon=link_info["icon"],
                            width=20,
                            height=20,
                            style={"marginRight": "12px"}
                        ),
                        link_info["label"]
                    ],
                    href=link_info["href"],
                    id=link_info["id"],
                    className="nav-item-enhanced text-white",
                    style=self._get_nav_style(),
                    active="exact"
                )
            )

        # Thêm tiêu đề "USER MANAGEMENT"
        nav_items.append(
            html.Hr(
                style={
                    "border": "none",
                    "height": "1px",
                    "background": "rgba(255,255,255,0.2)",
                    "margin": "15px 0"
                }
            )
        )
        nav_items.append(
            html.Div(
                "USER MANAGEMENT",
                style={
                    "color": "rgba(255,255,255,0.6)",
                    "fontSize": "11px",
                    "fontWeight": "600",
                    "letterSpacing": "1px",
                    "padding": "10px 20px 5px 20px",
                    "textTransform": "uppercase"
                }
            )
        )

        # Thêm liên kết User Groups
        nav_items.append(
            dbc.NavLink(
                [
                    DashIconify(
                        icon=nav_links[8]["icon"],
                        width=20,
                        height=20,
                        style={"marginRight": "12px"}
                    ),
                    nav_links[8]["label"]
                ],
                href=nav_links[8]["href"],
                id=nav_links[8]["id"],
                className="nav-item-enhanced text-white",
                style=self._get_nav_style(),
                active="exact"
            )
        )

        # Thêm tiêu đề "NAVIGATION"
        nav_items.append(
            html.Hr(
                style={
                    "border": "none",
                    "height": "1px",
                    "background": "rgba(255,255,255,0.2)",
                    "margin": "15px 0"
                }
            )
        )
        nav_items.append(
            html.Div(
                "NAVIGATION",
                style={
                    "color": "rgba(255,255,255,0.6)",
                    "fontSize": "11px",
                    "fontWeight": "600",
                    "letterSpacing": "1px",
                    "padding": "10px 20px 5px 20px",
                    "textTransform": "uppercase"
                }
            )
        )

        # Thêm các liên kết Paths, Marker Types, Footprints
        for link_info in nav_links[9:12]:
            nav_items.append(
                dbc.NavLink(
                    [
                        DashIconify(
                            icon=link_info["icon"],
                            width=20,
                            height=20,
                            style={"marginRight": "12px"}
                        ),
                        link_info["label"]
                    ],
                    href=link_info["href"],
                    id=link_info["id"],
                    className="nav-item-enhanced text-white",
                    style=self._get_nav_style(),
                    active="exact"
                )
            )

        return html.Div(
            [
                # Logo/Title section
                html.Div(
                    [
                        dcc.Link(
                            html.Div(
                                [
                                    DashIconify(
                                        icon="mdi:robot-industrial",
                                        width=40,
                                        height=40,
                                        style={"color": "white", "marginBottom": "10px"}
                                    ),
                                    html.H2(
                                        "GUI MiR100",
                                        className="text-white text-center",
                                        style={
                                            "color": "#FFFFFF",
                                            "fontWeight": "bold",
                                            "fontSize": "24px",
                                            "margin": "0",
                                            "textShadow": "0 2px 4px rgba(0,0,0,0.3)"
                                        }
                                    ),
                                    html.Div(
                                        "Robot Management System",
                                        style={
                                            "color": "rgba(255,255,255,0.8)",
                                            "fontSize": "12px",
                                            "fontStyle": "italic",
                                            "marginTop": "5px",
                                            "textAlign": "center"
                                        }
                                    )
                                ],
                                style={"textAlign": "center"}
                            ),
                            href="/",
                            style={"textDecoration": "none"}
                        )
                    ],
                    style={
                        "padding": "20px 10px",
                        "borderBottom": "2px solid rgba(255,255,255,0.2)",
                        "marginBottom": "20px"
                    }
                ),

                # Navigation menu
                dbc.Nav(
                    nav_items,
                    vertical=True,
                    pills=True,
                    id="sidebar-nav",
                    style={"padding": "0 10px"}
                ),

                # Bottom section with Change Password
                html.Div(
                    dbc.NavLink(
                        [
                            DashIconify(
                                icon=nav_links[-1]["icon"],
                                width=20,
                                height=20,
                                style={"marginRight": "12px"}
                            ),
                            nav_links[-1]["label"]
                        ],
                        href=nav_links[-1]["href"],
                        id=nav_links[-1]["id"],
                        className="nav-item-enhanced text-white",
                        style={
                            **self._get_nav_style(),
                            "backgroundColor": "rgba(255,255,255,0.1)",
                            "border": "1px solid rgba(255,255,255,0.2)"
                        },
                        active="exact"
                    ),
                    style={
                        "position": "absolute",
                        "bottom": "20px",
                        "left": "10px",
                        "right": "10px"
                    }
                )
            ],
            style={
                "background": "linear-gradient(180deg, #77B5FE 0%, #6ba3fc 100%)",
                "padding": "0",
                "width": "250px",
                "height": "100vh",
                "color": "white",
                "position": "fixed",
                "boxShadow": "4px 0 15px rgba(0,0,0,0.1)",
                "overflow": "hidden"
            }
        )

    def _get_nav_style(self, active=False):
        """Get navigation item styling, with special handling for active state"""
        base_style = {
            "color": "white",
            "padding": "12px 20px",
            "margin": "2px 0",
            "borderRadius": "10px",
            "transition": "all 0.3s ease",
            "display": "flex",
            "alignItems": "center",
            "fontSize": "14px",
            "fontWeight": "500",
            "textDecoration": "none",
            "border": "1px solid transparent",
            "backgroundColor": "transparent"
        }
        if active:
            base_style.update({
                "border": "2px solid white",
                "backgroundColor": "rgba(255,255,255,0.15)",
                "color": "white",
                "fontWeight": "600",
                "boxShadow": "0 0 12px rgba(255,255,255,0.6)"
            })
        return base_style