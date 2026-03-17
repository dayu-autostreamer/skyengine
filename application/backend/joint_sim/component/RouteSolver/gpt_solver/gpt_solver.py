import numpy as np
from joint_sim.component.RouteSolver.route_solver_factory import RouteSolverFactory
from joint_sim.component.RouteSolver.template_solver.route_solver import RouteSolver
from joint_sim.component.RouteSolver.gpt_solver.gpt_models.gpt.inference import (
    MAPFGPTInference,
    MAPFGPTInferenceConfig,
)


@RouteSolverFactory.register_solver("mapf_gpt")
class MAPFGPTRouteSolver(RouteSolver):
    def __init__(self, model_path="weights/model-6M.pt", device="cuda"):
        super().__init__()
        cfg = MAPFGPTInferenceConfig(path_to_weights=model_path, device=device)
        self.gpt_inference = MAPFGPTInference(cfg)
        self.device = device

    def plan(self, obs: list, transfer_requests=None) -> list:
        """
        obs: list[ndarray], 每个元素 shape=(3, H, W)
             channel 0: 障碍物
             channel 1: 其他智能体
             channel 2: 目标位置
        """
        converted_obs = self._convert_observations(obs)
        actions = self.gpt_inference.act(converted_obs)
        return self._adapt_actions(actions)

    def _convert_observations(self, obs: list) -> list:
        """
        对齐 AStarRouteSolver 的 obs 格式：
        list[ndarray(3, H, W)] → list[dict] (MAPF-GPT 需要的格式)
        """
        converted = []
        for obs_data in obs:
            # obs_data shape: (3, H, W)
            obstacle_map  = obs_data[0]  # (H, W) 障碍物
            agent_map     = obs_data[1]  # (H, W) 其他智能体（可选用）
            target_map    = obs_data[2]  # (H, W) 目标

            H, W = obstacle_map.shape
            obs_radius = H // 2

            # 当前智能体始终在局部地图中心，与 AStar 保持一致
            ax, ay = obs_radius, obs_radius

            # 目标坐标：从 channel 2 找亮点
            target_pos = np.argwhere(target_map > 0.5)
            if len(target_pos) > 0:
                ty, tx = int(target_pos[0][0]), int(target_pos[0][1])
            else:
                # 已到达目标或目标不可见，停在原地
                ty, tx = ay, ax

            converted.append({
                "global_xy":        (ax, ay),
                "global_target_xy": (tx, ty),
                "global_obstacles": obstacle_map.astype(int).tolist(),
            })
        return converted

    def _adapt_actions(self, actions) -> list:
        return [int(a) for a in actions]

    def reset(self):
        self.gpt_inference.reset_states()
        super().reset()