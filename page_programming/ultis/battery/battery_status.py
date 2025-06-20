#!/usr/bin/env python
"""
BatteryChecker module to retrieve battery level for MIR100 robot in simulation or real mode.
In real mode, fetches battery level via HTTP API.
In simulation mode, simulates battery level decreasing by 1% every 30 seconds, reading initial level from JSON.
"""

import json
import os
import time
import requests
import rospy
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

class BatteryChecker:
    """
    Manages battery level checking for MIR100 robot in simulation or real mode.
    """
    def __init__(self, simulation_state_path="database_json/simulation_state.json",
                 battery_file_path="database_json/battery_percent.json"):
        """
        Initialize BatteryChecker.

        Args:
            simulation_state_path (str): Path to simulation state JSON file.
            battery_file_path (str): Path to battery percentage JSON file.
        """
        self.simulation_state_path = simulation_state_path
        self.battery_file_path = battery_file_path
        self.battery_level = self._load_simulated_battery()
        self.last_update_time = None
        self.mode = self._load_mode()
        self.ip = load_ip_from_json("database_json/ip_address.json")
        self.api_url = 'http://' + self.ip + '/api/v2.0.0/status'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic YWRtaW46OGM2OTc2ZTViNTQxMDQxNWJkZTkwOGJkNGRlZTE1ZGZiMTY3YTljODczZmM0YmI4YTgxZjZmMmFiNDQ4YTkxOA=='
        }
        rospy.loginfo(f"BatteryChecker initialized in {'simulation' if self.mode == 'simulation' else 'real'} mode with initial battery level {self.battery_level}%.")

    def _load_mode(self):
        """
        Load mode from simulation_state.json.
        Returns 'simulation' or 'real', defaulting to 'simulation' on error.
        """
        try:
            if not os.path.exists(self.simulation_state_path):
                rospy.logwarn(f"Simulation state file not found: {self.simulation_state_path}. Defaulting to simulation mode.")
                return "simulation"
            with open(self.simulation_state_path, 'r') as f:
                state = json.load(f)
            mode = state.get("mode", "simulation")
            if mode not in ["simulation", "real"]:
                rospy.logwarn(f"Invalid mode '{mode}' in {self.simulation_state_path}. Defaulting to simulation.")
                return "simulation"
            rospy.loginfo(f"Loaded mode: {mode} from {self.simulation_state_path}")
            return mode
        except json.JSONDecodeError:
            rospy.logerr(f"Invalid JSON in {self.simulation_state_path}. Defaulting to simulation mode.")
            return "simulation"
        except Exception as e:
            rospy.logerr(f"Error reading {self.simulation_state_path}: {e}. Defaulting to simulation mode.")
            return "simulation"

    def _load_simulated_battery(self):
        """
        Load simulated battery level from JSON file.
        Returns battery level as float, defaulting to 100.0 on error or if file doesn't exist.
        """
        try:
            if os.path.exists(self.battery_file_path):
                with open(self.battery_file_path, 'r') as f:
                    data = json.load(f)
                battery_level = data.get("battery_percentage", 100.0)
                if isinstance(battery_level, (int, float)):
                    return float(battery_level)
                else:
                    rospy.logwarn(f"Invalid battery_percentage in {self.battery_file_path}: {battery_level}. Defaulting to 100.0.")
                    return 100.0
            else:
                rospy.logwarn(f"Battery file not found: {self.battery_file_path}. Defaulting to 100.0.")
                return 100.0
        except json.JSONDecodeError:
            rospy.logerr(f"Invalid JSON in {self.battery_file_path}. Defaulting to 100.0.")
            return 100.0
        except Exception as e:
            rospy.logerr(f"Error reading {self.battery_file_path}: {e}. Defaulting to 100.0.")
            return 100.0

    def _save_simulated_battery(self):
        """
        Save current simulated battery level to JSON file.
        """
        try:
            os.makedirs(os.path.dirname(self.battery_file_path), exist_ok=True)
            with open(self.battery_file_path, 'w') as f:
                json.dump({"battery_percentage": self.battery_level}, f, indent=2)
            rospy.loginfo(f"Saved simulated battery level {self.battery_level}% to {self.battery_file_path}")
        except Exception as e:
            rospy.logerr(f"Failed to save simulated battery level to {self.battery_file_path}: {e}")

    def _get_battery_level_via_ip(self):
        """
        Retrieve battery level from robot API in real mode.
        Returns battery level as float or None on failure.
        """
        try:
            response = requests.get(self.api_url, headers=self.headers, timeout=2)
            response.raise_for_status()
            data = response.json()
            battery_level = data.get("battery_percentage")
            if isinstance(battery_level, (int, float)):
                return float(battery_level)
            else:
                rospy.logerr(f"Invalid battery_percentage in API response: {battery_level}")
                return None
        except requests.exceptions.RequestException as e:
            rospy.logerr(f"Failed to fetch battery level from {self.api_url}: {e}")
            return None
        except ValueError as e:
            rospy.logerr(f"Failed to parse JSON response from {self.api_url}: {e}")
            return None
        except Exception as e:
            rospy.logerr(f"Unexpected error fetching battery level from {self.api_url}: {e}")
            return None

    def check_battery(self):
        """
        Check current battery level based on mode.
        In simulation mode, decreases battery by 1% every 30 seconds and saves to JSON.
        In real mode, fetches battery level via API.
        Returns battery level as float or None on failure.
        """
        if self.mode == "real":
            battery_level = self._get_battery_level_via_ip()
            if battery_level is not None:
                rospy.loginfo(f"Real mode: Battery level retrieved: {battery_level}%")
            return battery_level
        else:  # Simulation mode
            current_time = time.time()
            if self.last_update_time is None:
                self.last_update_time = current_time
                rospy.loginfo(f"Simulation mode: Initial battery level loaded: {self.battery_level}%")
            elif (current_time - self.last_update_time) >= 30.0:
                self.battery_level = max(0.0, self.battery_level - 1.0)
                self.last_update_time = current_time
                self._save_simulated_battery()
                rospy.loginfo(f"Simulation mode: Battery level decreased to {self.battery_level}%")
            return self.battery_level

    def update_battery_level(self, new_level):
        """
        Update the simulated battery level and save to JSON if in simulation mode.
        """
        if self.mode == "simulation":
            self.battery_level = max(0.0, min(new_level, 100.0))
            self._save_simulated_battery()
            rospy.loginfo(f"Simulation mode: Battery level updated to {self.battery_level}%")
        else:
            rospy.logwarn("Cannot update battery level in real mode.")

def main():
    """
    Main function for standalone testing of BatteryChecker.
    """
    rospy.init_node('battery_checker_test', anonymous=True)
    checker = BatteryChecker()
    rate = rospy.Rate(1)  # 1 Hz
    while not rospy.is_shutdown():
        battery_level = checker.check_battery()
        if battery_level is not None:
            rospy.loginfo(f"Battery level: {battery_level}%")
        else:
            rospy.logwarn("Failed to retrieve battery level.")
        rate.sleep()

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass