'''
@Project ：SkyEngine 
@File    ：route_solver.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 22:50
'''


class RouteSolver:
    def __init__(self):
        """
        RouteSolver 与环境绑定。
        env 通常是 Pogema 式的多智能体网格环境。
        """
        self.pending_transfers = []  # 等待执行的运输任务
        self.active_routes = {}  # agv_id -> 当前路径状态
        self.policy = None  # 可选：内部策略 (如A*或RL)

    def plan(self, obs: dict) -> list:
        """
        核心接口：根据当前环境状态和待搬运任务，输出每个agent的动作。

        输入:
        ------
        obs : dict
            当前环境观测，包含每个AGV的局部视野等信息。
            通常来源于 env.step() 或 env.reset() 返回。
        输出:
        ------
        agent_actions : list[int]
            每个AGV在当前时间步要执行的动作（例如0=stay, 1=up, 2=down, 3=left, 4=right）
            格式直接兼容 Pogema 的输入:
                env.step({'agent_actions': agent_actions, 'machine_actions': machine_actions})
        """
        pass


