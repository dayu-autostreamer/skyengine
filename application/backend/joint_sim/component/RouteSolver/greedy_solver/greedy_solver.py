from joint_sim.component.RouteSolver.route_solver_factory import RouteSolverFactory
from joint_sim.component.RouteSolver.template_solver.route_solver import RouteSolver
import numpy as np


@RouteSolverFactory.register_solver("greedy")
class GreedyRouteSolver(RouteSolver):
    def __init__(self):
        super().__init__()

    def plan(self, obs: list, transfer_requests=None) -> list:
        """
        obs: list[ndarray], 每个元素 shape=(3, H, W)
             channel 0: 障碍物
             channel 1: 其他智能体
             channel 2: 目标位置
        """
        actions = []
        for obs_data in obs:
            H, W = obs_data[0].shape
            obs_radius = H // 2

            # 当前位置固定在局部地图中心
            ax, ay = obs_radius, obs_radius

            # 目标位置从 channel 2 找亮点
            target_map = obs_data[2]
            target_pos = np.argwhere(target_map > 0.5)

            if len(target_pos) == 0:
                # 已到达目标或无目标，停留
                actions.append(0)
                continue

            ty, tx = int(target_pos[0][0]), int(target_pos[0][1])
            actions.append(self._greedy_move((ax, ay), (tx, ty)))

        return actions

    def _greedy_move(self, pos, target) -> int:
        """
        动作编号与 AStar / Pogema 保持一致:
        0=stay, 1=up(-row), 2=down(+row), 3=left(-col), 4=right(+col)
        """
        (x, y) = pos
        (tx, ty) = target
        if tx < x:
            return 1  # up (row 减小)
        elif tx > x:
            return 2  # down (row 增大)
        elif ty < y:
            return 3  # left (col 减小)
        elif ty > y:
            return 4  # right (col 增大)
        else:
            return 0  # stay

    def update_after_step(self, infos):
        pass