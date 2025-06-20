import gymnasium as gym
import numpy as np
from stable_baselines3 import SAC
from stable_baselines3.common.env_util import make_vec_env
from scipy.interpolate import CubicSpline
import torch
import torch.nn as nn
import onnx
import logging
import sys
import traceback

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PathFollowingEnv(gym.Env):
    metadata = {'render_modes': ['human'], 'render_fps': 30} # Required by gymnasium

    def __init__(self):
        super(PathFollowingEnv, self).__init__()
        logger.debug("Initializing PathFollowingEnv")
        
        self.action_space = gym.spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32)
        
        self.v_max = 0.5
        self.v_min = -0.5
        self.omega_limit_abs = 0.5
        self.wheelbase = 0.6
        self.dt = 0.05
        self.lookahead_distance = 0.2
        
        self.max_episode_steps = 400
        self.current_step_count = 0

        self.Nw_krivulje = 5
        self.L_min_segment = 0.5
        self.L_max_segment = 2.0
        self.straight_path_prob = 0.1
        self.Lw_straight = 2.5

        self.k1_reward = 5.0
        self.k2_reward = 2.5
        self.k3_reward = 0.2
        self.etol_reward = 0.2
        self.epsilon_stationary = 1e-6

        self.np_random = None # Will be initialized in reset by super().reset(seed=seed)
        self._configure_spaces() # Initialize spaces if they need seeding

    def _configure_spaces(self):
        # If your action_space or observation_space relied on self.np_random for their ranges
        # you might need to re-initialize them after np_random is set.
        # For fixed Box spaces like these, it's usually not necessary.
        pass

    def reset(self, seed=None, options=None):
        super().reset(seed=seed) # This initializes self.np_random
        logger.debug(f"Resetting environment with seed: {seed}")
        
        self.current_step_count = 0

        # Use self.np_random for all random operations from now on
        if self.np_random.uniform() < self.straight_path_prob:
            self.waypoints_x = np.array([0, self.Lw_straight])
            self.waypoints_y = np.array([0, 0])
        else:
            valid_path = False
            attempts = 0
            while not valid_path and attempts < 100: # Add attempt limit
                self.waypoints_x = self.np_random.uniform(-2, 2, self.Nw_krivulje)
                self.waypoints_y = self.np_random.uniform(-2, 2, self.Nw_krivulje)
                if len(self.waypoints_x) < 2:
                    attempts += 1
                    continue
                distances = np.sqrt(np.diff(self.waypoints_x)**2 + np.diff(self.waypoints_y)**2)
                if np.all(distances >= self.L_min_segment) and np.all(distances <= self.L_max_segment):
                    valid_path = True
                attempts += 1
            if not valid_path: # Fallback if random generation fails
                logger.warning("Failed to generate a valid random path after 100 attempts, using default.")
                self.waypoints_x = np.array([0, self.Lw_straight])
                self.waypoints_y = np.array([0, 0])

        num_waypoints = len(self.waypoints_x)
        if num_waypoints < 2:
             self.waypoints_x = np.array([0, 1.0])
             self.waypoints_y = np.array([0, 0])
             num_waypoints = 2
        
        self.t_path = np.linspace(0, 1, num_waypoints)
        try:
            if num_waypoints == 2:
                self.spline_x = CubicSpline(self.t_path, self.waypoints_x, bc_type='clamped')
                self.spline_y = CubicSpline(self.t_path, self.waypoints_y, bc_type='clamped')
            else:
                self.spline_x = CubicSpline(self.t_path, self.waypoints_x)
                self.spline_y = CubicSpline(self.t_path, self.waypoints_y)
        except ValueError as e:
            logger.error(f"CubicSpline error: {e}. Waypoints X: {self.waypoints_x}, Y: {self.waypoints_y}, t: {self.t_path}")
            # Fallback to a simple straight line
            self.waypoints_x = np.array([0.0, 1.0])
            self.waypoints_y = np.array([0.0, 0.0])
            self.t_path = np.linspace(0, 1, 2)
            self.spline_x = CubicSpline(self.t_path, self.waypoints_x, bc_type='clamped')
            self.spline_y = CubicSpline(self.t_path, self.waypoints_y, bc_type='clamped')


        self.spline_derivative_x = self.spline_x.derivative()
        self.spline_derivative_y = self.spline_y.derivative()

        initial_pos_error_range = 0.1
        initial_heading_error_range = 0.0873
        
        self.x = self.waypoints_x[0] + self.np_random.uniform(-initial_pos_error_range, initial_pos_error_range)
        self.y = self.waypoints_y[0] + self.np_random.uniform(-initial_pos_error_range, initial_pos_error_range)
        
        path_angle_start_x = self.spline_derivative_x(0)
        path_angle_start_y = self.spline_derivative_y(0)
        initial_path_angle = np.arctan2(path_angle_start_y, path_angle_start_x)
        
        self.theta = initial_path_angle + self.np_random.uniform(-initial_heading_error_range, initial_heading_error_range)
        self.theta = np.arctan2(np.sin(self.theta), np.cos(self.theta))
        
        self.v = 0.0
        self.omega = 0.0

        obs = self._get_observation()
        logger.debug(f"Reset observation: {obs}")
        if np.any(np.isnan(obs)):
            logger.error("NaN detected in reset observation. Attempting recovery.")
            self._recover_from_nan_obs()
            obs = self._get_observation()
            if np.any(np.isnan(obs)):
                 raise ValueError("Invalid observation after attempting recovery in reset")
        return obs, {}

    def _recover_from_nan_obs(self):
        """Helper to reset state to a known good configuration if NaNs occur."""
        logger.warning("Executing recovery for NaN observation in reset.")
        self.waypoints_x = np.array([0.0, 1.0])
        self.waypoints_y = np.array([0.0, 0.0])
        self.t_path = np.linspace(0,1,2)
        self.spline_x = CubicSpline(self.t_path, self.waypoints_x, bc_type='clamped')
        self.spline_y = CubicSpline(self.t_path, self.waypoints_y, bc_type='clamped')
        self.spline_derivative_x = self.spline_x.derivative()
        self.spline_derivative_y = self.spline_y.derivative()
        self.x, self.y, self.theta, self.v, self.omega = 0.0, 0.0, 0.0, 0.0, 0.0

    def _get_observation(self):
        t_eval_pts = np.linspace(0, 1, 100)
        path_x_pts = self.spline_x(t_eval_pts)
        path_y_pts = self.spline_y(t_eval_pts)
        
        distances_sq = (path_x_pts - self.x)**2 + (path_y_pts - self.y)**2
        if not np.all(np.isfinite(distances_sq)): # Check for NaNs in distances_sq
            logger.error(f"NaN or Inf in distances_sq. x:{self.x}, y:{self.y}, path_x_pts:{path_x_pts[:5]}, path_y_pts:{path_y_pts[:5]}")
            # This often means spline is problematic.
            # For safety, return a zero observation or a fixed safe observation.
            return np.zeros(self.observation_space.shape, dtype=np.float32)


        closest_idx = np.argmin(distances_sq)
        closest_t = t_eval_pts[closest_idx]

        dx = self.x - self.spline_x(closest_t)
        dy = self.y - self.spline_y(closest_t)
        tangent_x_at_closest = self.spline_derivative_x(closest_t)
        tangent_y_at_closest = self.spline_derivative_y(closest_t)
        norm_tangent_at_closest = np.sqrt(tangent_x_at_closest**2 + tangent_y_at_closest**2)
        
        if norm_tangent_at_closest < 1e-6:
            e_p = np.sign(dx * tangent_y_at_closest - dy * tangent_x_at_closest) * np.sqrt(dx**2+dy**2) if np.sqrt(dx**2+dy**2) > 1e-6 else 0.0
        else:
            e_p = (dx * tangent_y_at_closest - dy * tangent_x_at_closest) / norm_tangent_at_closest
        
        angle_of_path_at_closest = np.arctan2(tangent_y_at_closest, tangent_x_at_closest)
        psi_e = angle_of_path_at_closest - self.theta
        psi_e = np.arctan2(np.sin(psi_e), np.cos(psi_e))

        if norm_tangent_at_closest < 1e-6:
            t_lookahead_psi_e2 = closest_t
        else:
            t_lookahead_psi_e2 = closest_t + self.lookahead_distance / norm_tangent_at_closest
        t_lookahead_psi_e2 = np.clip(t_lookahead_psi_e2, 0, 1.0)
        
        tangent_x_at_lookahead = self.spline_derivative_x(t_lookahead_psi_e2)
        tangent_y_at_lookahead = self.spline_derivative_y(t_lookahead_psi_e2)
        angle_of_path_at_lookahead = np.arctan2(tangent_y_at_lookahead, tangent_x_at_lookahead)
        
        psi_e2 = angle_of_path_at_lookahead - self.theta
        psi_e2 = np.arctan2(np.sin(psi_e2), np.cos(psi_e2))
        
        obs = np.array([e_p, psi_e, self.v, self.omega, psi_e2], dtype=np.float32)
        if np.any(np.isnan(obs)):
            logger.error(f"NaN in _get_observation. e_p:{e_p}, psi_e:{psi_e}, v:{self.v}, omega:{self.omega}, psi_e2:{psi_e2}")
            obs = np.nan_to_num(obs, nan=0.0, posinf=1.0, neginf=-1.0) # Basic sanitization
        return obs

    def step(self, action):
        self.current_step_count += 1
        # logger.debug(f"Stepping with action: {action}")

        v_cmd_from_sac = action[0] * (self.v_max - self.v_min) / 2 + (self.v_max + self.v_min) / 2
        v_cmd_from_sac = np.clip(v_cmd_from_sac, self.v_min, self.v_max)

        t_eval_pts = np.linspace(0, 1, 100)
        path_x_pts = self.spline_x(t_eval_pts)
        path_y_pts = self.spline_y(t_eval_pts)
        distances_sq = (path_x_pts - self.x)**2 + (path_y_pts - self.y)**2
        closest_idx = np.argmin(distances_sq)
        t_closest_for_pp = t_eval_pts[closest_idx]

        tangent_x_at_closest_pp = self.spline_derivative_x(t_closest_for_pp)
        tangent_y_at_closest_pp = self.spline_derivative_y(t_closest_for_pp)
        norm_tangent_at_closest_pp = np.sqrt(tangent_x_at_closest_pp**2 + tangent_y_at_closest_pp**2)

        if norm_tangent_at_closest_pp < 1e-6:
            t_pp_lookahead = t_closest_for_pp
        else:
            t_pp_lookahead = t_closest_for_pp + self.lookahead_distance / norm_tangent_at_closest_pp
        t_pp_lookahead = np.clip(t_pp_lookahead, 0, 1.0)

        x_pp_lookahead = self.spline_x(t_pp_lookahead)
        y_pp_lookahead = self.spline_y(t_pp_lookahead)

        alpha_l = np.arctan2(y_pp_lookahead - self.y, x_pp_lookahead - self.x) - self.theta
        alpha_l = np.arctan2(np.sin(alpha_l), np.cos(alpha_l))
        
        L_pp = np.sqrt((x_pp_lookahead - self.x)**2 + (y_pp_lookahead - self.y)**2)
        
        if L_pp < 1e-3:
            omega_cmd = 0.0
        else:
            omega_cmd = (2 * v_cmd_from_sac * np.sin(alpha_l)) / L_pp
        
        omega_cmd = np.clip(omega_cmd, -self.omega_limit_abs, self.omega_limit_abs)

        constraint_sum = abs(v_cmd_from_sac) + (self.wheelbase / 2) * abs(omega_cmd)
        v_final = v_cmd_from_sac
        omega_final = omega_cmd

        if constraint_sum > self.v_max:
            scale = self.v_max / constraint_sum if constraint_sum > 1e-6 else 0.0
            v_final = v_cmd_from_sac * scale
            omega_final = omega_cmd * scale
        
        v_final = np.clip(v_final, self.v_min, self.v_max)
        omega_final = np.clip(omega_final, -self.omega_limit_abs, self.omega_limit_abs)

        self.x += v_final * np.cos(self.theta) * self.dt
        self.y += v_final * np.sin(self.theta) * self.dt
        self.theta += omega_final * self.dt
        self.theta = np.arctan2(np.sin(self.theta), np.cos(self.theta))

        self.v = v_final
        self.omega = omega_final

        observation_next = self._get_observation()
        e_p_next = observation_next[0]

        stationary_flag = 1 if abs(v_final) < self.epsilon_stationary else 0
        reward_path_dev = -self.k1_reward * abs(e_p_next)
        reward_vel_term = self.k2_reward * v_final * (1 - abs(e_p_next) / self.etol_reward)
        penalty_stationary = -self.k3_reward * stationary_flag
        reward = reward_path_dev + reward_vel_term + penalty_stationary

        terminated_failure = abs(e_p_next) > 1.0
        dist_to_goal_sq = (self.x - self.waypoints_x[-1])**2 + (self.y - self.waypoints_y[-1])**2
        terminated_success = np.sqrt(dist_to_goal_sq) < 0.2
        
        terminated = terminated_failure or terminated_success
        truncated = self.current_step_count >= self.max_episode_steps
        
        # logger.debug(f"Step result - obs: {observation_next}, reward: {reward}, terminated: {terminated}, truncated: {truncated}")
        if np.any(np.isnan(observation_next)) or np.isnan(reward):
            logger.error(f"NaN detected in step output. Obs:{observation_next}, Reward:{reward}. Trying to recover.")
            observation_next = np.nan_to_num(observation_next, nan=0.0, posinf=1.0, neginf=-1.0)
            reward = float(np.nan_to_num(reward, nan=-10.0))
            if np.any(np.isnan(observation_next)):
                raise ValueError("Invalid step output even after nan_to_num")

        return observation_next, float(reward), terminated, truncated, {}

    def render(self):
        pass # No rendering implemented

    def close(self): # Required by gymnasium
        pass


