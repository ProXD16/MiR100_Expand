import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# Class to encapsulate the layout
class PathGuideLayout:
    def __init__(self):
        self.layout = self.create_layout()

    def create_layout(self):
        # Enhanced button styles
        button_style = {
            'padding': '12px 24px',
            'fontSize': '14px',
            'fontWeight': '600',
            'borderRadius': '8px',
            'border': 'none',
            'transition': 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            'boxShadow': '0 4px 12px rgba(119, 181, 254, 0.3)',
            'backgroundColor': '#77B5FE',  # Giữ nguyên màu xanh
            'color': 'white',
            'cursor': 'pointer',
            'position': 'relative',
            'overflow': 'hidden',
            'textTransform': 'uppercase',
            'letterSpacing': '0.5px',
        }
        
        # Enhanced modal styles
        modal_style = {
            'borderRadius': '16px',
            'border': 'none',
            'boxShadow': '0 20px 60px rgba(0, 0, 0, 0.15)',
        }
        
        modal_header_style = {
            'borderBottom': '1px solid #e9ecef',
            'padding': '24px 32px 16px',
            'backgroundColor': '#f8f9fa',
            'borderRadius': '16px 16px 0 0',
        }
        
        modal_body_style = {
            'padding': '24px 32px',
            'backgroundColor': 'white',
        }
        
        modal_footer_style = {
            'borderTop': '1px solid #e9ecef',
            'padding': '16px 32px 24px',
            'backgroundColor': '#f8f9fa',
            'borderRadius': '0 0 16px 16px',
        }
        
        # Enhanced dropdown style
        dropdown_style = {
            'marginBottom': '24px',
            'borderRadius': '8px',
            'border': '2px solid #e9ecef',
            'transition': 'border-color 0.3s ease',
        }
        
        # Column card style
        column_card_style = {
            'backgroundColor': 'white',
            'borderRadius': '16px',
            'padding': '28px',
            'boxShadow': '0 8px 32px rgba(0, 0, 0, 0.08)',
            'border': '1px solid #f0f0f0',
            'transition': 'transform 0.3s ease, box-shadow 0.3s ease',
            'height': 'fit-content',
            'minHeight': '400px',
        }
        
        return html.Div([
            # Store để lưu trữ dữ liệu (giữ nguyên)
            dcc.Store(id='start-positions-store', data=[]),
            dcc.Store(id='waypoints-store', data=[]),
            dcc.Store(id='goal-positions-store', data=[]),
            
            # Enhanced Modal cho Add Start Position
            dbc.Modal([
                dbc.ModalHeader([
                    html.Div([
                        html.I(className="fas fa-map-marker-alt", 
                               style={'color': '#77B5FE', 'marginRight': '12px', 'fontSize': '20px'}),
                        dbc.ModalTitle("Add Start Position", 
                                     style={'fontSize': '20px', 'fontWeight': '600', 'color': '#2c3e50'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style=modal_header_style),
                dbc.ModalBody([
                    html.Div([
                        html.Label("Select position:", 
                                 style={'fontWeight': '600', 'marginBottom': '12px', 'color': '#34495e', 'fontSize': '16px'}),
                        html.P("Choose a starting position for your path guide", 
                               style={'color': '#7f8c8d', 'fontSize': '14px', 'marginBottom': '16px'}),
                        dcc.Dropdown(
                            id='start-position-dropdown',
                            options=[],
                            placeholder="Select a position...",
                            style=dropdown_style
                        )
                    ])
                ], style=modal_body_style),
                dbc.ModalFooter([
                    dbc.Button("Submit", id="start-submit-btn", color="info", className="me-3", 
                              style={**button_style, **{'background': 'linear-gradient(135deg, #77B5FE 0%, #5a9efc 100%)'}}),
                    dbc.Button("Cancel", id="start-cancel-btn", color="secondary", 
                              style={**button_style, **{
                                  'backgroundColor': '#95a5a6', 
                                  'boxShadow': '0 4px 12px rgba(149, 165, 166, 0.3)'
                              }})
                ], style=modal_footer_style)
            ], id="start-modal", is_open=False, style=modal_style, size="lg"),
            
            # Enhanced Modal cho Add Waypoint
            dbc.Modal([
                dbc.ModalHeader([
                    html.Div([
                        html.I(className="fas fa-route", 
                               style={'color': '#77B5FE', 'marginRight': '12px', 'fontSize': '20px'}),
                        dbc.ModalTitle("Add Waypoint", 
                                     style={'fontSize': '20px', 'fontWeight': '600', 'color': '#2c3e50'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style=modal_header_style),
                dbc.ModalBody([
                    html.Div([
                        html.Label("Select position:", 
                                 style={'fontWeight': '600', 'marginBottom': '12px', 'color': '#34495e', 'fontSize': '16px'}),
                        html.P("Add an intermediate point along your path", 
                               style={'color': '#7f8c8d', 'fontSize': '14px', 'marginBottom': '16px'}),
                        dcc.Dropdown(
                            id='waypoint-position-dropdown',
                            options=[],
                            placeholder="Select a waypoint...",
                            style=dropdown_style
                        )
                    ])
                ], style=modal_body_style),
                dbc.ModalFooter([
                    dbc.Button("Submit", id="waypoint-submit-btn", color="info", className="me-3", 
                              style={**button_style, **{'background': 'linear-gradient(135deg, #77B5FE 0%, #5a9efc 100%)'}}),
                    dbc.Button("Cancel", id="waypoint-cancel-btn", color="secondary", 
                              style={**button_style, **{
                                  'backgroundColor': '#95a5a6', 
                                  'boxShadow': '0 4px 12px rgba(149, 165, 166, 0.3)'
                              }})
                ], style=modal_footer_style)
            ], id="waypoint-modal", is_open=False, style=modal_style, size="lg"),
            
            # Enhanced Modal cho Add Goal Position
            dbc.Modal([
                dbc.ModalHeader([
                    html.Div([
                        html.I(className="fas fa-flag-checkered", 
                               style={'color': '#77B5FE', 'marginRight': '12px', 'fontSize': '20px'}),
                        dbc.ModalTitle("Add Goal Position", 
                                     style={'fontSize': '20px', 'fontWeight': '600', 'color': '#2c3e50'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ], style=modal_header_style),
                dbc.ModalBody([
                    html.Div([
                        html.Label("Select position:", 
                                 style={'fontWeight': '600', 'marginBottom': '12px', 'color': '#34495e', 'fontSize': '16px'}),
                        html.P("Choose the final destination for your path", 
                               style={'color': '#7f8c8d', 'fontSize': '14px', 'marginBottom': '16px'}),
                        dcc.Dropdown(
                            id='goal-position-dropdown',
                            options=[],
                            placeholder="Select a goal position...",
                            style=dropdown_style
                        )
                    ])
                ], style=modal_body_style),
                dbc.ModalFooter([
                    dbc.Button("Submit", id="goal-submit-btn", color="info", className="me-3", 
                              style={**button_style, **{'background': 'linear-gradient(135deg, #77B5FE 0%, #5a9efc 100%)'}}),
                    dbc.Button("Cancel", id="goal-cancel-btn", color="secondary", 
                              style={**button_style, **{
                                  'backgroundColor': '#95a5a6', 
                                  'boxShadow': '0 4px 12px rgba(149, 165, 166, 0.3)'
                              }})
                ], style=modal_footer_style)
            ], id="goal-path-modal", is_open=False, style=modal_style, size="lg"),
            
            # Enhanced Main content
            html.Div([
                # Enhanced Header
                html.Div([
                    html.Div([
                        html.H1("Path Guide Manager", 
                               style={
                                   'marginBottom': '8px', 
                                   'fontSize': '32px', 
                                   'fontWeight': '700',
                                   'background': 'linear-gradient(135deg, #2c3e50 0%, #3498db 100%)',
                                   'backgroundClip': 'text',
                                   'WebkitBackgroundClip': 'text',
                                   'WebkitTextFillColor': 'transparent',
                                   'textAlign': 'center'
                               }),
                        html.P("Configure and manage your navigation path with precision", 
                               style={
                                   'color': '#7f8c8d', 
                                   'marginBottom': '40px', 
                                   'fontSize': '16px',
                                   'textAlign': 'center',
                                   'fontWeight': '400'
                               })
                    ])
                ], style={'marginBottom': '40px'}),
                
                # Enhanced Three columns with cards
                html.Div([
                    # Enhanced Start positions column
                    html.Div([
                        html.Div([
                            html.Div([
                                html.I(className="fas fa-play-circle", 
                                       style={'color': '#27ae60', 'fontSize': '24px', 'marginRight': '12px'}),
                                html.H3("Start Positions", 
                                       style={
                                           'marginBottom': '8px', 
                                           'fontSize': '22px', 
                                           'fontWeight': '700',
                                           'color': '#2c3e50'
                                       })
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
                            html.P("Define where your journey begins", 
                                   style={'color': '#7f8c8d', 'fontSize': '14px', 'marginBottom': '24px'}),
                            dbc.Button([
                                html.I(className="fas fa-plus", style={'marginRight': '8px'}),
                                "Add Start"
                            ], id="add-start-btn", color="info", size="sm", className="mb-4", 
                                       style={**button_style, **{'width': '100%', 'justifyContent': 'center'}}),
                            html.Div(id="start-positions-list", style={'minHeight': '200px'})
                        ], style=column_card_style)
                    ], style={'flex': '1', 'marginRight': '20px'}),
                    
                    # Enhanced Waypoints column
                    html.Div([
                        html.Div([
                            html.Div([
                                html.I(className="fas fa-map-signs", 
                                       style={'color': '#f39c12', 'fontSize': '24px', 'marginRight': '12px'}),
                                html.H3("Waypoints", 
                                       style={
                                           'marginBottom': '8px', 
                                           'fontSize': '22px', 
                                           'fontWeight': '700',
                                           'color': '#2c3e50'
                                       })
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
                            html.P("Set intermediate checkpoints", 
                                   style={'color': '#7f8c8d', 'fontSize': '14px', 'marginBottom': '24px'}),
                            dbc.Button([
                                html.I(className="fas fa-plus", style={'marginRight': '8px'}),
                                "Add Waypoint"
                            ], id="add-waypoint-btn", color="info", size="sm", className="mb-4", 
                                       style={**button_style, **{'width': '100%', 'justifyContent': 'center'}}),
                            html.Div(id="waypoints-list", style={'minHeight': '200px'})
                        ], style=column_card_style)
                    ], style={'flex': '1', 'marginRight': '20px'}),
                    
                    # Enhanced Goal positions column
                    html.Div([
                        html.Div([
                            html.Div([
                                html.I(className="fas fa-flag-checkered", 
                                       style={'color': '#e74c3c', 'fontSize': '24px', 'marginRight': '12px'}),
                                html.H3("Goal Positions", 
                                       style={
                                           'marginBottom': '8px', 
                                           'fontSize': '22px', 
                                           'fontWeight': '700',
                                           'color': '#2c3e50'
                                       })
                            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
                            html.P("Mark your final destination", 
                                   style={'color': '#7f8c8d', 'fontSize': '14px', 'marginBottom': '24px'}),
                            dbc.Button([
                                html.I(className="fas fa-plus", style={'marginRight': '8px'}),
                                "Add Goal"
                            ], id="add-goal-btn", color="info", size="sm", className="mb-4", 
                                       style={**button_style, **{'width': '100%', 'justifyContent': 'center'}}),
                            html.Div(id="goal-positions-list", style={'minHeight': '200px'})
                        ], style=column_card_style)
                    ], style={'flex': '1'}),
                ], style={
                    'display': 'flex', 
                    'gap': '0px',
                    'alignItems': 'stretch'
                })
                
            ], style={
                'padding': '40px',
                'backgroundColor': 'white',
                'borderRadius': '20px',
                'boxShadow': '0 20px 60px rgba(0, 0, 0, 0.08)',
                'margin': '20px auto',
                'maxWidth': '1400px',
                'position': 'relative',
                'border': '1px solid #f0f0f0'
            })
        ], style={
            'backgroundColor': '#f5f5f5',  # Giữ nguyên màu nền
            'minHeight': '100vh', 
            'padding': '20px',
            'background': 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        })