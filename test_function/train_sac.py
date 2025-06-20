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
    def __init__(self):
        super(PathFollowingEnv, self).__init__()
        logger.debug("Initializing PathFollowingEnv")
        self.action_space = gym.spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32)
        self.v_max = 0.4
        self.v_min = -0.4
        self.dt = 0.01
        self.lookahead_distance = 0.15
        self.seed_value = None
        self.rng = None
        self.reset()

    def seed(self, seed=None):
        logger.debug(f"Setting seed: {seed}")
        self.seed_value = seed
        self.rng = np.random.default_rng(seed)
        return [seed]

    def reset(self, seed=None, options=None):
        logger.debug("Resetting environment")
        if seed is not None:
            self.seed(seed)
        if self.rng is None:
            self.rng = np.random.default_rng(self.seed_value)
        
        self.t = np.linspace(0, 1, 5)
        self.waypoints_x = self.rng.uniform(-2, 2, 5)
        self.waypoints_y = self.rng.uniform(-2, 2, 5)
        self.spline_x = CubicSpline(self.t, self.waypoints_x)
        self.spline_y = CubicSpline(self.t, self.waypoints_y)
        self.spline_derivative_x = self.spline_x.derivative()
        self.spline_derivative_y = self.spline_y.derivative()
        self.x = self.waypoints_x[0]
        self.y = self.waypoints_y[0]
        self.theta = np.arctan2(self.spline_derivative_y(0), self.spline_derivative_x(0))
        self.v = 0.0
        self.omega = 0.0
        obs = self._get_observation()
        logger.debug(f"Reset observation: {obs}")
        if np.any(np.isnan(obs)):
            logger.error("NaN detected in observation")
            raise ValueError("Invalid observation")
        return obs, {}

    def _get_observation(self):
        t = np.linspace(0, 1, 1000)
        distances = np.sqrt((self.spline_x(t) - self.x)**2 + (self.spline_y(t) - self.y)**2)
        closest_t = t[np.argmin(distances)]
        dx = self.x - self.spline_x(closest_t)
        dy = self.y - self.spline_y(closest_t)
        tangent_x = self.spline_derivative_x(closest_t)
        tangent_y = self.spline_derivative_y(closest_t)
        norm_tangent = np.sqrt(tangent_x**2 + tangent_y**2)
        e_p = (dx * tangent_y - dy * tangent_x) / norm_tangent if norm_tangent != 0 else 0.0
        angle_to_path = np.arctan2(tangent_y, tangent_x)
        psi_e = angle_to_path - self.theta
        psi_e = np.arctan2(np.sin(psi_e), np.cos(psi_e))
        lookahead_t = closest_t + self.lookahead_distance / norm_tangent if norm_tangent != 0 and closest_t + self.lookahead_distance / norm_tangent <= 1 else 1.0
        lookahead_angle = np.arctan2(self.spline_derivative_y(lookahead_t), self.spline_derivative_x(lookahead_t))
        psi_e2 = lookahead_angle - self.theta
        psi_e2 = np.arctan2(np.sin(psi_e2), np.cos(psi_e2))
        obs = np.array([e_p, psi_e, self.v, self.omega, psi_e2], dtype=np.float32)
        return obs

    def step(self, action):
        logger.debug(f"Stepping with action: {action}")
        v = action[0] * (self.v_max - self.v_min) / 2 + (self.v_max + self.v_min) / 2
        v = np.clip(v, self.v_min, self.v_max)
        self.omega = 1.5 * self._get_observation()[1]
        self.x += v * np.cos(self.theta) * self.dt
        self.y += v * np.sin(self.theta) * self.dt
        self.theta += self.omega * self.dt
        self.v = v
        observation = self._get_observation()
        e_p = observation[0]
        stationary_flag = 1 if abs(v) < 0.01 else 0
        k1, k2, k3 = 5.0, 2.5, 0.2
        e_tol = 0.2
        reward = -k1 * abs(e_p) + k2 * v * (1 - abs(e_p) / e_tol) - k3 * stationary_flag
        done = abs(e_p) > 1.0 or np.sqrt((self.x - self.waypoints_x[-1])**2 + (self.y - self.waypoints_y[-1])**2) < 0.2
        truncated = False
        logger.debug(f"Step result - obs: {observation}, reward: {reward}, done: {done}")
        if np.any(np.isnan(observation)) or np.isnan(reward):
            logger.error("NaN detected in step")
            raise ValueError("Invalid step output")
        return observation, reward, done, truncated, {}

    def render(self):
        pass

