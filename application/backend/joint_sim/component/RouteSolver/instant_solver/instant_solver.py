'''
@Project ：SkyEngine 
@File    ：greedy_solver.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 23:06
'''

# 能够立刻完成路由任务

from joint_sim.component.RouteSolver.route_solver_factory import \
    RouteSolverFactory
from joint_sim.component.RouteSolver.template_solver.route_solver import \
    RouteSolver
@RouteSolverFactory.register_solver("instant")
class GreedyRouteSolver(RouteSolver):
    def __init__(self, env):
        super().__init__(env)
        self.env = env
        self.transfer_targets = {}  # agv_id -> target position

    def plan(self, obs, transfer_requests):
        agent_actions = []
        agent_obs = obs.get("agent_observation", [])
        positions = obs.get("positions", [])

        # 1️⃣ 为空闲AGV分配任务
        for agv_id, pos in enumerate(positions):
            if agv_id not in self.transfer_targets or self._reached_target(pos, self.transfer_targets[agv_id]):
                # 若该AGV空闲且有待分配任务
                if transfer_requests:
                    req = transfer_requests.pop(0)
                    target = self.env.machine_positions[req['to_machine']]
                    self.transfer_targets[agv_id] = target
                else:
                    self.transfer_targets[agv_id] = None

        # 2️⃣ 基于目标生成贪心动作
        for agv_id, pos in enumerate(positions):
            target = self.transfer_targets.get(agv_id)
            if target is None:
                action = 0  # stay
            else:
                action = self._greedy_move(pos, target)
            agent_actions.append(action)

        return agent_actions

    def _greedy_move(self, pos, target):
        (x, y) = pos
        (tx, ty) = target
        if tx > x:
            return 1  # up
        elif tx < x:
            return 2  # down
        elif ty > y:
            return 4  # right
        elif ty < y:
            return 3  # left
        else:
            return 0  # stay

    def _reached_target(self, pos, target):
        return pos == target

    def update_after_step(self, infos):
        # 更新转运完成状态
        pass
