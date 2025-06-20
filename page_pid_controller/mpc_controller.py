import cvxpy as cp
import numpy as np

class MPCController:
    def __init__(self, max_vel=1.0, max_ang_vel=1.5, R=1.0):
        self.max_vel = max_vel
        self.max_ang_vel = max_ang_vel
        self.R = R
        
    def setup_mpc(self, N=10, dt=0.1):
        self.N = N
        self.dt = dt
        self.Q = np.diag([1.0, 1.0, 0.5])  # State weights
        self.R = np.diag([0.1, 0.05])      # Control weights
        
    def mpc_step(self, current_pose, target_pose):
        x, y, yaw = current_pose
        x_ref, y_ref, yaw_ref = target_pose
        
        # Control variables
        v = cp.Variable()
        omega = cp.Variable()
        
        # Linear approximation around current yaw
        cos_yaw = np.cos(yaw)
        sin_yaw = np.sin(yaw)
        
        # State prediction
        next_x = x + v * cos_yaw * self.dt
        next_y = y + v * sin_yaw * self.dt
        next_yaw = yaw + omega * self.dt
        
        # Cost function
        cost = self.Q[0,0] * (next_x - x_ref)**2 + \
               self.Q[1,1] * (next_y - y_ref)**2 + \
               self.Q[2,2] * (next_yaw - yaw_ref)**2 + \
               self.R[0,0] * v**2 + \
               self.R[1,1] * omega**2
        
        # Constraints
        constraints = [
            v <= self.max_vel,
            v >= -self.max_vel,
            omega <= self.max_ang_vel,
            omega >= -self.max_ang_vel
        ]
        
        # Solve
        prob = cp.Problem(cp.Minimize(cost), constraints)
        prob.solve(solver=cp.ECOS)
        
        if prob.status == cp.OPTIMAL:
            return float(v.value), float(omega.value)
        return 0.0, 0.0
        
    
    # def calculate_tangent_angle(self, prev_action, current_action):
    #     if prev_action['Steering'] == 'STRAIGHT' and current_action['Steering'] in ['LEFT', 'RIGHT']:
    #         return self.current_yaw
    #     elif prev_action['Steering'] in ['LEFT', 'RIGHT'] and current_action['Steering'] == 'STRAIGHT':
    #         if prev_action['Steering'] == 'LEFT':
    #             return self.current_yaw + prev_action['distance']
    #         else:  
    #             return self.current_yaw - prev_action['distance']
    #     return self.current_yaw
    
    # def trapezoidal_velocity_profile(self, distance_remaining, is_linear=True):
    #     if is_linear:
    #         max_vel = self.max_vel
    #         accel = self.accel
    #         current_vel = self.current_vel
    #     else:
    #         max_vel = self.max_ang_vel
    #         accel = self.accel / self.R 
    #         current_vel = self.current_ang_vel
    #     decel_distance = (max_vel**2) / (2 * accel)
        
    #     if distance_remaining <= decel_distance:
    #         new_vel = math.sqrt(2 * accel * distance_remaining)
    #     elif current_vel < max_vel:
    #         new_vel = min(max_vel, current_vel + accel * 0.1) 
    #     else:
    #         new_vel = max_vel
    #     return new_vel
    
    # def control_loop(self):
    #     rate = rospy.Rate(10) 
    #     while not rospy.is_shutdown():
    #         if self.current_segment < len(self.path):
    #             segment = self.path[self.current_segment]
    #             if self.current_action < len(segment):
    #                 action = segment[self.current_action]
    #                 cmd_vel = Twist()
    #                 if action['Steering'] == 'STRAIGHT':
    #                     total_distance = action['distance']
    #                     remaining_distance = total_distance - self.distance_covered
    #                     if remaining_distance > 0:
    #                         self.current_vel = self.trapezoidal_velocity_profile(remaining_distance, True)
    #                         if action['Gear'] == 'FORWARD':
    #                             cmd_vel.linear.x = self.current_vel
    #                         else:  
    #                             cmd_vel.linear.x = -self.current_vel
    #                         self.distance_covered += abs(self.current_vel) * 0.1 
    #                     else:
    #                         self.current_action += 1
    #                         self.distance_covered = 0.0
    #                         self.current_vel = 0.0
    #                         if self.current_action < len(segment):
    #                             next_action = segment[self.current_action]
    #                             if next_action['Steering'] != 'STRAIGHT':
    #                                 self.current_yaw = self.calculate_tangent_angle(action, next_action)
    #                 else:
    #                     total_angle = action['distance']
    #                     remaining_angle = total_angle - self.angle_covered
                        
    #                     if remaining_angle > 0:
    #                         self.current_ang_vel = self.trapezoidal_velocity_profile(remaining_angle, False)
    #                         linear_vel = self.current_ang_vel * self.R
    #                         if action['Gear'] == 'FORWARD':
    #                             cmd_vel.linear.x = linear_vel
    #                         else: 
    #                             cmd_vel.linear.x = -linear_vel
    #                         if action['Steering'] == 'LEFT':
    #                             cmd_vel.angular.z = self.current_ang_vel
    #                         else:  
    #                             cmd_vel.angular.z = -self.current_ang_vel
    #                         self.angle_covered += abs(self.current_ang_vel) * 0.1  
    #                     else:
    #                         self.current_action += 1
    #                         self.angle_covered = 0.0
    #                         self.current_ang_vel = 0.0
    #                         if self.current_action < len(segment):
    #                             next_action = segment[self.current_action]
    #                             if next_action['Steering'] == 'STRAIGHT':
    #                                 self.current_yaw = self.calculate_tangent_angle(action, next_action)
    #                 self.cmd_vel_pub.publish(cmd_vel)
    #             else:
    #                 self.current_segment += 1
    #                 self.current_action = 0
    #         else:
    #             cmd_vel = Twist()
    #             self.cmd_vel_pub.publish(cmd_vel)
    #         rate.sleep()
    #     plt.show()


