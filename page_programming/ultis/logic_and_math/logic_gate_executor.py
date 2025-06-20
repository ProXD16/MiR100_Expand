#!/usr/bin/env python
import rospy
import time

# Define signal objects (unique instances)
SIGNAL_BREAK = object()
SIGNAL_CONTINUE = object()
SIGNAL_FATAL_ERROR = object() # Tín hiệu cho lỗi nghiêm trọng cần dừng toàn bộ

class LogicGateExecutor:
    def __init__(self):
        pass

    def compare(self, value_a, operator, value_b):
        rospy.loginfo(f"Comparing: {value_a} {operator} {value_b}")
        if operator == "equal_to":
            return value_a == value_b
        elif operator == "not_equal_to":
            return value_a != value_b
        elif operator == "less_than":
            return value_a < value_b
        elif operator == "less_than_or_equal_to":
            return value_a <= value_b
        elif operator == "greater_than":
            return value_a > value_b
        elif operator == "greater_than_or_equal_to":
            return value_a >= value_b
        else:
            rospy.logerr(f"Unknown operator: {operator}")
            return False

    def evaluate_conditions(self, conditions_block):
        """
        This method MUST be overridden by a subclass that understands the structure
        of condition_item within conditions_block and can extract/evaluate them.
        """
        if not conditions_block:
            rospy.logdebug("LogicGateExecutor.evaluate_conditions: empty conditions_block, defaulting to True.")
            return True 
        rospy.logerr("LogicGateExecutor.evaluate_conditions must be fully overridden by a subclass.")
        return False 

    def execute_loop_infinite(self, body_commands):
        rospy.loginfo("Starting infinite loop")
        while not rospy.is_shutdown():
            iteration_interrupted_by_continue = False
            for cmd_idx, cmd in enumerate(body_commands):
                if rospy.is_shutdown():
                    rospy.loginfo("Infinite loop body interrupted by ROS shutdown.")
                    return None 
                
                rospy.logdebug(f"Infinite loop: Executing body command {cmd_idx+1}/{len(body_commands)}")
                result = self.execute_command(cmd)
                
                if result is SIGNAL_FATAL_ERROR: # Ưu tiên kiểm tra lỗi nghiêm trọng
                    rospy.logerr("FATAL ERROR received in infinite loop. Propagating.")
                    return SIGNAL_FATAL_ERROR
                if result is SIGNAL_BREAK:
                    rospy.loginfo("BREAK signal received in infinite loop. Exiting loop.")
                    return None # Loop kết thúc do break, không phải lỗi
                if result is SIGNAL_CONTINUE:
                    rospy.loginfo("CONTINUE signal received in infinite loop. Proceeding to next iteration phase.")
                    iteration_interrupted_by_continue = True
                    break 
            
            if rospy.is_shutdown() and iteration_interrupted_by_continue:
                 rospy.loginfo("Infinite loop interrupted by ROS shutdown during continue processing.")
                 return None
        rospy.loginfo("Exited infinite loop (ROS shutdown or break signal)")
        return None 

    def execute_loop_count(self, iterations, body_commands):
        rospy.loginfo(f"Starting count loop for {iterations} iterations")
        for i in range(iterations):
            if rospy.is_shutdown():
                rospy.loginfo(f"Count loop interrupted by ROS shutdown at iteration {i+1}")
                return None 
            
            rospy.loginfo(f"Count loop iteration {i+1}/{iterations}")
            iteration_interrupted_by_continue = False
            for cmd_idx, cmd in enumerate(body_commands):
                if rospy.is_shutdown():
                    rospy.loginfo(f"Count loop body interrupted by ROS shutdown at iteration {i+1}, cmd {cmd_idx+1}")
                    return None

                rospy.logdebug(f"Count loop iter {i+1}: Executing body command {cmd_idx+1}/{len(body_commands)}")
                result = self.execute_command(cmd)

                if result is SIGNAL_FATAL_ERROR:
                    rospy.logerr(f"FATAL ERROR received in count loop (iteration {i+1}). Propagating.")
                    return SIGNAL_FATAL_ERROR
                if result is SIGNAL_BREAK:
                    rospy.loginfo(f"BREAK signal received in count loop (iteration {i+1}). Exiting loop.")
                    return None 
                if result is SIGNAL_CONTINUE:
                    rospy.loginfo(f"CONTINUE signal received in count loop (iteration {i+1}). Proceeding to next iteration.")
                    iteration_interrupted_by_continue = True
                    break 
            
            if rospy.is_shutdown() and iteration_interrupted_by_continue:
                 rospy.loginfo(f"Count loop interrupted by ROS shutdown during continue (iteration {i+1}).")
                 return None
        rospy.loginfo("Finished count loop")
        return None

    def execute_while(self, conditions_block, body_commands):
        rospy.loginfo("Starting while loop")
        while not rospy.is_shutdown():
            # Việc đánh giá điều kiện có thể gây lỗi nếu _get_value_from_command_source phức tạp
            # Tuy nhiên, evaluate_conditions hiện trả về bool, không phải signal
            condition_met = self.evaluate_conditions(conditions_block)
            # Nếu evaluate_conditions có thể trả về SIGNAL_FATAL_ERROR, cần xử lý ở đây
            # if condition_met is SIGNAL_FATAL_ERROR: return SIGNAL_FATAL_ERROR
            if not condition_met:
                rospy.loginfo("While loop condition became false. Exiting.")
                break 
            
            rospy.loginfo("While loop condition true. Executing body.")
            iteration_interrupted_by_continue = False
            for cmd_idx, cmd in enumerate(body_commands):
                if rospy.is_shutdown():
                    rospy.loginfo(f"While loop body interrupted by ROS shutdown, cmd {cmd_idx+1}")
                    return None

                rospy.logdebug(f"While loop: Executing body command {cmd_idx+1}/{len(body_commands)}")
                result = self.execute_command(cmd)

                if result is SIGNAL_FATAL_ERROR:
                    rospy.logerr("FATAL ERROR received in while loop. Propagating.")
                    return SIGNAL_FATAL_ERROR
                if result is SIGNAL_BREAK:
                    rospy.loginfo("BREAK signal received in while loop. Exiting loop.")
                    return None 
                if result is SIGNAL_CONTINUE:
                    rospy.loginfo("CONTINUE signal received in while loop. Re-evaluating while condition.")
                    iteration_interrupted_by_continue = True
                    break 
            
            if rospy.is_shutdown() and iteration_interrupted_by_continue:
                 rospy.loginfo("While loop interrupted by ROS shutdown during continue.")
                 return None
        rospy.loginfo("Exited while loop (condition false, ROS shutdown, or break signal)")
        return None 

    def execute_if(self, conditions_block, then_commands, else_commands=None):
        rospy.loginfo("Executing if statement")
        signal_to_propagate = None
        
        # Tương tự execute_while, evaluate_conditions có thể phức tạp
        condition_eval_result = self.evaluate_conditions(conditions_block)
        # if condition_eval_result is SIGNAL_FATAL_ERROR: return SIGNAL_FATAL_ERROR
        
        rospy.logdebug(f"If condition evaluated to: {condition_eval_result}")

        if condition_eval_result:
            rospy.loginfo("If condition true. Executing then_commands.")
            for cmd_idx, cmd in enumerate(then_commands):
                if rospy.is_shutdown(): 
                    rospy.loginfo(f"If 'then' block interrupted by ROS shutdown, cmd {cmd_idx+1}")
                    break # Thoát khỏi for, signal_to_propagate vẫn là giá trị trước đó (None hoặc từ lệnh trước)
                rospy.logdebug(f"If 'then': Executing command {cmd_idx+1}/{len(then_commands)}")
                result = self.execute_command(cmd)

                if result is SIGNAL_FATAL_ERROR: # Ưu tiên lỗi nghiêm trọng
                    return SIGNAL_FATAL_ERROR 
                if result is SIGNAL_BREAK or result is SIGNAL_CONTINUE:
                    signal_to_propagate = result
                    rospy.loginfo(f"Signal '{'BREAK' if result is SIGNAL_BREAK else 'CONTINUE'}' received in 'then' block. Propagating.")
                    break # Dừng thực thi các lệnh còn lại trong 'then' và truyền tín hiệu
        elif else_commands:
            rospy.loginfo("If condition false. Executing else_commands.")
            for cmd_idx, cmd in enumerate(else_commands):
                if rospy.is_shutdown(): 
                    rospy.loginfo(f"If 'else' block interrupted by ROS shutdown, cmd {cmd_idx+1}")
                    break
                rospy.logdebug(f"If 'else': Executing command {cmd_idx+1}/{len(else_commands)}")
                result = self.execute_command(cmd)

                if result is SIGNAL_FATAL_ERROR:
                    return SIGNAL_FATAL_ERROR
                if result is SIGNAL_BREAK or result is SIGNAL_CONTINUE:
                    signal_to_propagate = result
                    rospy.loginfo(f"Signal '{'BREAK' if result is SIGNAL_BREAK else 'CONTINUE'}' received in 'else' block. Propagating.")
                    break 
        else:
            rospy.loginfo("If condition false. No else_commands to execute.")
        
        return signal_to_propagate # Trả về None, SIGNAL_BREAK, hoặc SIGNAL_CONTINUE

    def execute_wait(self, duration):
        rospy.loginfo(f"Waiting for {duration} seconds")
        if duration > 0:
            start_time = time.time()
            while time.time() - start_time < duration:
                if rospy.is_shutdown():
                    rospy.loginfo("Wait interrupted by ROS shutdown.")
                    return None # Wait bị hủy, không phải lỗi
                time.sleep(0.1) 
        rospy.loginfo("Wait finished.")
        return None # Wait hoàn thành bình thường

    def execute_command(self, command):
        if not isinstance(command, dict):
            rospy.logerr(f"Invalid command format: {command}. Expected a dictionary.")
            # Đây có thể coi là một lỗi nghiêm trọng nếu định dạng JSON sai
            return SIGNAL_FATAL_ERROR 

        command_type = command.get("type")
        subtype = command.get("subtype")
        command_id = command.get("id", "N/A") 
        
        rospy.logdebug(f"LogicExecutor: Processing cmd ID='{command_id}', type='{command_type}', subtype='{subtype}'")

        if command_type == "control":
            if subtype == "break":
                rospy.loginfo(f"LogicExecutor (Cmd ID {command_id}): Executing CONTROL.BREAK command.")
                return SIGNAL_BREAK
            elif subtype == "continue":
                rospy.loginfo(f"LogicExecutor (Cmd ID {command_id}): Executing CONTROL.CONTINUE command.")
                return SIGNAL_CONTINUE
            else:
                rospy.logwarn(f"LogicExecutor (Cmd ID {command_id}): Unknown 'control' subtype: {subtype}. Treating as NOP.")
                return None # Lệnh control không xác định, coi như không làm gì

        elif command_type == "logic":
            if subtype == "break": 
                rospy.loginfo(f"LogicExecutor (Cmd ID {command_id}): Executing LOGIC.BREAK command.")
                return SIGNAL_BREAK
            elif subtype == "continue":
                rospy.loginfo(f"LogicExecutor (Cmd ID {command_id}): Executing LOGIC.CONTINUE command.")
                return SIGNAL_CONTINUE
            
            elif subtype == "loop":
                loop_type = command.get("config", {}).get("loop_type")
                body_commands = command.get("body_commands", [])
                if not isinstance(body_commands, list):
                     rospy.logerr(f"LogicExecutor (Cmd ID {command_id}): body_commands for loop is not a list. FATAL."); return SIGNAL_FATAL_ERROR
                if loop_type == "infinite" or loop_type == "forever":
                    return self.execute_loop_infinite(body_commands) 
                elif loop_type == "count":
                    iterations = command.get("config", {}).get("iterations", 1)
                    if not isinstance(iterations, int) or iterations < 0:
                        rospy.logerr(f"LogicExecutor (Cmd ID {command_id}): Invalid iterations '{iterations}' for count loop. FATAL."); return SIGNAL_FATAL_ERROR
                    return self.execute_loop_count(iterations, body_commands)
                else:
                    rospy.logwarn(f"LogicExecutor (Cmd ID {command_id}): Unknown loop_type '{loop_type}' for logic.loop. Treating as NOP.")
                    return None
            
            elif subtype == "while":
                conditions_block = command.get("conditions") or command.get("condition_commands")
                if conditions_block is None: conditions_block = []
                if not isinstance(conditions_block, list):
                     rospy.logerr(f"LogicExecutor (Cmd ID {command_id}): conditions_block for while is not a list. FATAL."); return SIGNAL_FATAL_ERROR
                body_commands = command.get("body_commands", [])
                if not isinstance(body_commands, list):
                     rospy.logerr(f"LogicExecutor (Cmd ID {command_id}): body_commands for while is not a list. FATAL."); return SIGNAL_FATAL_ERROR
                return self.execute_while(conditions_block, body_commands)
            
            elif subtype == "if":
                conditions_block = command.get("conditions", [])
                if not isinstance(conditions_block, list):
                     rospy.logerr(f"LogicExecutor (Cmd ID {command_id}): conditions_block for if is not a list. FATAL."); return SIGNAL_FATAL_ERROR
                then_commands = command.get("then_commands", [])
                if not isinstance(then_commands, list):
                     rospy.logerr(f"LogicExecutor (Cmd ID {command_id}): then_commands for if is not a list. FATAL."); return SIGNAL_FATAL_ERROR
                else_commands = command.get("else_commands") # Can be None or a list
                if else_commands is not None and not isinstance(else_commands, list):
                     rospy.logerr(f"LogicExecutor (Cmd ID {command_id}): else_commands for if is present but not a list. FATAL."); return SIGNAL_FATAL_ERROR
                return self.execute_if(conditions_block, then_commands, else_commands)

            elif subtype == "true" or subtype == "false":
                rospy.logdebug(f"LogicExecutor (Cmd ID {command_id}): Encountered 'logic.{subtype}' as a command. It's typically used in conditions. Doing nothing (NOP).")
                return None 
            
            else:
                rospy.logwarn(f"LogicExecutor (Cmd ID {command_id}): Unknown 'logic' subtype: {subtype}. Treating as NOP.")
                return None 

        elif command_type == "wait":
            duration = command.get("config", {}).get("duration", 0)
            if not isinstance(duration, (int, float)) or duration < 0:
                 rospy.logerr(f"LogicExecutor (Cmd ID {command_id}): Invalid duration '{duration}' for wait. FATAL."); return SIGNAL_FATAL_ERROR
            return self.execute_wait(duration)
        
        rospy.logdebug(f"LogicExecutor (Cmd ID {command_id}): Command type='{command_type}', subtype='{subtype}' not handled by base. Returning False.")
        return False # Báo cho class con thử xử lý

    def execute_program(self, json_data_list):
        if not isinstance(json_data_list, list):
            rospy.logerr(f"execute_program expects a list of programs, got {type(json_data_list)}")
            # Cố gắng phục hồi nếu chỉ một đối tượng chương trình được truyền vào
            if isinstance(json_data_list, dict) and "name" in json_data_list and "commands" in json_data_list:
                rospy.logwarn("execute_program: It seems a single program object was passed. Wrapping it in a list.")
                json_data_list = [json_data_list] 
            else:
                return # Không thể phục hồi

        if not json_data_list:
            rospy.logerr("execute_program: No JSON program data provided (empty list).")
            return

        for program_idx, program_data in enumerate(json_data_list):
            if not isinstance(program_data, dict):
                rospy.logerr(f"execute_program: Program item at index {program_idx} is not a dictionary: {program_data}")
                continue # Bỏ qua chương trình không hợp lệ

            program_name = program_data.get("name", f"Unnamed_Program_{program_idx}")
            commands = program_data.get("commands", [])

            if not isinstance(commands, list):
                rospy.logerr(f"execute_program: Commands for program '{program_name}' is not a list: {commands}")
                continue # Bỏ qua chương trình có danh sách lệnh không hợp lệ

            rospy.loginfo(f"Executing program: '{program_name}' ({len(commands)} commands)")
            if rospy.is_shutdown():
                rospy.logwarn(f"ROS shutdown before starting program: '{program_name}'")
                break # Dừng xử lý các chương trình tiếp theo
            
            for cmd_idx, command_item in enumerate(commands):
                if rospy.is_shutdown():
                    rospy.logwarn(f"Program '{program_name}' execution interrupted by ROS shutdown during command {cmd_idx+1} processing.")
                    return # Dừng toàn bộ nếu ROS tắt
                
                rospy.logdebug(f"Program '{program_name}': Executing top-level command {cmd_idx+1}/{len(commands)}")
                result = self.execute_command(command_item) 
                
                if result is SIGNAL_FATAL_ERROR:
                    rospy.logerr(f"FATAL ERROR encountered during execution of program '{program_name}'. Halting all further program execution.")
                    return # Dừng toàn bộ chuỗi chương trình
                # Các tín hiệu BREAK/CONTINUE được xử lý bên trong các cấu trúc lặp/if,
                # chúng không tự động dừng vòng lặp duyệt qua các lệnh của chương trình.
            
            if rospy.is_shutdown():
                rospy.logwarn(f"Program '{program_name}' did not fully complete due to ROS shutdown.")
                return 
            else:
                 rospy.loginfo(f"Finished executing program: '{program_name}'")