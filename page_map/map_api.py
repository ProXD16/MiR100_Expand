# map_api.py
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import requests
import json
from PIL import Image
import io
import os
import base64
import logging
from dash import callback_context
from dash.exceptions import PreventUpdate
from shutil import copy2  # Import copy2 for copying images
from get_ip_address import load_ip_from_json


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class MapAPI:
    def __init__(self, ip=load_ip_from_json("database_json/ip_address.json")):  # Added IP as an argument with default value
        self.ip = ip
        self.host = 'http://' + self.ip + '/api/v2.0.0/'
        self.headers = {}
        self.headers['Content-Type'] = 'application/json'
        self.headers['Authorization'] = 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='
        self.all_maps_data = self.fetch_maps()  # Store all data
        self.filter_text = ""  # Added filter text
        self.image_output_dir = "page_map/image/all_map_api"
        self.change_path_image = "" # Define destination path

    def fetch_maps(self):
        """Fetches the maps data from the API."""
        try:
            b = requests.get(self.host + '/maps', headers=self.headers)
            b.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            maps_data = json.loads(b.content)
            return maps_data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching maps data: {e}")
            return []

    def create_map_api(self):
        """Creates the layout for the Map section, resembling the provided image, with scrolling only on the table."""
        filtered_maps_data = self.get_filtered_maps()
        num_items = len(filtered_maps_data)

        # Top section (header, filter, buttons)
        top_section = html.Div(
            [
                
                dbc.Row(
                    [
                        dbc.Col(
                            html.H3("Maps", className="mb-0", style={"color": "#2C3E50"}),
                            width="auto",
                        ),
                        dbc.Col(
                            html.P("Create and edit maps.", style={"color": "#777", "fontSize": "0.8em", "marginBottom": "0px"}),
                            width="auto",
                        ),
                        dbc.Col(
                            html.Span("?", style={"border": "1px solid #777", "borderRadius": "50%", "padding": "0px 5px", "fontSize": "0.8em", "color": "#777", "marginLeft": "5px", "cursor": "pointer"}),
                            width="auto",
                        ),
                    ],
                    align="center",
                    className="mb-2",
                ),
                
                dbc.Row(
                    [
                        dbc.Col(
                            html.Button(
                                [html.I(className="fas fa-plus me-1"), "Create map"],
                                id="create-map-button",
                                className="btn btn-success btn-sm",
                            ),
                            width="auto",
                        ),
                        dbc.Col(
                            html.Button(
                                [html.I(className="fas fa-upload me-1"), "Import site"],
                                id="import-site-button",
                                className="btn btn-secondary btn-sm",
                            ),
                            width="auto",
                        ),
                        dbc.Col(
                            html.Button(
                                [html.I(className="fas fa-plus me-1"), html.Span("Change map", id="change-map-button-text")],
                                id="change-map-button",
                                className="btn btn-success btn-sm", style={'display': 'none'}
                            ),
                            width="auto",
                        ),

                    ],
                    className="mb-3",
                ),
            ],
            style={"marginBottom": "10px"},  # Add some spacing below the top section
        )

        # Scrollable Table section
        scrollable_table = html.Div(
            [
                dbc.Table(
                    [
                        html.Thead(
                            html.Tr(
                                [
                                    html.Th("Name"),
                                    html.Th("Created by"),
                                    html.Th("Functions"),
                                ]
                            )
                        ),
                        html.Tbody(
                            # Use the maps data to create the table rows
                            [self.create_map_row(map_data.get("name", "N/A"), "Administrator", index=i, map_id=map_data.get("id")) for i, map_data in enumerate(filtered_maps_data)]
                        )
                    ],
                    bordered=False,
                    striped=False,
                    hover=True,
                    style={"fontSize": "0.9em"},
                    className="table-responsive",  # Make the table responsive
                )
            ],
            style={
                "overflowY": "auto",  # Enable vertical scrolling
                "maxHeight": "400px",  # Limit the height of the table. Adjust as needed.
            },
        )
        modal = dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Map Details")),
                dbc.ModalBody(id="modal-body-content"),
                
            ],
            id="map-modal",
            is_open=False,
        )
        

        export_modal = dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Do you want to export this map?")),
                dbc.ModalBody(id="modal-export-body-content", children=[
                html.Div(id="yes-export-button", style={'display': 'none'})  # PLaceholder
            ]),
               
            ],
            id="export-modal",
            is_open=False,
        )
        delete_modal = dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Do you want to delete this map?")),
                dbc.ModalBody(id="modal-delete-body-content"),
                
            ],
            id="delete-modal",
            is_open=False,
        )

        # Combine the top section and scrollable table
        map_section_layout = html.Div(
            id="map-api-container",
            children=[top_section, scrollable_table, modal, export_modal,delete_modal, dcc.Store(id='selected-map-index')],  # Add the modal and dcc.Store
            style={
                "padding": "30px",
                "flex": "1",
                "background": "white",
                "marginLeft": "20px",
                "marginTop": "50px",
                "borderRadius": "5px",
                "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
            },
        )
        return map_section_layout
    

    def create_map_row(self, name, created_by, index, is_active=False, is_export=False, map_id=None):
        """Creates a table row for a map entry."""
        functions = []
        functions.append(
                html.Button(
                    html.I(className="fas fa-check"),
                    className="btn btn-success btn-sm",
                    style={"marginLeft": "5px"},  # Add spacing between buttons
                    id={"type": "export-map-button", "index": int(index)},  # Unique ID
                    n_clicks=0,
                )
            )
        functions.append(
            html.Button(
                html.I(className="fas fa-eye"),
                className="btn btn-primary btn-sm",
                style={"marginLeft": "5px"},  # Add spacing between buttons
                id={"type": "view-map-button", "index": int(index)},  # Unique ID
                n_clicks=0,
            )
        )
        functions.append(
            html.Button(
                html.I(className="fas fa-times"),
                className="btn btn-danger btn-sm",
                style={"marginLeft": "5px"} , # Add spacing between buttons
                id={"type": "delete-map-button", "index": int(index)},  # Unique ID
                n_clicks=0,
            )
        )

        return html.Tr(
            [
                html.Td(
                    [
                        html.I(className="fas fa-map-marker-alt me-1"),
                        name,
                        html.Span(" ACTIVE", className="badge bg-success ms-1") if is_active else "",
                    ]
                ),
                html.Td(created_by),
                html.Td(functions),
            ]
        )

    def get_filtered_maps(self):
        """Filters the maps based on the filter text."""
        if not self.filter_text:
            return self.all_maps_data
        else:
            filtered_maps = [
                map_data for map_data in self.all_maps_data
                if self.filter_text.lower() in map_data.get("name", "").lower()
            ]
            return filtered_maps

    def copy_image(self, source_path, destination_path):
        """Copies the image from source path to destination path."""
        try:
            copy2(source_path, destination_path)
            print(f"Image copied successfully from {source_path} to {destination_path}")
        except FileNotFoundError:
            print(f"Error: Source image not found at {source_path}")
        except Exception as e:
            print(f"Error copying image: {e}")

    def register_callbacks(self, app):
        @app.callback(
            [Output("map-modal", "is_open"),
             Output("export-modal", "is_open"),
             Output("delete-modal", "is_open")],
            [Input({"type": "view-map-button", "index": dash.ALL}, "n_clicks"),
             Input({"type": "export-map-button", "index": dash.ALL}, "n_clicks"),
             Input({"type": "delete-map-button", "index": dash.ALL}, "n_clicks"),
             ],
            [State("map-modal", "is_open"),
             State("export-modal", "is_open"),
             State("delete-modal", "is_open")],
            prevent_initial_call=True
        )
        def toggle_modal(view_clicks, export_clicks,delete_clicks, is_map_open, is_export_open,is_delete_open):
            ctx = dash.callback_context
            if not ctx.triggered:
                return is_map_open, is_export_open,is_delete_open
            else:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

                if "view-map-button" in trigger_id:
                    return not is_map_open, False, False  # Open map modal
                elif "export-map-button" in trigger_id:
                    return False, not is_export_open ,False # Open export modal
                elif "delete-map-button" in trigger_id:
                    return False,  False, not is_delete_open # Open delete modal
               
                else:
                    return is_map_open, is_export_open,is_delete_open
        
        @app.callback(
            [Output("modal-body-content", "children"),
            Output("modal-export-body-content", "children"),
            Output("modal-delete-body-content", "children")],
            [Input({"type": "view-map-button", "index": dash.ALL}, "n_clicks"),
            Input({"type": "export-map-button", "index": dash.ALL}, "n_clicks"),
            Input({"type": "delete-map-button", "index": dash.ALL}, "n_clicks")],
            [State({"type": "view-map-button", "index": dash.ALL}, "id"),
            State({"type": "export-map-button", "index": dash.ALL}, "id"),
            State({"type": "delete-map-button", "index": dash.ALL}, "id")]
        )
        def update_modal_content(view_clicks, export_clicks, delete_clicks, view_button_id, export_button_id, delete_button_id):
            ctx = dash.callback_context

            if not ctx.triggered:
                logging.debug("update_modal_content: No trigger (initial load).")
                return "", "", ""  # Return empty content for all modals if no trigger

            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            logging.debug(f"update_modal_content: Trigger ID: {trigger_id}")

            # Handle View Map Button Click
            if "view-map-button" in trigger_id:
                clicked_index = None
                try:
                    for i, id_dict in enumerate(view_button_id):
                        if trigger_id.startswith(f'{{"index":{id_dict["index"]},"type":"view-map-button"}}'):
                            clicked_index = i
                            break  # Found the button that triggered the callback

                    if clicked_index is None:
                        logging.warning("update_modal_content: Could not find clicked index based on trigger ID (view).")
                        return "Error: Could not identify clicked button.", "", ""

                    button_id_of_clicked_button = view_button_id[clicked_index]
                    map_index = button_id_of_clicked_button['index']

                    try:
                        map_list = self.get_filtered_maps()
                        map_data = map_list[int(map_index)]
                        map_name = map_data['name']

                        self.image_output_dir = os.path.normpath(self.image_output_dir)
                        image_path = os.path.join(self.image_output_dir, f"{map_name}.png")
                        self.change_path_image = image_path

                        if os.path.exists(image_path):
                            with open(image_path, 'rb') as image_file:
                                encoded_image = base64.b64encode(image_file.read()).decode('ascii')
                            image_component = html.Img(src=f'data:image/png;base64,{encoded_image}',
                                                        style={'width': '100%', 'height': 'auto'})
                            return image_component, "", ""  # Return content for view modal, empty for export and delete
                        else:
                            return f"Image not found for map {map_name} in folder : {self.image_output_dir}. Please regenerate map and try again.", "", ""

                    except IndexError:
                        return f"Error: Map index {map_index} is out of range.", "", ""
                    except Exception as e:
                        return f"An unexpected error occurred: {e}", "", ""

                except Exception as e:
                    logging.error(f"update_modal_content: An unexpected error occurred (view): {e}")
                    return f"An unexpected error occurred: {e}", "", ""

            # Handle Export Map Button Click
            elif "export-map-button" in trigger_id:
                clicked_index = None
                try:
                    for i, id_dict in enumerate(export_button_id):
                        if trigger_id.startswith(f'{{"index":{id_dict["index"]},"type":"export-map-button"}}'):
                            clicked_index = i
                            break  # Found the button that triggered the callback

                    if clicked_index is None:
                        logging.warning("update_modal_content: Could not find clicked index based on trigger ID (export).")
                        return "", "Error: Could not identify clicked button.", ""

                    # Get the map index from the button ID
                    button_id_of_clicked_button = export_button_id[clicked_index]
                    map_index = button_id_of_clicked_button['index']
                    try:
                        map_list = self.get_filtered_maps()
                        map_data = map_list[int(map_index)]
                        map_name = map_data['name']

                        self.image_output_dir = os.path.normpath(self.image_output_dir)
                        image_path = os.path.join(self.image_output_dir, f"{map_name}.png")
                        self.change_path_image = image_path
                    except IndexError:
                        return f"Error: Map index {map_index} is out of range.", "", ""

                    export_buttons = html.Div(  # Return content for export modal, empty for view and delete
                        style={
                            'display': 'flex',
                            'justifyContent': 'space-between'
                        },
                        children=[
                            html.Button(
                                'Active',
                                id='yes-export-button',
                                n_clicks=0,
                                style={
                                    'backgroundColor': 'green',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'border': 'none',
                                    'borderRadius': '5px',
                                    'cursor': 'pointer',
                                    'fontSize': '16px',
                                    'marginLeft': '40px'
                                }
                            ),
                            html.Button(
                                'Cancel',
                                id='no-export-button',
                                n_clicks=0,
                                style={
                                    'backgroundColor': 'red',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'border': 'none',
                                    'borderRadius': '5px',
                                    'cursor': 'pointer',
                                    'fontSize': '16px',
                                    'marginRight': '40px'
                                }
                            ),
                        ]
                    )
                    return "", export_buttons, ""

                except Exception as e:
                    logging.error(f"update_modal_content: An unexpected error occurred (export): {e}")
                    return "", f"An unexpected error occurred: {e}", ""

            # Handle Delete Map Button Click
            elif "delete-map-button" in trigger_id:
                clicked_index = None
                try:
                    for i, id_dict in enumerate(delete_button_id):
                        if trigger_id.startswith(f'{{"index":{id_dict["index"]},"type":"delete-map-button"}}'):
                            clicked_index = i
                            break  # Found the button that triggered the callback

                    if clicked_index is None:
                        logging.warning("update_modal_content: Could not find clicked index based on trigger ID (delete).")
                        return "", "", "Error: Could not identify clicked button."

                    # Get the map index from the button ID
                    button_id_of_clicked_button = delete_button_id[clicked_index]
                    map_index = button_id_of_clicked_button['index']

                    delete_buttons = html.Div(  # Return content for delete modal, empty for view and export
                        style={
                            'display': 'flex',
                            'justifyContent': 'space-between'
                        },
                        children=[
                            html.Button(
                                'Yes',
                                id='yes-delete-button',
                                n_clicks=0,
                                style={
                                    'backgroundColor': 'green',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'border': 'none',
                                    'borderRadius': '5px',
                                    'cursor': 'pointer',
                                    'fontSize': '16px',
                                    'marginLeft': '40px'
                                }
                            ),
                            html.Button(
                                'No',
                                id='no-delete-button',
                                n_clicks=0,
                                style={
                                    'backgroundColor': 'blue',
                                    'color': 'white',
                                    'padding': '10px 20px',
                                    'border': 'none',
                                    'borderRadius': '5px',
                                    'cursor': 'pointer',
                                    'fontSize': '16px',
                                    'marginRight': '40px'
                                }
                            ),
                        ]
                    )
                    return "", "", delete_buttons

                except Exception as e:
                    logging.error(f"update_modal_content: An unexpected error occurred (delete): {e}")
                    return "", "", f"An unexpected error occurred: {e}"

            else:
                return "", "", ""  # No trigger, return empty content
        @app.callback(
            Output("change-map-button-text", "children"),
            [Input("yes-export-button", "n_clicks")],
            [State("change-map-button-text", "children")]
        )
        def on_active_export_click(n_clicks, is_export_open):
            """Copies the image, replaces the source image, and closes the export modal."""
            if n_clicks is None or n_clicks == 0:
                return is_export_open  # Do not close if button hasn't been clicked

            source_image_path = "static/map_image.png"
            destination_image_path = self.change_path_image  # Get destination path from class

            try:
                # Check if the destination image exists.  If not, there's nothing to copy.
                if not os.path.exists(destination_image_path):
                    print(f"Error: Destination image not found at {destination_image_path}.  Aborting image overwrite.")
                    return is_export_open  # Keep modal open

                # Replace the source image with the destination image.  This is the requested direct overwrite.
                copy2(destination_image_path, source_image_path) # Overwrite the source image with the destination image.
                print(f"Successfully overwrote {source_image_path} with {destination_image_path}")

                return False  # Close modal

            except FileNotFoundError:
                print(f"Error:  Image not found at {destination_image_path}.") # Only check for destination since source now always exists
                return is_export_open  # Giữ nguyên trạng thái modal
            except OSError as e:
                print(f"Lỗi OSError: {e}")
                return is_export_open  # Giữ nguyên trạng thái modal
            except Exception as e:
                print(f"Lỗi không mong muốn: {e}")
                return is_export_open  # Giữ nguyên trạng thái modal
            
        @app.callback(
            Output("export-modal", "is_open", allow_duplicate=True),
            Input("yes-export-button", "n_clicks"),
            State("export-modal", "is_open"),
            prevent_initial_call = True
        )
        def toggle_export_modal(n_clicks, is_open):
            return not is_open
        
        @app.callback(
            Output("export-modal", "is_open", allow_duplicate=True),
            Input("no-export-button", "n_clicks"),
            State("export-modal", "is_open"),
            prevent_initial_call = True
        )
        def toggle_export_modal(n_clicks, is_open):
            return not is_open

# Example Usage (within your Dash app):
if __name__ == '__main__':
    
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])
    map_api = MapAPI()  # You can also pass the IP address here

    app.layout = html.Div(id='app-container', children=map_api.create_map_api())
    map_api.register_callbacks(app)
    app.run(debug=True, port=8051)