# Training SAC
if __name__ == "__main__":
    try:
        logger.info("Starting SAC training")
        logger.info(f"PyTorch version: {torch.__version__}")
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
        env = make_vec_env(PathFollowingEnv, n_envs=1)
        logger.info("Environment created")
        model = SAC(
            "MlpPolicy",
            env,
            verbose=1,
            learning_rate=3e-4,
            buffer_size=100000,
            learning_starts=1000,
            batch_size=256,
            tau=0.005,
            gamma=0.99,
            train_freq=1,
            gradient_steps=1,
            policy_kwargs=dict(net_arch=[256, 256]),
            device='cuda' if torch.cuda.is_available() else 'cpu'
        )
        logger.info("SAC model initialized")
        logger.info("Starting learning")
        model.learn(total_timesteps=100000)
        logger.info("Training completed")
        model.save("sac_path_following")
        logger.info("Model saved as sac_path_following")

        # Export to ONNX
        logger.info("Exporting to ONNX")
        policy = model.policy
        logger.debug(f"Policy state_dict keys: {list(policy.state_dict().keys())}")
        
        # Create a simple policy network for ONNX export
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        class PolicyNet(nn.Module):
            def __init__(self):
                super(PolicyNet, self).__init__()
                self.fc1 = nn.Linear(5, 256)
                self.fc2 = nn.Linear(256, 256)
                self.fc3 = nn.Linear(256, 1)
                self.relu = nn.ReLU()

            def forward(self, x):
                x = self.relu(self.fc1(x))
                x = self.relu(self.fc2(x))
                x = torch.tanh(self.fc3(x))
                return x

        policy_net = PolicyNet().to(device)
        state_dict = policy.state_dict()
        
        # Correct mapping from SAC policy state_dict to our simplified PolicyNet
        policy_net.fc1.weight.data = state_dict['actor.latent_pi.0.weight'].to(device)
        policy_net.fc1.bias.data = state_dict['actor.latent_pi.0.bias'].to(device)
        policy_net.fc2.weight.data = state_dict['actor.latent_pi.2.weight'].to(device)
        policy_net.fc2.bias.data = state_dict['actor.latent_pi.2.bias'].to(device)
        policy_net.fc3.weight.data = state_dict['actor.mu.weight'].to(device)
        policy_net.fc3.bias.data = state_dict['actor.mu.bias'].to(device)
        policy_net.eval()

        # Alternative approach: Force everything to CPU before ONNX export
        # This ensures compatibility even if the original model was on GPU
        try:
            # First approach with device consistency
            dummy_input = torch.randn(1, 5, device=device)
            torch.onnx.export(
                policy_net,
                dummy_input,
                "sac_model.onnx",
                input_names=["input"],
                output_names=["output"],
                opset_version=11
            )
        except Exception as e:
            logger.warning(f"First ONNX export attempt failed: {str(e)}")
            logger.info("Trying alternative approach with CPU-only tensors")
            
            # Move everything to CPU
            policy_net = policy_net.cpu()
            dummy_input = torch.randn(1, 5)
            torch.onnx.export(
                policy_net,
                dummy_input,
                "sac_model.onnx",
                input_names=["input"],
                output_names=["output"],
                opset_version=11
            )
        logger.info("Model has been saved as sac_model.onnx")
    except Exception as e:
        logger.error(f"Error during training: {str(e)}")
        traceback.print_exc()
        sys.exit(1)