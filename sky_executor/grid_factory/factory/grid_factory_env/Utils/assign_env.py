from pogema.envs import PogemaLifeLong, GridConfig
import random
from typing import Optional


class PogemaLifeLongWithAssign(PogemaLifeLong):
    def __init__(self, grid_config=GridConfig(num_agents=2), assigner=None):
        super().__init__(grid_config)
        self.assigner = assigner
        self.machines = []
        self.activated_machines = []

    def reset(
        self,
        seed: Optional[int] = None,
        return_info: bool = True,
        options: Optional[dict] = None,
    ):
        super().reset(seed, return_info, options)
        # 重新分配可能的目标
        for idx in range(self.grid_config.num_agents):
            self.grid.finishes_xy[idx] = random.choice(
                self.grid_config.possible_targets_xy
            )
        if return_info:
            return self._obs(), self._get_infos()
        return self._obs()

    # def assign_new_target(self, agent_idx, assigner_obs):
    #     """调用分配器获取新目标"""
    #     pending_transfers = assigner_obs.get("pending_transfers", {})
    #     available_machine_list = assigner_obs.get("available_machine_list", [])
    #     if self.assigner is not None:
    #         return self.assigner.assign(
    #             agent_idx, pending_transfers, available_machine_list
    #         )
    #     else:
    #         # fallback: 默认随机分配空闲点
    #         return random.choice(self.grid_config.possible_targets_xy)

    def task_step(self, action: dict):
        """处理任务层"""
        rewards = []
        infos = [dict() for _ in range(self.grid_config.num_agents)]

        for agent_idx in range(self.grid_config.num_agents):
            on_goal = self.grid.on_goal(agent_idx)
            active = self.grid.is_active[agent_idx]

            if on_goal and active:
                rewards.append(1.0)
                # 更新当前任务完成状态

                # 根据assigner指定的动作给agv分配target
                self.grid.finishes_xy[agent_idx] = action.get(agent_idx, None)

            else:
                rewards.append(0.0)

            infos[agent_idx]["is_active"] = self.grid.is_active[agent_idx]

        # 返回需要的观察信息,包括machine,agv当前状态,当前任务状态等
        obs = None
        terminated = [False] * self.grid_config.num_agents
        truncated = [False] * self.grid_config.num_agents
        return obs, rewards, terminated, truncated, infos

    def step(self, action: list):
        """移动小车"""
        rewards = []

        infos = [dict() for _ in range(self.grid_config.num_agents)]

        # 移动agents
        self.move_agents(action)

        # 将分配下一次目标的决策放到后续执行

        # 返回需要的观察信息,也就是正常的pogema信息
        obs = self._obs()

        terminated = [False] * self.grid_config.num_agents
        truncated = [False] * self.grid_config.num_agents
        return obs, rewards, terminated, truncated, infos
