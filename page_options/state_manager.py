import json
import os
import subprocess
import psutil
import logging

logger = logging.getLogger(__name__)

STATE_FILE = "simulation_state.json"
STATE_FILE_COPY = "database_json/simulation_state.json"

class StateManager:
    def __init__(self):
        self.initialize_state_file()
    
    def initialize_state_file(self):
        """Khởi tạo file simulation_state.json nếu chưa tồn tại"""
        if not os.path.exists(STATE_FILE):
            # Tạo thư mục database_json nếu chưa tồn tại
            os.makedirs(os.path.dirname(STATE_FILE_COPY) or '.', exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                json.dump({"mode": None, "simulation_running": False}, f)
            # Lưu bản sao
            with open(STATE_FILE_COPY, 'w') as f_copy:
                json.dump({"mode": None, "simulation_running": False}, f_copy)
    
    def save_simulation_state(self, mode="simulation", running=True):
        """Lưu trạng thái simulation vào file và bản sao"""
        try:
            state = {
                "mode": mode,
                "simulation_running": running
            }
            # Lưu vào file gốc
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f)
            logger.info(f"Saved state: {state}")
            # Lưu vào file bản sao
            os.makedirs(os.path.dirname(STATE_FILE_COPY) or '.', exist_ok=True)
            with open(STATE_FILE_COPY, 'w') as f_copy:
                json.dump(state, f_copy)
            logger.info(f"Saved copy state to {STATE_FILE_COPY}: {state}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def load_simulation_state(self):
        """Đọc trạng thái simulation từ file"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                return state
            return {"mode": None, "simulation_running": False}
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return {"mode": None, "simulation_running": False}
    
    def check_ros_processes_running(self):
        """Kiểm tra xem các process ROS simulation hoặc real model có đang chạy không"""
        ros_processes = [
            'gazebo',
            'gzserver', 
            'gzclient',
            'amcl',
            'move_base',
            'rviz',
            'mir_driver',  # Thêm process liên quan đến mir_driver
            'tf_monitor'   # Thêm process tf_monitor
        ]
        
        running_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                process_name = proc.info['name'].lower()
                cmdline = ' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ''
                
                for ros_proc in ros_processes:
                    if ros_proc in process_name or ros_proc in cmdline:
                        running_processes.append(ros_proc)
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        logger.debug(f"Found running ROS processes: {running_processes}")
        return len(running_processes) > 0
    
    def update_simulation_status(self):
        """Cập nhật trạng thái simulation dựa trên các process đang chạy"""
        current_state = self.load_simulation_state()
        ros_running = self.check_ros_processes_running()
        
        if current_state.get("simulation_running") and not ros_running:
            # Simulation đã tắt, cập nhật trạng thái
            logger.info("ROS processes stopped, updating state")
            self.save_simulation_state(mode=None, running=False)
            return False
        elif current_state.get("simulation_running") and ros_running:
            # Simulation vẫn đang chạy
            return True
        
        return ros_running
    
    def should_redirect_to_home(self):
        """Kiểm tra xem có nên redirect tới trang home không"""
        state = self.load_simulation_state()
        if state.get("simulation_running") and state.get("mode") in ["simulation", "real"]:
            if self.check_ros_processes_running():
                return True
            else:
                self.save_simulation_state(mode=None, running=False)
                return False
        return False
    
    def clear_state(self):
        """Xóa trạng thái - dùng khi tắt simulation"""
        self.save_simulation_state(mode=None, running=False)