# Training SAC
if __name__ == "__main__":
    try:
        logger.info("Starting SAC training")
        logger.info(f"PyTorch version: {torch.__version__}")
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
        
        env = make_vec_env(PathFollowingEnv, n_envs=1, seed=np.random.randint(0, 10000))
        logger.info("Environment created")
        
        model = SAC(
            "MlpPolicy",
            env,
            verbose=1,
            learning_rate=3e-4,
            buffer_size=500000,
            learning_starts=5000,
            batch_size=256,
            tau=0.005,
            gamma=0.99,
            train_freq=1,
            gradient_steps=1,
            policy_kwargs=dict(net_arch=[256, 256]),
            ent_coef='auto',
            device='cuda' if torch.cuda.is_available() else 'cpu',
            seed=np.random.randint(0, 10000) # Seed for SAC model
        )
        logger.info("SAC model initialized")
        logger.info("Starting learning")
        model.learn(total_timesteps=500)
        logger.info("Training completed")
        model.save("sac_path_following")
        logger.info("Model saved as sac_path_following")

        logger.info("Exporting to ONNX")
        
        class PolicyNet(nn.Module):
            def __init__(self, obs_dim, act_dim):
                super(PolicyNet, self).__init__()
                self.fc1 = nn.Linear(obs_dim, 256)
                self.fc2 = nn.Linear(256, 256)
                self.fc3 = nn.Linear(256, act_dim)
                self.relu = nn.ReLU()
                self.tanh = nn.Tanh()

            def forward(self, x):
                x = self.relu(self.fc1(x))
                x = self.relu(self.fc2(x))
                mu = self.fc3(x) 
                return self.tanh(mu)

        obs_dim = env.observation_space.shape[0]
        act_dim = env.action_space.shape[0]
        onnx_policy_net = PolicyNet(obs_dim, act_dim)
        
        actor_state_dict = model.policy.actor.state_dict()
        onnx_policy_net.fc1.weight.data = actor_state_dict['latent_pi.0.weight']
        onnx_policy_net.fc1.bias.data = actor_state_dict['latent_pi.0.bias']
        onnx_policy_net.fc2.weight.data = actor_state_dict['latent_pi.2.weight']
        onnx_policy_net.fc2.bias.data = actor_state_dict['latent_pi.2.bias']
        onnx_policy_net.fc3.weight.data = actor_state_dict['mu.weight']
        onnx_policy_net.fc3.bias.data = actor_state_dict['mu.bias']
        
        onnx_policy_net.eval()
        device_for_export = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        onnx_policy_net.to(device_for_export)

        try:
            dummy_input = torch.randn(1, obs_dim, device=device_for_export)
            torch.onnx.export(
                onnx_policy_net,
                dummy_input,
                "sac_model.onnx",
                input_names=["input"],
                output_names=["output"],
                opset_version=11
            )
            logger.info("Model exported to ONNX successfully (attempt 1)")
        except Exception as e:
            logger.warning(f"First ONNX export attempt failed: {str(e)}")
            logger.info("Trying alternative approach with CPU-only tensors for export")
            onnx_policy_net.cpu()
            dummy_input = torch.randn(1, obs_dim)
            torch.onnx.export(
                onnx_policy_net,
                dummy_input,
                "sac_model.onnx",
                input_names=["input"],
                output_names=["output"],
                opset_version=11
            )
            logger.info("Model exported to ONNX successfully (attempt 2, CPU)")
        
        logger.info("Model has been saved as sac_model.onnx")

    except Exception as e:
        logger.error(f"Error during training: {str(e)}")
        traceback.print_exc()
        sys.exit(1)