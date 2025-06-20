import requests
import json
import os
from get_ip_address import load_ip_from_json

def enrich_and_save_map_data(ip='192.168.0.172',
                           map_guids_names_file="image/gui_and_name.json",
                           output_file="image/map_image.json"):
    """
    Loads map GUIDs and names from a JSON file, fetches detailed map data from an API for each GUID,
    and saves the enriched map data (including the name) to a JSON file.

    Args:
        ip (str, optional): The IP address of the API server. Defaults to '192.168.0.172'.
        map_guids_names_file (str, optional): Path to the JSON file containing map GUIDs and names.
            Defaults to "/home/
            /Downloads/mir_control_gui/App MIR100/static/image/gui_and_name.json".
        output_file (str, optional): Path to the JSON file where the enriched map data will be saved.
            Defaults to "/home/hieu/Downloads/mir_control_gui/App MIR100/static/image/map_image.json".
    """
    ip = load_ip_from_json("database_json/ip_address.json")
    host = 'http://' + ip + '/api/v2.0.0/'
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='}

    try:
        # Load GUIDs and names from the JSON file
        with open(map_guids_names_file, 'r') as f:
            map_guids_names = json.load(f)

        # Create a list to store the enriched map data
        enriched_maps_data = []

        # Iterate through the GUIDs and names, fetching map data for each
        for map_info in map_guids_names:
            guid = map_info.get('guid')
            map_name = map_info.get('name')  # Get the name associated with guid

            if guid:
                # GET /maps/{guid} : nhan thong tin map theo GUID
                map_url = host + 'maps/' + guid
                try: # Added try-except for request itself
                    b = requests.get(map_url, headers=headers)
                    b.raise_for_status() # Raise HTTPError for bad responses

                    if b.status_code == 200:
                        try:
                            map_data = json.loads(b.content)
                            map_data['name'] = map_name  # Add the name from the JSON into the object
                            # Append the map data (now with name) to enriched_maps_data
                            enriched_maps_data.append(map_data)
                            print(f"Successfully fetched and enriched map data for GUID: {guid}")

                        except json.JSONDecodeError as e:
                            print(f"Error decoding JSON for GUID {guid}: {e}")
                            print(f"Response content for GUID {guid}: {b.content}")

                    else:
                        print(f"Request failed for GUID {guid} with status code: {b.status_code}")
                        print(f"Response content for GUID {guid}: {b.content}")
                except requests.exceptions.RequestException as e:
                    print(f"RequestException for GUID {guid}: {e}") # Catch request errors

            else:
                print("Skipping map entry with missing 'guid'.")

        # Save the enriched map data to a JSON file
        with open(output_file, 'w') as f:
            json.dump(enriched_maps_data, f, indent=4)

        print(f"Enriched map data saved to {output_file}")
        return True  # Indicate Success

    except FileNotFoundError:
        print(f"Error: File '{map_guids_names_file}' not found.")
        return False # Indicate failure
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file: {map_guids_names_file}.  Please check file is valid JSON.")
        print(f"Error details: {e}")
        return False # Indicate failure
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print(f"Exception Details: {e}")
        return False # Indicate failure

# Example Usage
if __name__ == '__main__':
    if enrich_and_save_map_data():
        print("Map data enriched and saved successfully.")
    else:
        print("Failed to enrich and save map data.")
