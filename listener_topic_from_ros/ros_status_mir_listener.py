#!/usr/bin/env python
import rospy
from std_msgs.msg import String
import json
import os
from datetime import datetime

# Cấu hình thư mục và file lưu trữ
DATA_DIR = "database_json"
STATUS_FILE = os.path.join(DATA_DIR, "mir_status.json")

# Đảm bảo thư mục tồn tại
os.makedirs(DATA_DIR, exist_ok=True)

def callback(msg):
    try:
        # Ghi dữ liệu mới vào file
        with open(STATUS_FILE, 'w') as f:
            data = {
                "timestamp": datetime.now().isoformat(),
                "data": json.loads(msg.data)  # Giữ nguyên cấu trúc message
            }
            json.dump(data, f, indent=2)
        print(f"Đã cập nhật status vào {STATUS_FILE}")
    except Exception as e:
        print(f"Lỗi khi xử lý message: {e}")

def listener():
    rospy.init_node('mir_status_logger')
    rospy.Subscriber('/mir_status_msg', String, callback)
    print("Đang lắng nghe topic /mir_status_msg...")
    rospy.spin()

if __name__ == '__main__':
    listener()