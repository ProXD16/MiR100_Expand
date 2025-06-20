import json
import base64
from PIL import Image  # pip install pillow
import io
import requests
import os
from get_ip_address import load_ip_from_json

def fetch_enrich_and_save_maps(ip='192.168.0.172',
                              map_guids_names_file="image/gui_and_name.json",
                              output_file="image/map_image.json",
                              image_output_dir="/home/duc/Downloads/App_MIR100/map_api_f/image/all_map_api"):
    """
    Loads map GUIDs and names from a JSON, fetches detailed map data for each,
    saves enriched map data (with name) to a JSON, and saves map images to a directory.

    Args:
        ip (str, optional): IP address of the API server. Defaults to '192.168.0.172'.
        map_guids_names_file (str, optional): Path to JSON containing map GUIDs/names.
            Defaults to "/home/hieu/Downloads/mir_control_gui/App MIR100/static/image/gui_and_name.json".
        output_file (str, optional): Path to JSON where enriched map data will be saved.
            Defaults to "/home/hieu/Downloads/mir_control_gui/App MIR100/static/image/map_image.json".
        image_output_dir (str, optional): Directory where map images will be saved.
            Defaults to "/home/hieu/Downloads/mir_control_gui/App MIR100/static/image/all_map_api".
    """
    ip = load_ip_from_json("database_json/ip_address.json")
    host = 'http://' + ip + '/api/v2.0.0/'
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='}

    try:
        # Load GUIDs and names from the JSON file
        with open(map_guids_names_file, 'r') as f:
            map_guids_names = json.load(f)

        # Create the image directory if it doesn't exist
        if not os.path.exists(image_output_dir):
            try:
                os.makedirs(image_output_dir)
                print(f"Directory '{image_output_dir}' created successfully.")
            except OSError as e:
                print(f"Error creating directory '{image_output_dir}': {e}")
                return False  # Indicate failure

        # Create a list to store the enriched map data
        enriched_maps_data = []

        # Iterate through the GUIDs and names, fetching map data for each
        for map_info in map_guids_names:
            guid = map_info.get('guid')
            map_name = map_info.get('name', 'unknown')  # Get the name; default 'unknown'

            if guid:
                # GET /maps/{guid} : nhan thong tin map theo GUID
                map_url = host + 'maps/' + guid
                try:  # Surround entire request sequence for robustness
                    b = requests.get(map_url, headers=headers)
                    b.raise_for_status()  # Raise HTTPError for bad responses

                    try:  # Try decoding response content to JSON
                        map_data = json.loads(b.content)
                        map_data['name'] = map_name  # Add the name from the JSON
                        enriched_maps_data.append(map_data)

                        # Save the image if map key and image data are present
                        if 'map' in map_data:
                            image_data = map_data['map']
                            try:  # Handle Base64 Decoding issues.
                                image_data_decoded = base64.b64decode(image_data)
                                image = Image.open(io.BytesIO(image_data_decoded))
                                image_path = os.path.join(image_output_dir, f"{map_name}.png")  # Filename with map name
                                image.save(image_path)
                                print(f"Successfully saved image '{map_name}' to '{image_path}'")

                            except base64.binascii.Error as e:
                                print(f"Base64 Decoding error for map {map_name}: {e}")
                            except Exception as e: # Handle any problem saving the image
                                print(f"Error saving image '{map_name}': {e}")

                        else:
                            print(f"No image found in JSON for map '{map_name}'.")

                        print(f"Successfully fetched and enriched map data for GUID: {guid}")

                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON for GUID {guid}: {e}")
                        print(f"Response content for GUID {guid}: {b.content}")

                except requests.exceptions.RequestException as e:
                    print(f"Request failed for GUID {guid}: {e}")  # Handle request errors

            else:
                print("Skipping map entry with missing 'guid'.")

        # Save the enriched map data to a JSON file
        with open(output_file, 'w') as f:
            json.dump(enriched_maps_data, f, indent=4)

        print(f"Enriched map data saved to {output_file}")
        return True  # Indicate success

    except FileNotFoundError:
        print(f"Error: File '{map_guids_names_file}' not found.")
        return False  # Indicate failure
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file: {map_guids_names_file}.  Please check file is valid JSON.")
        print(f"Error details: {e}")
        return False  # Indicate failure
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"Exception Details: {e}")
        return False  # Indicate failure

# Example Usage
if __name__ == '__main__':
    if fetch_enrich_and_save_maps():
        print("Maps fetched, enriched, saved to JSON, and images saved successfully.")
    else:
        print("Failed to fetch, enrich, save maps, and/or save images.")
