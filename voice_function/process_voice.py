import numpy as np

import noisereduce as nr
from pydub import AudioSegment
from pydub.effects import normalize
import time
import threading
import re # Import thư viện regular expression để tách câu
import rospy
import speech_recognition as sr
from control_teleop import RobotController #Import class RobotController

if not rospy.core.is_initialized():
    rospy.init_node('voice_control_node', anonymous=True)
else:
    pass  # ROS đã được khởi tạo, không cần log cảnh báo

try:
    control = RobotController(linear_speed=0.2, angular_speed=0.5, cmd_vel_topic='/cmd_vel', goal_topic="/move_base_simple/goal")
except Exception:
    control = None  # Không in lỗi, chỉ gán None nếu khởi tạo thất bại


robot_busy = False # Might still be useful for other complex commands later
state_lock = threading.Lock() # Might still be useful
x_goal = None # To store the extracted X coordinate
y_goal = None # To store the extracted Y coordinate
status_log = []
# --- Hàm tiền xử lý âm thanh ---

def preprocess_audio(audio_data: sr.AudioData):
    # (Giữ nguyên hàm preprocess_audio như cũ)
    try:
        # 1. Lấy dữ liệu thô và thông tin từ AudioData
        raw_data = audio_data.get_raw_data()
        sample_rate = audio_data.sample_rate
        sample_width = audio_data.sample_width # Số byte trên mỗi sample (vd: 2 cho 16-bit)
        channels = 1 # Giả định là mono, speech_recognition thường làm việc với mono

        # Xác định kiểu dữ liệu numpy dựa trên sample_width
        if sample_width == 2:
            dtype = np.int16
        elif sample_width == 1:
            dtype = np.uint8 # Hoặc np.int8 nếu là signed
        elif sample_width == 4:
            dtype = np.int32
        else:
            rospy.logerr(f"Lỗi: sample_width không được hỗ trợ: {sample_width}")
            return None

        audio_array = np.frombuffer(raw_data, dtype=dtype)
        max_val = np.iinfo(dtype).max
        audio_float = audio_array.astype(np.float32) / max_val
        # Sử dụng stationary=True nếu nhiễu nền tương đối ổn định
        reduced_noise_float = nr.reduce_noise(y=audio_float, sr=sample_rate, stationary=True)

        reduced_noise_array = (reduced_noise_float * max_val).astype(dtype)
        audio_segment = AudioSegment(
            data=reduced_noise_array.tobytes(),
            sample_width=sample_width,
            frame_rate=sample_rate,
            channels=channels
        )
        # headroom điều chỉnh mức độ chuẩn hóa, 1.0 là khá nhẹ nhàng
        normalized_segment = normalize(audio_segment, headroom=1.0)

        processed_raw_data = normalized_segment.raw_data

        processed_audio_data = sr.AudioData(processed_raw_data, sample_rate, sample_width)

        rospy.loginfo("Đã hoàn thành tiền xử lý âm thanh (Giảm nhiễu & Chuẩn hóa).")
        return processed_audio_data

    except Exception as e:
        rospy.logerr(f"Lỗi trong quá trình tiền xử lý âm thanh: {e}")
        return None


# --- Hàm trích xuất tọa độ bằng regular expression ---
def normalize_keyword(keyword):
    """Chuẩn hóa keyword về một dạng thống nhất."""
    kw_lower = keyword.lower()
    normalizations = {
        "tiến lên": ["tiến lên","tịnh tiến"],
        "lùi lại" : ["lùi lại"],
        "rẽ trái" : ["rẽ trái"],
        "rẽ phải" : ["rẽ phải"],
        "đi đường thẳng": ["đi đường thẳng"],
        "đi cung tròn": ["đi cung tròn"],
        "xoay tại chỗ": ["xoay tai cho", "quay tại chỗ"],
        # "dừng lại": ["dung lai", "stop"],
    }
    for normalized, variants in normalizations.items():
        if kw_lower in variants or kw_lower == normalized:
            return normalized
    return kw_lower

# --- Core Extraction Function ---

