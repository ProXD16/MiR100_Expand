import subprocess, socket, time, threading, sys, os

def is_roscore_running():
    try:
        s = socket.create_connection(("localhost", 11311), timeout=1)
        s.close()
        return True
    except socket.error:
        return False

def start_roscore_background():
    print("🚀 Đang khởi động roscore ngầm...")
    subprocess.Popen(
        ['roscore'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setpgrp 
    )

def wait_for_roscore(timeout=15):
    print("⏳ Đợi roscore sẵn sàng...")
    for i in range(timeout):
        if is_roscore_running():
            print("✅ roscore đã sẵn sàng.")
            return True
        time.sleep(1)
    print("❌ roscore không sẵn sàng sau thời gian chờ.")
    return False

if __name__ == "__main__":
    if not is_roscore_running():
        start_roscore_background()
        if not wait_for_roscore():
            sys.exit("❌ Không thể kết nối đến roscore.")
    from threading_launcher import app, run_ros_node, run_map_listener
    threading.Thread(target=run_ros_node, daemon=True).start()
    threading.Thread(target=run_map_listener, daemon=True).start()
    app.run(debug=True, host='0.0.0.0', port=8050)