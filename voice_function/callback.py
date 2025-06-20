
import numpy as np
import io
import noisereduce as nr
from pydub.effects import normalize
import time
import rospy
from dash import dcc, html
from dash.dependencies import Input, Output, State # Import State if needed, but globals are simpler here
import speech_recognition as sr
from process_voice import *
import queue

def setup_callback(app):
    
    
    @app.callback(
        Output('status-output', 'children', allow_duplicate=True), # Cần allow_duplicate
        Input('speak-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def recognize_speech_callback(n_clicks):
        global x_goal, y_goal,results, duration_time # Sử dụng biến global để lưu kết quả

        if control is None:
            rospy.logerr("Callback 'Nói' được gọi nhưng RobotController không hợp lệ.")
            return "Lỗi: Không thể kết nối với robot controller."

        # # Kiểm tra robot_busy nếu cần (ví dụ: không cho nghe khi đang chạy)
        # # with state_lock:
        # if robot_busy:
        #     rospy.logwarn("Nút 'Nói' được nhấn khi robot đang bận.")
        #     return "Robot đang di chuyển, vui lòng đợi..."

        r = sr.Recognizer()
        mic = sr.Microphone()
        text_output = "Đang chuẩn bị nghe..."

        # Reset global goals trước khi nghe
        x_goal = None
        y_goal = None
        results= None
        duration_time=None

        with mic as source:
            rospy.loginfo("Chuẩn bị nghe: Hiệu chỉnh tiếng ồn nền...")
            try:
                r.adjust_for_ambient_noise(source, duration=2.5) # Giảm thời gian hiệu chỉnh nếu cần
                rospy.loginfo("Bắt đầu nghe...")
                # Tăng phrase_time_limit nếu người dùng cần nói dài hơn
                audio_original = r.listen(source, timeout=8, phrase_time_limit=15)
                rospy.loginfo("Đã nghe xong, đang tiền xử lý...")
                # Tùy chọn: Bật/tắt tiền xử lý
                enable_preprocessing = True
                if enable_preprocessing:
                    audio = preprocess_audio(audio_original)
                    if audio is None:
                        rospy.logwarn("Tiền xử lý thất bại, sử dụng âm thanh gốc.")
                        audio = audio_original # Fallback về âm thanh gốc nếu lỗi
                else:
                    audio = audio_original
                    rospy.loginfo("Bỏ qua tiền xử lý âm thanh.")

                rospy.loginfo("Đang gửi đi để nhận dạng...")
                text = r.recognize_google(audio, language='vi-VN')
                rospy.loginfo(f"Google Speech Recognition nghĩ bạn đã nói: '{text}'")

                # Trích xuất tọa độ từ văn bản
                result_queue = queue.Queue()
                thread = extract_actions_threaded(text, result_queue)

                # Chờ thread chạy xong rồi lấy kết quả
                thread.join()
                results = result_queue.get()
                # results = extract_actions_and_coordinates(text)

                if results:  # Kiểm tra xem danh sách results có rỗng không
                    # Bắt đầu xây dựng chuỗi output
                    text_output = f"Đã nhận dạng: \"{text}\".\n"
                    text_output += "Lệnh đã trích xuất:\n"

                    # Lặp qua từng lệnh trong danh sách results
                    for i, command in enumerate(results):
                        action = command['action']
                        x_coord = command['x']
                        y_coord = command['y']
                        
                        duration_time=command['duration']

                        # Định dạng dòng cho lệnh hiện tại
                        # Sử dụng enumerate để đánh số thứ tự (1, 2, 3...)
                        command_line = f" {i+1}. {action}"

                        # Chỉ thêm tọa độ nếu chúng tồn tại (không phải None)
                        if x_coord is not None and y_coord is not None:
                            command_line += f": x={x_coord}, y={y_coord}"
                        if duration_time is not None: 
                            command_line += f": time={duration_time}"
                        # (Bạn có thể thêm logic để xử lý nếu chỉ có x hoặc y, nhưng hàm hiện tại thường trả về cả hai hoặc không)

                        # Thêm dòng lệnh đã định dạng vào chuỗi output, cùng với dấu xuống dòng
                        text_output += command_line + "\n"

                    # Thêm thông báo cuối cùng
                    text_output += "Nhấn 'Run' để thực hiện các lệnh." # Hoặc một thông báo phù hợp khác

                    

                else:
                    # Thông báo nếu không tìm thấy lệnh nào (cả action và tọa độ)
                    text_output = f"Đã nhận dạng: \"{text}\", nhưng không trích xuất được lệnh hợp lệ (hành động/tọa độ).\nVui lòng thử lại."

                return html.Pre(text_output) # Dùng Pre để giữ định dạng xuống dòng

            except sr.WaitTimeoutError:
                rospy.logwarn("Không phát hiện giọng nói trong thời gian chờ.")
                return "Không nghe thấy gì. Vui lòng thử lại."
            except sr.UnknownValueError:
                rospy.logwarn("Google Speech Recognition không thể hiểu âm thanh.")
                return "Không thể hiểu bạn nói gì. Vui lòng nói rõ hơn và thử định dạng 'x bằng [số] y bằng [số]'."
            except sr.RequestError as e:
                rospy.logerr(f"Không thể yêu cầu kết quả từ Google Speech Recognition; {e}")
                return f"Lỗi mạng hoặc dịch vụ nhận dạng: {e}"
            except Exception as e:
                rospy.logerr(f"Lỗi không xác định trong quá trình nhận dạng: {e}")
                # In traceback để debug
                import traceback
                traceback.print_exc()
                return f"Lỗi không mong muốn: {e}"

    # --- Callback của Dash khi nhấn nút "Run" ---
    # @app.callback(
    #     Output('status-log-store', 'data', allow_duplicate=True),
    #     Input('run-voice', 'n_clicks'),
    #     prevent_initial_call=True
    # )
    # def start_voice_execution(n_clicks):
    #     global results
    #     if not results:
    #         return ["⚠️ Chưa có lệnh nào được nhận dạng."]

    #     thread = threading.Thread(target=execute_commands)
    #     thread.start()
    #     return []  # Reset log

    # @app.callback(
    #     Output('status-output', 'children', allow_duplicate=True),
    #     Input('update-status-interval', 'n_intervals'),
    #     State('status-log-store', 'data')
    # )
    # def update_status_output(n, log):
    #     return [html.Div(line) for line in status_log]

    @app.callback(
        Output('status-output', 'children', allow_duplicate=True),
        Input('run-voice', 'n_clicks'),
        prevent_initial_call=True
    )
    def run_voice_callback_logic(n_clicks):
        global results, control

        if control is None:
            return "❌ Lỗi: Không thể kết nối với robot controller."

        if not results:
            return "⚠️ Chưa có lệnh nào được nhận dạng."

        output_messages = []
        commands = list(results)
        results.clear()

        output_messages.append(f"▶️ Bắt đầu thực hiện {len(commands)} lệnh:")

        for i, cmd in enumerate(commands):
            action = cmd.get('action')
            x = cmd.get('x')
            y = cmd.get('y')
            duration = cmd.get('duration')
            success = False

            msg = f" - Lệnh {i+1}: {action}"

            if action in ["đi đến", "đi đường thẳng", "đi cung tròn"] and x is not None and y is not None:
                msg += f" (x={x}, y={y})"
                success = control_go_to_coordinate(x, y)

            elif action in ["tiến lên", "lùi lại", "rẽ trái", "rẽ phải"] and duration is not None:
                msg += f" (duration={duration}s)"
                success = control_direction(command_input=action, duration_sec=duration, rate_hz=10)

            elif action == "xoay tại chỗ" and duration is not None:
                msg += f" (duration={duration}s)"
                success = control_direction(command_input="xoay tại chỗ", duration_sec=duration, rate_hz=10)

            else:
                msg += " ❌ Lệnh không hợp lệ hoặc thiếu thông tin."

            msg += " ✅" if success else " ❌"
            output_messages.append(msg)

            # Cho nghỉ một chút giữa các lệnh
            time.sleep(0.5)

        output_messages.append("✅ Đã hoàn thành tất cả các lệnh.")

        return "\n".join(output_messages)