def extract_actions_and_coordinates(text):
    """
    Trích xuất các hành động (keywords) và cặp tọa độ (x, y) liên quan từ văn bản.

    Args:
        text (str): Văn bản đầu vào.
        max_distance_keyword (int): Khoảng cách tối đa (ký tự) từ cuối keyword
                                    đến đầu cụm tọa độ để được coi là liên quan.
        default_action (str | None): Hành động mặc định cho tọa độ không có keyword.
                                     Đặt là None để không gán mặc định.

    Returns:
        list[dict]: Danh sách lệnh, mỗi lệnh là một dictionary chứa:
                    'action': Tên hành động (str).
                    'x': Tọa độ x (float hoặc None).
                    'y': Tọa độ y (float hoặc None).
    """
    # Danh sách để lưu kết quả cuối cùng (định dạng đơn giản) và thông tin tạm thời để xử lý
    max_distance_keyword=50
    default_action="đi đến"
    processed_results = []
    order_counter = 0 # Vẫn cần để giữ đúng thứ tự

    # --- Regex Definitions ---
    keywords_map = {
        r'(?:tiến\s+lên|tịnh\s+tiến)\s+(?:trong\s+)?(\d+(?:[.,]\d+)?)\s*(?:giây|dây)': "tiến lên",
        r'(?:lùi\s+lại)\s+(?:trong\s+)?(\d+(?:[.,]\d+)?)\s*(?:giây|dây)': "lùi lại",
        r'(?:rẽ\s+trái)\s+(?:trong\s+)?(\d+(?:[.,]\d+)?)\s*(?:giây|dây)': "rẽ trái",
        r'(?:rẽ\s+phải)\s+(?:trong\s+)?(\d+(?:[.,]\d+)?)\s*(?:giây|dây)': "rẽ phải",

        r'(?:đi\s+đường\s+thẳng)': "đi đường thẳng", 
        r'(?:đi\s+cung\s+tròn)': "đi cung tròn",
        r'(?:xoay\s+tại\s+chỗ|quay\s+tại\s+chỗ)': "xoay tại chỗ",
        # r'(?:dừng\s+lại|dung\s+lai|stop)': "dừng lại",
    }
    independent_actions = {"xoay tại chỗ", "dừng lại"}

    keyword_patterns = list(keywords_map.keys())
    keyword_regex = r'\b(' + '|'.join(keyword_patterns) + r')\b'

    number_pattern = r'([+-]?\d+(?:[.,]\d+)?)'
    x_def = r'(?:x|ích)\s*(?:bằng|là|=)\s*'
    y_def = r'(?:y|i)\s*(?:bằng|là|=)\s*'
    separator = r'[\s,;]*(?:và|and|;)?[\s,;]*'
    pattern_xy = rf'{x_def}{number_pattern}{separator}{y_def}{number_pattern}'
    pattern_yx = rf'{y_def}{number_pattern}{separator}{x_def}{number_pattern}'
    combined_pattern_coords = rf'(?:{pattern_xy})|(?:{pattern_yx})'

    # --- Find Items ---
    found_items = []

    # Find keywords
    for match in re.finditer(keyword_regex, text, re.IGNORECASE):
        keyword_original = match.group(1)
        normalized_kw = None
        duration_value=None
        for pattern, norm_kw in keywords_map.items():
            match_duration = re.fullmatch(pattern, keyword_original, re.IGNORECASE)
            if match_duration:
                normalized_kw = norm_kw
                # Nếu có group thời lượng trong regex
                if match_duration.lastindex:
                    try:
                        duration_value = float(match_duration.group(1).replace(',', '.'))
                    except:
                        duration_value = None
                break
        if normalized_kw is None:
             normalized_kw = normalize_keyword(keyword_original)
        found_items.append({
            'type': 'keyword',
            'normalized': normalized_kw,
            'duration': duration_value,
            'start': match.start(),
            'end': match.end(),
            'id': f"kw_{match.start()}"
        })

    # Find coordinates
    for match in re.finditer(combined_pattern_coords, text, re.IGNORECASE):
        groups = match.groups()
        x_str, y_str = None, None
        if groups[0] is not None and groups[1] is not None:
            x_str = groups[0]
            y_str = groups[1]
        elif groups[2] is not None and groups[3] is not None:
            y_str = groups[2]
            x_str = groups[3]
        else:
            # Bỏ qua cảnh báo log
            continue
        try:
            x_coord = float(x_str.replace(',', '.'))
            y_coord = float(y_str.replace(',', '.'))
            found_items.append({
                'type': 'coordinate',
                'x': x_coord,
                'y': y_coord,
                'start': match.start(),
                'end': match.end(),
                'id': f"coord_{match.start()}"
            })
        except (ValueError, TypeError):
            # Bỏ qua cảnh báo log
            pass # Không làm gì nếu chuyển đổi lỗi

    # --- Sort and Process Items ---
    found_items.sort(key=lambda item: item['start'])

    processed_ids = set()
    last_keyword_item = None

    for i, current_item in enumerate(found_items):
        if current_item['id'] in processed_ids:
            continue

        item_type = current_item['type']

        if item_type == 'keyword':
            last_keyword_item = current_item
            normalized_action = current_item['normalized']
            has_extracted_duration = current_item.get('duration') is not None


            if normalized_action in independent_actions or has_extracted_duration:
                 # Thêm kết quả đơn giản vào danh sách tạm thời
                 processed_results.append({
                        'action': normalized_action,
                        'duration': current_item.get('duration'),
                        'x': None, 'y': None,
                        '_order': order_counter
                    })
                 processed_ids.add(current_item['id'])
                 order_counter += 1
                 last_keyword_item = None

        elif item_type == 'coordinate':
            coord_item = current_item
            action_to_assign = default_action
            linked_keyword_id = None

            if last_keyword_item and last_keyword_item['id'] not in processed_ids:
                distance = coord_item['start'] - last_keyword_item['end']
                if distance >= 0 and distance <= max_distance_keyword and last_keyword_item['id'] not in processed_ids:
                    action_to_assign = last_keyword_item['normalized']
                    linked_keyword_id = last_keyword_item['id']

            # Thêm kết quả đơn giản vào danh sách tạm thời
            processed_results.append({
                'action': action_to_assign,
                'x': coord_item['x'],
                'y': coord_item['y'],
                '_order': order_counter # Thêm key tạm thời để sort
            })
            processed_ids.add(coord_item['id'])
            if linked_keyword_id:
                processed_ids.add(linked_keyword_id)
                last_keyword_item = None
            order_counter += 1

    # --- Final Sort and Cleanup ---
    # Sắp xếp dựa trên thứ tự xử lý
    processed_results.sort(key=lambda r: r['_order'])

    # Tạo danh sách kết quả cuối cùng, loại bỏ key '_order'
    final_results = []
    # for r in processed_results:
    #     result = {'action': r['action'], 'x': r['x'], 'y': r['y']}
    #     if 'duration' in r and r['duration'] is not None:
    #         result['duration'] = r['duration']
    #     final_results.append(result)

    # return final_results
    for r in processed_results:
        result = {
            'action': r['action'],
            'x': r['x'],
            'y': r['y'],
            'duration': r.get('duration', None)
        }
        final_results.append(result)

    return final_results
