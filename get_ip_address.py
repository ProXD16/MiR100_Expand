import os, json, logging

logger = logging.getLogger(__name__)

def load_ip_from_json(json_path="database_json/ip_address.json", default_ip="192.168.0.173"):
    try:
        if not os.path.exists(json_path):
            logger.warning(f"IP JSON file not found: {json_path}. Returning default IP: {default_ip}")
            return default_ip
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ip = data.get("ip_address")
        if not ip:
            logger.warning(f"No 'ip_address' key in {json_path}. Returning default IP: {default_ip}")
            return default_ip
        logger.info(f"Loaded IP address: {ip} from {json_path}")
        return ip
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {json_path}. Returning default IP: {default_ip}")
        return default_ip
    except Exception as e:
        logger.error(f"Error reading {json_path}: {e}. Returning default IP: {default_ip}")
        return default_ip
    
if __name__ == "__main__":
    ip = load_ip_from_json()
    print(f"IP Address: {ip}")