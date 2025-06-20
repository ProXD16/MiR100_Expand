import json
import os

def save_lines_to_json(lines, filename="database_json/line_drawn.json"):
    filepath = os.path.join(os.getcwd(), filename) 
    print(f"Attempting to save lines to: {filepath}")
    
    try:
        with open(filepath, 'w') as f:
            json.dump(lines, f, indent=4)
        print(f"Successfully saved {len(lines)} lines to {filename}")
    except Exception as e:
        print(f"Error saving lines to {filename}: {e}")

def load_lines_from_json(filename="database_json/line_drawn.json"):
    filepath = os.path.join(os.getcwd(), filename)
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {filename}.  Returning an empty list.")
        return []
    except Exception as e:
        print(f"Error loading lines from {filename}: {e}.  Returning an empty list.")
        return []