def extract_actions_threaded(text, result_queue):
    def run():
        results = extract_actions_and_coordinates(text)
        result_queue.put(results)  # Đẩy kết quả vào hàng đợi
    thread = threading.Thread(target=run)
    thread.start()
    return thread



# --- Hàm điều khiển robot ---
def control_go_to_coordinate(x, y):
    def move_coordinate():
        global robot_busy # Sử dụng biến global để đánh dấu trạng thái bận
        if control is None:
            rospy.logerr("RobotController không hợp lệ. Không thể gửi mục tiêu.")
            return False # Trả về False nếu không thành công
        rospy.loginfo(f"Gửi mục tiêu đến robot: x={x}, y={y}")
        try:
            control.publish_goal(float(x), float(y), 0.0)  
            return True # Trả về True nếu gửi lệnh thành công
        except Exception as e:
            return False # Trả về False nếu có lỗi
    thread = threading.Thread(target=move_coordinate)
    thread.start()


def control_direction(command_input, duration_sec, rate_hz=10):
    def move_loop():
        if control is None:
            rospy.logerr("RobotController chưa được khởi tạo.")
            return

        if command_input == "tiến lên":
            function_move = control.move_forward
        elif command_input == "lùi lại":
            function_move = control.move_backward
        elif command_input == "rẽ trái":
            function_move = control.move_forward_left
        elif command_input == "rẽ phải":
            function_move = control.move_forward_right
        elif command_input == "xoay tại chỗ":
            function_move = control.turn_right
        else:
            rospy.logwarn(f"Lệnh không hợp lệ: {command_input}")
            return

        rospy.loginfo(f"Robot command: {command_input} trong {duration_sec} giây ({rate_hz} Hz)")
        rate = rospy.Rate(rate_hz)
        end_time = time.time() + duration_sec

        try:
            while time.time() < end_time and not rospy.is_shutdown():
                function_move()
                rate.sleep()
        except rospy.ROSInterruptException:
            rospy.logwarn("ROS bị ngắt khi gửi lệnh.")
        finally:
            control.stop()
            rospy.loginfo("Đã kết thúc lệnh điều khiển.")

    # --- Khởi tạo luồng ---
    thread = threading.Thread(target=move_loop)
    thread.start()