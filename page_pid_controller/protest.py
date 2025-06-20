import rospy
import math
import matplotlib.pyplot as plt
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
from matplotlib.animation import FuncAnimation
from mpc_controller import MPCController

class MiR100Controller:
    def __init__(self):
        rospy.init_node('mir100_controller')
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.amcl_pose_sub = rospy.Subscriber('/amcl_pose', PoseWithCovarianceStamped, self.amcl_callback)
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_yaw = 0.0
        self.trajectory_x = []
        self.trajectory_y = []
        self.path_equations = []
        self.R, self.max_vel, self.max_ang_vel = 1.0, 1.0, 1.5
        self.mpc_controller = MPCController(max_vel=self.max_vel, max_ang_vel=self.max_ang_vel,
                                         R=self.R)
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], 'b-', linewidth=2)
        self.ax.set_xlim(-20, 20)
        self.ax.set_ylim(-20, 20)
        self.ax.grid(True)
        self.ax.set_aspect('equal')
        self.ani = FuncAnimation(self.fig, self.update_plot, init_func=self.init_plot, 
                                frames=None, interval=100, blit=True, cache_frame_data=False)
        
        self.path = [
            [{'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.21}, 
             {'Steering': 'STRAIGHT', 'Gear': 'FORWARD', 'distance': 6.22}, 
             {'Steering': 'RIGHT', 'Gear': 'FORWARD', 'distance': 0.0}],
            
            [{'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.12}, 
             {'Steering': 'RIGHT', 'Gear': 'BACKWARD', 'distance': 0.25}, 
             {'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.2}],
            
            [{'Steering': 'RIGHT', 'Gear': 'BACKWARD', 'distance': 0.14}, 
             {'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.31}, 
             {'Steering': 'RIGHT', 'Gear': 'BACKWARD', 'distance': 0.02}],
            
            [{'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.36}, 
             {'Steering': 'zSTRAIGHT', 'Gear': 'FORWARD', 'distance': 1.41}, 
             {'Steering': 'RIGHT', 'Gear': 'FORWARD', 'distance': 0.04}],
            
            [{'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.13}, 
             {'Steering': 'STRAIGHT', 'Gear': 'FORWARD', 'distance': 0.3}, 
             {'Steering': 'RIGHT', 'Gear': 'FORWARD', 'distance': 0.02}],
            
            [{'Steering': 'RIGHT', 'Gear': 'BACKWARD', 'distance': 0.19}, 
             {'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.37}, 
             {'Steering': 'RIGHT', 'Gear': 'BACKWARD', 'distance': 0.12}],
            
            [{'Steering': 'RIGHT', 'Gear': 'FORWARD', 'distance': 0.57}, 
             {'Steering': 'STRAIGHT', 'Gear': 'FORWARD', 'distance': 4.58}, 
             {'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.03}],
            
            [{'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.08}, 
             {'Steering': 'RIGHT', 'Gear': 'BACKWARD', 'distance': 0.2}, 
             {'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.26}],
            
            [{'Steering': 'RIGHT', 'Gear': 'BACKWARD', 'distance': 0.22}, 
             {'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.71}, 
             {'Steering': 'RIGHT', 'Gear': 'FORWARD', 'distance': 0.14}],
            
            [{'Steering': 'LEFT', 'Gear': 'FORWARD', 'distance': 0.49}, 
             {'Steering': 'STRAIGHT', 'Gear': 'FORWARD', 'distance': 12.27}, 
             {'Steering': 'RIGHT', 'Gear': 'FORWARD', 'distance': 0.01}],
            
            [{'Steering': 'LEFT', 'Gear': 'BACKWARD', 'distance': 0.41}, 
             {'Steering': 'RIGHT', 'Gear': 'FORWARD', 'distance': 0.71}, 
             {'Steering': 'LEFT', 'Gear': 'BACKWARD', 'distance': 0.41}]
        ]
        
        self.current_segment = 0
        self.current_action = 0
        self.distance_covered = 0.0
        self.angle_covered = 0.0
        self.R = 1.0  
        self.max_vel = 1.0  
        self.max_ang_vel = 1.5  
        self.accel = 0.5 
        self.current_vel = 0.0
        self.current_ang_vel = 0.0
        
    def amcl_callback(self, msg):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        # Correct yaw calculation from quaternion
        self.current_yaw = math.atan2(2.0*(q.w*q.z + q.x*q.y), 1.0 - 2.0*(q.y*q.y + q.z*q.z))
        self.trajectory_x.append(self.current_x)
        self.trajectory_y.append(self.current_y)
        
    def init_plot(self):
        self.line.set_data([], [])
        return self.line,
    
    def update_plot(self, frame=0):
        self.line.set_data(self.trajectory_x, self.trajectory_y)
        return self.line,
    
    def get_initial_pose(self):
        rospy.loginfo("Listening data from topic /amcl_pose...")
        initial_pose = rospy.wait_for_message('/amcl_pose', PoseWithCovarianceStamped)
        self.current_x = initial_pose.pose.pose.position.x
        self.current_y = initial_pose.pose.pose.position.y
        q = initial_pose.pose.pose.orientation
        self.current_yaw = math.atan2(2.0*(q.w*q.z + q.x*q.y), 1.0 - 2.0*(q.y*q.y + q.z*q.z))
        self.trajectory_x.append(self.current_x)
        self.trajectory_y.append(self.current_y)

    def straight_path(self, t, pose, gear='FORWARD'):
        x, y, yaw = pose
        dx, dy = t * math.cos(yaw), t * math.sin(yaw)
        if gear == 'BACKWARD':
            dx, dy = -dx, -dy
        return (x + dx, y + dy, yaw)
    
    def left_circular_path(self, t, pose, gear='FORWARD', R=1.0):
        x, y, yaw = pose
        angle = t  # Góc quét
        # Tâm cung tròn nằm bên trái đường thẳng, cách R đơn vị
        xc = x - R * math.sin(yaw)  # Tâm dựa trên hướng hiện tại
        yc = y + R * math.cos(yaw)
        x_new = xc + R * math.sin(yaw + angle)
        y_new = yc - R * math.cos(yaw + angle)
        yaw_new = yaw + angle if gear == 'FORWARD' else yaw - angle  # Điều chỉnh cho BACKWARD
        yaw_new = (yaw_new + math.pi) % (2 * math.pi) - math.pi  # Chuẩn hóa
        print(f"Left: yaw = {yaw}, angle = {angle}, yaw_new = {yaw_new}, center = ({xc}, {yc})")
        return (x_new, y_new, yaw_new)

    def right_circular_path(self, t, pose, gear='FORWARD', R=1.0):
        x, y, yaw = pose
        angle = t
        xc = x + R * math.sin(yaw)
        yc = y - R * math.cos(yaw)
        x_new = xc + R * math.sin(yaw - angle)
        y_new = yc - R * math.cos(yaw - angle)
        yaw_new = (yaw - angle) if gear == 'FORWARD' else (yaw + angle)  # Điều chỉnh cho BACKWARD
        yaw_new = (yaw_new + math.pi) % (2 * math.pi) - math.pi
        return (x_new, y_new, yaw_new)

    def convert_segments_to_path(self):
        self.path_equations = []
        current_pose = (self.current_x, self.current_y, self.current_yaw)  # Lấy từ thực tế
        
        for i, segment in enumerate(self.path):
            segment_equations = []
            for action in segment:
                steering = action['Steering']
                gear = action['Gear']
                distance = action['distance']
                print(f"Segment {i}, Action {steering}: start_pose = {current_pose}")

                if steering == 'STRAIGHT':
                    segment_equations.append({
                        'type': 'line',
                        'func': self.straight_path,
                        'distance': distance,
                        'start_pose': current_pose,
                        'gear': gear
                    })
                    current_pose = self.straight_path(distance, current_pose, gear)
                elif steering in ['LEFT', 'RIGHT']:
                    segment_equations.append({
                        'type': 'arc',
                        'func': self.left_circular_path if steering == 'LEFT' else self.right_circular_path,
                        'distance': distance,
                        'start_pose': current_pose,
                        'gear': gear,
                        'R': self.R
                    })
                    if steering == 'LEFT':
                        current_pose = self.left_circular_path(distance, current_pose, gear, self.R)
                    else:
                        current_pose = self.right_circular_path(distance, current_pose, gear, self.R)
            
            self.path_equations.append(segment_equations)
            # Đồng bộ lại với thực tế trước segment tiếp theo
            current_pose = (self.current_x, self.current_y, self.current_yaw)
            print(f"End of Segment {i}: current_pose = {current_pose}")
        
        self.current_pose = current_pose
    
    def execute_path_with_mpc(self):
        rate = rospy.Rate(20)
        self.mpc_controller.setup_mpc(N=10, dt=0.1)
        
        for i, segment in enumerate(self.path_equations):
            print(f"Starting Segment {i}")
            for action in segment:
                t = 0.0
                step_size = 0.05
                while t < action['distance'] and not rospy.is_shutdown():
                    ref_t = min(t + step_size, action['distance'])
                    ref_pose = action['func'](
                        ref_t,
                        action['start_pose'],
                        **{k: v for k, v in action.items() if k in ['gear', 'R']}
                    )
                    current_pose = (self.current_x, self.current_y, self.current_yaw)
                    v, omega = self.mpc_controller.mpc_step(current_pose, ref_pose)
                    print(f"Segment {i}, Action {action['type']}: v = {v}, omega = {omega}, ref_pose = {ref_pose}, current_pose = {current_pose}")
                    cmd_vel = Twist()
                    cmd_vel.linear.x = v
                    cmd_vel.angular.z = omega
                    self.cmd_vel_pub.publish(cmd_vel)
                    t += step_size
                    rate.sleep()
                    if int(t/step_size) % 5 == 0:
                        self.update_plot()

    # def plot_path(self):
    #     plt.figure()
    #     plt.plot(self.trajectory_x, self.trajectory_y, 'b-', label='Actual path')
    #     plt.axis('equal')
    #     plt.grid(True)
    #     plt.legend()
    #     plt.show()

if __name__ == '__main__':
    try:
        controller = MiR100Controller()
        controller.get_initial_pose()
        controller.convert_segments_to_path()
        controller.execute_path_with_mpc()
        # controller.plot_path()
    except rospy.ROSInterruptException:
        pass