import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

# Khởi tạo ứng dụng Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.config.suppress_callback_exceptions = True

# Dữ liệu mẫu cho danh sách maps
maps_data = [
    {"Name": "Maptest", "Created by": "Distributor", "Functions": "✓ 👁 ⚙"},
    {"Name": "New615", "Created by": "Administrator", "Functions": "✓ ✏ ❌"},
    {"Name": "Sanhc7", "Created by": "Administrator", "Functions": "✓ ✏ ❌"},
    {"Name": "Tang8", "Created by": "Distributor", "Functions": "✓ 👁 ⚙"},
    {"Name": "ghgh", "Created by": "Administrator", "Functions": "✓ ✏ ❌"},
    {"Name": "lab_813_new", "Created by": "Distributor", "Functions": "✓ 👁 ⚙"},
    {"Name": "map", "Created by": "Administrator", "Functions": "✓ ✏ ❌"},
    {"Name": "map1", "Created by": "Administrator", "Functions": "✓ ✏ ❌"},
    {"Name": "map_moi", "Created by": "Administrator", "Functions": "✓ ✏ ❌"},
    {"Name": "map_moi", "Created by": "Administrator", "Functions": "✓ ✏ ❌"},
]

df_maps = pd.DataFrame(maps_data)

# Layout chính
def main_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Maps", className="mb-1"),
                html.P("Create and edit maps", className="text-muted mb-4"),
            ], width=6),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("+ Create map", id="create-map-btn", color="success", className="me-2"),
                    dbc.Button("🏠 Import site", color="success", className="me-2"),
                    dbc.Button("🔍 Clear filters", color="light", outline=True)
                ], className="float-end")
            ], width=6)
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText("Filter:"),
                    dbc.Input(id="filter-input", placeholder="Write name to filter by...", value=""),
                    dbc.InputGroupText("28 item(s) found")
                ], className="mb-3")
            ], width=6),
            dbc.Col([
                html.Div([
                    html.Span("Page 2 of 3", className="me-2"),
                    dbc.ButtonGroup([
                        dbc.Button("<<", size="sm", color="primary"),
                        dbc.Button("<", size="sm", color="primary"),
                        dbc.Button(">", size="sm", color="primary"),
                        dbc.Button(">>", size="sm", color="primary"),
                    ])
                ], className="float-end")
            ], width=6)
        ]),
        
        dbc.Card([
            dbc.CardBody([
                # Header
                dbc.Row([
                    dbc.Col(html.H6("Name"), width=3),
                    dbc.Col(html.H6("Created by"), width=3),
                    dbc.Col(html.H6("Functions"), width=6),
                ], className="border-bottom pb-2 mb-3"),
                
                # Default site row
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className="bi bi-folder me-2"),
                            html.Strong("Default site")
                        ])
                    ], width=3),
                    dbc.Col("", width=3),
                    dbc.Col([
                        dbc.Badge("EXPORT", color="success")
                    ], width=6),
                ], className="mb-2"),
                
                # Maps list
                html.Div(id="maps-list")
            ])
        ])
    ], fluid=True, className="p-4")

# Layout trang mapping
def mapping_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4([
                    "123 ",
                    html.I(className="bi bi-star text-warning")
                ]),
                html.P("Edit and draw the map", className="text-muted")
            ], width=6),
            dbc.Col([
                dbc.Button("← Go back", id="go-back-btn", color="secondary", className="float-end")
            ], width=6)
        ], className="mb-3"),
        
        # Toolbar
        dbc.Card([
            dbc.CardBody([
                dbc.ButtonGroup([
                    dbc.Button("🔍", color="light", size="sm"),
                    dbc.Button("⋯", color="light", size="sm"),
                    dbc.Button("↶", color="light", size="sm"),
                    dbc.Button("💾", color="light", size="sm"),
                    dbc.Button("+", color="success", size="sm"),
                    dbc.Button("↖", color="light", size="sm"),
                ], className="me-3"),
                
                dbc.Select(
                    options=[{"label": "No object-type selected", "value": "none"}],
                    value="none",
                    style={"width": "200px", "display": "inline-block"},
                    className="me-3"
                ),
                
                dbc.ButtonGroup([
                    dbc.Button("🔧", color="light", size="sm"),
                    dbc.Button("🔍", color="light", size="sm"),
                    dbc.Button("🔍", color="light", size="sm"),
                ])
            ], className="py-2")
        ], className="mb-3"),
        
        # Main mapping area
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.P("Drag the map to move your view or use the zoom-in and -out buttons to zoom.", 
                           className="bg-dark text-white p-2 rounded position-absolute",
                           style={"top": "10px", "left": "10px", "z-index": "1000", "font-size": "12px"}),
                    
                    # Canvas area
                    html.Div([
                        # White drawing area
                        html.Div(
                            style={
                                "width": "600px",
                                "height": "400px",
                                "background-color": "white",
                                "border": "2px solid #000",
                                "margin": "50px auto",
                                "position": "relative"
                            }
                        )
                    ], style={
                        "background-color": "#e9ecef",
                        "height": "500px",
                        "position": "relative"
                    })
                ], style={"position": "relative"})
            ], className="p-0")
        ])
    ], fluid=True, className="p-4")

# Render maps list
def render_maps_list():
    maps_rows = []
    for _, row in df_maps.iterrows():
        maps_rows.append(
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="bi bi-folder me-2"),
                        html.Span(row['Name'])
                    ])
                ], width=3),
                dbc.Col(row['Created by'], width=3),
                dbc.Col([
                    html.Span(row['Functions'])
                ], width=6),
            ], className="mb-2 py-1")
        )
    return maps_rows

# Layout của ứng dụng
app.layout = html.Div([
    dcc.Store(id="current-page", data="main"),
    html.Div(id="page-content")
])

# Callback để chuyển trang
@app.callback(
    Output('page-content', 'children'),
    [Input('current-page', 'data')]
)
def display_page(current_page):
    if current_page == "mapping":
        return mapping_layout()
    else:
        return main_layout()

# Callback để render danh sách maps
@app.callback(
    Output('maps-list', 'children'),
    [Input('current-page', 'data')],
    prevent_initial_call=True
)
def update_maps_list(current_page):
    if current_page == "main":
        return render_maps_list()
    return []

# Callback để chuyển đến trang mapping khi nhấn Create map
@app.callback(
    Output('current-page', 'data', allow_duplicate=True),
    [Input('create-map-btn', 'n_clicks')],
    prevent_initial_call=True
)
def go_to_mapping(n_clicks):
    if n_clicks:
        return "mapping"
    return dash.no_update

# Callback để quay về trang chính khi nhấn Go back
@app.callback(
    Output('current-page', 'data', allow_duplicate=True),
    [Input('go-back-btn', 'n_clicks')],
    prevent_initial_call=True
)
def go_to_main(n_clicks):
    if n_clicks:
        return "main"
    return dash.no_update

if __name__ == '__main__':
    app.run(debug=True, port=8051)