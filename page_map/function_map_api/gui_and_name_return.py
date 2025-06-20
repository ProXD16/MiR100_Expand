import requests
import json
import os

def fetch_and_save_map_data(ip='192.168.0.172', file_path="image/gui_and_name.json"):
    """
    Fetches map data from the specified IP, extracts GUID and Name, 
    and saves the extracted data to a JSON file.

    Args:
        ip (str, optional): The IP address of the API server. Defaults to '192.168.0.172'.
        file_path (str, optional): The path to the JSON file where the extracted data will be saved.
            Defaults to "/home/hieu/Downloads/mir_control_gui/App MIR100/static/image/gui_and_name.json".
    """

    host = 'http://' + ip + '/api/v2.0.0/'
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='}

    try:
        b = requests.get(host + '/maps', headers=headers)
        b.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        all_maps_data = json.loads(b.content)
        print(b)
        print(all_maps_data)

        # Extract guid and name from each map and create a new list
        extracted_data = [{"guid": map_data.get("guid"), "name": map_data.get("name")} for map_data in all_maps_data]

        # Ensure the directory exists
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                print(f"Directory '{directory}' created successfully.")
            except OSError as e:
                print(f"Error creating directory '{directory}': {e}")
                return False  # Indicate failure

        # Save the extracted data to a JSON file
        with open(file_path, 'w') as f:
            json.dump(extracted_data, f, indent=4)

        print(f"Extracted GUIDs and Names saved to {file_path}")
        return True # Indicate success

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False  # Indicate failure
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        if hasattr(b, 'content'):  # Check if 'b' has content attribute
            print(f"Response content: {b.content}")  # Print the raw content from the server for debugging
        return False  # Indicate failure
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"Exception details: {e}")  # Print the exception details
        return False  # Indicate failure

# Example usage
if __name__ == '__main__':
    if fetch_and_save_map_data():
        print("Map data fetched and saved successfully.")
    else:
        print("Failed to fetch and save map data.")
