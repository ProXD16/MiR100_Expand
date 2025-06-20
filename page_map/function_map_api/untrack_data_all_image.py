import json
import base64
from PIL import Image  # pip install pillow
import io
import requests
import os
from get_ip_address import load_ip_from_json

def process_and_display_maps(ip='192.168.0.172',
                             map_guids_names_file="image/gui_and_name.json"):
    """
    Fetches a list of maps from an API, saves GUIDs and names to a JSON file,
    then reads the JSON file and displays each map image.

    Args:
        ip (str, optional): The IP address of the API server. Defaults to '192.168.0.172'.
        map_guids_names_file (str, optional): Path to the JSON file for storing map GUIDs and names.
            Defaults to "/home/hieu/Downloads/mir_control_gui/App MIR100/static/image/gui_and_name.json".
    """
    ip = load_ip_from_json("database_json/ip_address.json")
    host = 'http://' + ip + '/api/v2.0.0/'
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='}

    try:
        # 1. Fetch GUIDs and names and save to JSON
        # GET /maps : nhan cac map
        b = requests.get(host + '/maps', headers=headers)
        b.raise_for_status()  # Check for HTTP errors

        all_maps_data = json.loads(b.content)
        print(b)
        print(all_maps_data)

        # Extract guid and name from each map and create a new list
        extracted_data = [{"guid": map_data.get("guid"), "name": map_data.get("name")} for map_data in all_maps_data]

        # Ensure the directory exists
        directory = os.path.dirname(map_guids_names_file)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                print(f"Directory '{directory}' created successfully.")
            except OSError as e:
                print(f"Error creating directory '{directory}': {e}")
                return  # Exit if directory creation fails

        # Save the extracted data to a JSON file
        with open(map_guids_names_file, 'w') as f:
            json.dump(extracted_data, f, indent=4)

        print(f"Extracted GUIDs and Names saved to {map_guids_names_file}")

    except requests.exceptions.RequestException as e:
        print(f"Request to get map guids/names failed: {e}")
        return # Exit
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON for map guids/names: {e}")
        return # Exit
    except Exception as e:
        print(f"An unexpected error occurred while getting map guids/names: {e}")
        return # Exit


    # 2. Load and Display Maps from the JSON file
    try:
        # Load the JSON data from the file
        with open(map_guids_names_file, 'r') as f:
            map_list = json.load(f)  # Assuming the JSON contains a list of maps

        # Check if the loaded data is a list
        if not isinstance(map_list, list):
            print("Error: JSON file does not contain a list of maps.")
            return

        # Iterate through the maps in the list and display each one
        for map_data in map_list:
            # Check if the map data is a dictionary and contains a 'guid' key
            if isinstance(map_data, dict) and 'guid' in map_data:
                guid = map_data['guid']
                map_name = map_data.get('name', "Unnamed Map")  # Get map name

                try:
                    # Call function to display map for the guid.  Can access from name.
                    display_single_map(guid, map_name, host, headers)  # Pass host and headers

                except Exception as e:
                    print(f"Error displaying map with GUID {guid}: {e}")
            else:
                print(
                    "Error: Invalid map data format.  Expected a list of maps, each map as dictionary containing at least a GUID.")

    except FileNotFoundError:
        print(f"Error: File '{map_guids_names_file}' not found.")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"Exception details: {e}")


def display_single_map(guid, map_name, host, headers): # Added Host and Headers
    """Displays map from server"""

    # Construct URL to fetch image. If URL pattern is different, adjust here
    image_url = f"{host}maps/{guid}"  # Correctly formatted url

    try:
        b = requests.get(image_url, headers=headers)
        b.raise_for_status()  # Check for HTTP errors

        map_data = json.loads(b.content)  # Decode the response which is assumed to be JSON
        if 'map' in map_data:
            image_data = base64.b64decode(map_data['map'])

            # Open the image using PIL
            image = Image.open(io.BytesIO(image_data))

            # Display the image (using the default image viewer)
            print(f"Showing map: {map_name}")  # Shows the name
            image.show()

        else:
            print("ERROR: No 'map' key in JSON for GUID:", guid)

    except requests.exceptions.RequestException as e:
        print(f"Request error for GUID {guid}: {e}")
    except json.JSONDecodeError as e:
        print(f"Request error for GUID {guid}: JSONDecodeError. Check image is JSON with base64 map.")
    except base64.binascii.Error as e: #Added Handle invalid characters
        print(f"Base64 decoding error for GUID {guid}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred when processing guid={guid}: {e}")


# Example usage:
if __name__ == '__main__':
    process_and_display_maps(ip='192.168.0.172',
                             map_guids_names_file="image/gui_and_name.json")
