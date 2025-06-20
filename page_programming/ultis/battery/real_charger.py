import requests, json, os, logging

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

class ChargeAtStation:
    def __init__(self, ip = load_ip_from_json("database_json/ip_address.json"), auth_token = 'YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA==', group_file="mission_groups.json"):
        self.host = f"http://{ip}/api/v2.0.0"
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {auth_token}'
        }
        self.group_file = group_file
        os.makedirs(os.path.dirname(group_file) or ".", exist_ok=True)

    def get_mission_groups(self):
        """Lấy danh sách mission groups từ API và lưu vào file JSON"""
        response = requests.get(f"{self.host}/mission_groups", headers=self.headers)
        if response.status_code == 200:
            groups = response.json()
            group_dict = {g["name"]: g["guid"] for g in groups}
            with open(self.group_file, "w") as f:
                json.dump(group_dict, f)
            return group_dict
        return {}

    def load_mission_groups(self):
        """Tải từ file hoặc gọi lại API nếu file lỗi"""
        if os.path.exists(self.group_file):
            try:
                with open(self.group_file, "r") as f:
                    data = f.read().strip()
                    if not data:
                        raise ValueError("File is empty")
                    return json.loads(data)
            except (json.JSONDecodeError, ValueError):
                print("⚠️ File JSON lỗi hoặc rỗng. Đang gọi lại API...")
                return self.get_mission_groups()
        return self.get_mission_groups()

    def get_mission_list(self, group_name):
        """Lấy danh sách mission từ group đã chọn"""
        groups = self.load_mission_groups()
        group_id = groups.get(group_name)
        if not group_id:
            return []
        url = f"{self.host}/mission_groups/{group_id}/missions"
        response = requests.get(url, headers=self.headers)
        return response.json() if response.status_code == 200 else []

    def add_mission_to_queue(self, mission_id):
        """Đưa mission vào hàng đợi"""
        url = f"{self.host}/mission_queue"
        response = requests.post(url, json={"mission_id": mission_id}, headers=self.headers)
        return "✅ Mission 'Charge' đã được thêm vào hàng đợi." if response.status_code == 201 else f"❌ Lỗi: {response.status_code}"

    def queue_charge_mission(self, group_name="Missions", mission_name="Charging"):
        """Tìm và thêm mission 'Charging' vào hàng đợi"""
        missions = self.get_mission_list(group_name)
        charge = next((m for m in missions if m.get("name") == mission_name), None)
        if not charge:
            return f"❌ Không tìm thấy mission '{mission_name}' trong group '{group_name}'."
        return self.add_mission_to_queue(charge.get("guid"))
    def set_robot_ready(self):
        """
        Đổi trạng thái robot sang 'Ready' bằng cách gửi PUT /status với state_id=3.
        """
        url = f"{self.host}/status"
        payload = {
            "state_id": 3  # 3 = Ready
        }

        try:
            response = requests.put(url, headers=self.headers, data=json.dumps(payload))
            if response.status_code == 200:
                print("✅ Robot đã chuyển sang trạng thái 'Ready'.")
            else:
                print(f"❌ Lỗi khi chuyển trạng thái: {response.status_code} - {response.text}")
            return response
        except requests.RequestException as e:
            print(f"❌ Lỗi kết nối tới robot: {e}")
            return None
        
        
if __name__ == "__main__":
    manager = ChargeAtStation()
    manager.set_robot_ready()
    print(manager.queue_charge_mission())  # Mặc định group "Missions" và mission "Charging"
