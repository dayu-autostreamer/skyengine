from pogema.envs import PogemaLifeLong, GridConfig
import random
from typing import Optional


class PogemaLifeLongWithAssign(PogemaLifeLong):
    def __init__(self, grid_config=GridConfig(num_agents=2), assigner=None):
        super().__init__(grid_config)
        self.num_agents = self.grid_config.num_agents
        self.is_multiagent = True
        self.assigner = assigner

    def reset(self, seed: Optional[int] = None, return_info: bool = True, options: Optional[dict] = None, ):
        super().reset(seed, return_info, options)
        for idx in range(self.grid_config.num_agents):
            self.grid.finishes_xy[idx] = random.choice(self.grid_config.possible_targets_xy)
        if return_info:
            return self._obs(), self._get_infos()
        return self._obs()

    def assign_new_target(self, agent_idx):
        """调用分配器获取新目标"""
        if self.assigner is not None:
            return self.assigner.assign(agent_idx, grid=self.grid)
        else:
            # fallback: 默认随机分配空闲点
            return random.choice(self.grid_config.possible_targets_xy)

    def step(self, action: list):
        assert len(action) == self.grid_config.num_agents
        rewards = []

        infos = [dict() for _ in range(self.grid_config.num_agents)]

        self.move_agents(action)
        self.update_was_on_goal()

        for agent_idx in range(self.grid_config.num_agents):
            on_goal = self.grid.on_goal(agent_idx)
            active = self.grid.is_active[agent_idx]

            if on_goal and active:
                rewards.append(1.0)
                self.grid.finishes_xy[agent_idx] = self.assign_new_target(agent_idx)
            else:
                rewards.append(0.0)

            infos[agent_idx]["is_active"] = self.grid.is_active[agent_idx]

        obs = self._obs()

        terminated = [False] * self.grid_config.num_agents
        truncated = [False] * self.grid_config.num_agents
        return obs, rewards, terminated, truncated, infos
