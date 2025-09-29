"""
Grid Factory AGV智能体实现
"""

import random
from typing import List, Tuple, Dict, Any
from sky_executor.grid_factory.factory.Agent.BaseAgent import GridBaseAgent


class GridAgent(GridBaseAgent):

    def __init__(self, name=None, agent_id=None, parameter: dict = None):
        """
        初始化AGV智能体
        
        Args:
            name: 智能体名称
            agent_id: 智能体ID
            parameter: 参数配置
        """
        super().__init__(name, agent_id, parameter)

        # AGV状态
        self.current_position = (0, 0)
        self.target_position = None
        self.path = []
        self.path_index = 0

        # 移动策略
        self.movement_strategy = parameter.get("movement_strategy", "random")
        self.exploration_rate = parameter.get("exploration_rate", 0.1)

        # 路径规划参数
        self.path_planning_enabled = parameter.get("path_planning_enabled", True)
        self.obstacle_avoidance = parameter.get("obstacle_avoidance", True)

        # 历史记录
        self.position_history = []
        self.action_history = []
        self.reward_history = []

        # 环境信息
        self.grid_size = None
        self.obstacles = set()
        self.other_agents = set()

    def set_position(self, position: Tuple[int, int]):
        """设置当前位置"""
        self.current_position = position
        self.position_history.append(position)

    def set_target(self, target: Tuple[int, int]):
        """设置目标位置"""
        self.target_position = target
        if self.path_planning_enabled:
            self._plan_path()

    def set_environment_info(self, grid_size: Tuple[int, int], obstacles: set = None):
        """设置环境信息"""
        self.grid_size = grid_size
        self.obstacles = obstacles or set()

    def _plan_path(self):
        """路径规划"""
        if not self.target_position or not self.path_planning_enabled:
            return

        # 简单的A*路径规划
        self.path = self._a_star_pathfinding(self.current_position, self.target_position)
        self.path_index = 0

    def _a_star_pathfinding(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """A*路径规划算法"""
        if start == goal:
            return [start]

        # 开放列表和关闭列表
        open_list = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self._heuristic(start, goal)}

        while open_list:
            current = min(open_list, key=lambda x: x[0])[1]
            open_list.remove((f_score[current], current))

            if current == goal:
                # 重构路径
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            # 探索邻居
            for action in range(1, 5):  # 跳过等待动作
                neighbor = self._get_next_position(current, action)
                if self._is_valid_position(neighbor):
                    tentative_g_score = g_score[current] + 1

                    if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g_score
                        f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, goal)

                        if neighbor not in [pos for _, pos in open_list]:
                            open_list.append((f_score[neighbor], neighbor))

        # 如果找不到路径，返回空路径
        return []

    def _heuristic(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """启发式函数（曼哈顿距离）"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _get_next_position(self, position: Tuple[int, int], action: int) -> Tuple[int, int]:
        """根据动作获取下一个位置"""
        if action not in self.ACTION_VECTORS:
            return position

        dx, dy = self.ACTION_VECTORS[action]
        return (position[0] + dx, position[1] + dy)

    def _is_valid_position(self, position: Tuple[int, int]) -> bool:
        """检查位置是否有效"""
        if not self.grid_size:
            return True

        x, y = position
        if x < 0 or x >= self.grid_size[0] or y < 0 or y >= self.grid_size[1]:
            return False

        if position in self.obstacles:
            return False

        return True

    def sample(self, observations=None, **kwargs):
        """智能体推理采样"""
        if self.movement_strategy == "random":
            return self._random_action()
        elif self.movement_strategy == "greedy":
            return self._greedy_action()
        elif self.movement_strategy == "path_following":
            return self._path_following_action()
        elif self.movement_strategy == "exploration":
            return self._exploration_action()
        else:
            return self._random_action()

    def _random_action(self) -> int:
        """随机动作"""
        return random.randint(0, 4)

    def _greedy_action(self) -> int:
        """贪心动作（朝向目标移动）"""
        if not self.target_position:
            return 0  # 等待

        best_action = 0
        best_distance = float('inf')

        for action in range(1, 5):  # 跳过等待动作
            next_pos = self._get_next_position(self.current_position, action)
            if self._is_valid_position(next_pos):
                distance = self._heuristic(next_pos, self.target_position)
                if distance < best_distance:
                    best_distance = distance
                    best_action = action

        return best_action

    def _path_following_action(self) -> int:
        """路径跟随动作"""
        if not self.path or self.path_index >= len(self.path):
            return 0  # 等待

        target_pos = self.path[self.path_index]

        # 找到朝向目标位置的动作
        for action in range(1, 5):
            next_pos = self._get_next_position(self.current_position, action)
            if next_pos == target_pos:
                self.path_index += 1
                return action

        return 0  # 等待

    def _exploration_action(self) -> int:
        """探索动作（结合贪心和随机）"""
        if random.random() < self.exploration_rate:
            return self._random_action()
        else:
            return self._greedy_action()

    def reward(self, observations=None, **kwargs):
        """计算奖励"""
        reward = 0.0

        # 目标奖励
        if self.target_position and self.current_position == self.target_position:
            reward += 100.0

        # 距离奖励（负距离）
        if self.target_position:
            distance = self._heuristic(self.current_position, self.target_position)
            reward -= distance * 0.1

        # 碰撞惩罚
        if not self._is_valid_position(self.current_position):
            reward -= 10.0

        # 停滞惩罚
        if len(self.position_history) > 1 and self.position_history[-1] == self.position_history[-2]:
            reward -= 1.0

        return reward

    def is_finish(self, observations=None, **kwargs):
        """判断任务是否完成"""
        if self.target_position:
            return self.current_position == self.target_position
        return False

    def before_sample(self, observations=None, **kwargs):
        """采样前处理"""
        pass

    def after_sample(self, observations=None, **kwargs):
        """采样后处理"""
        pass

    def before_train(self, **kwargs):
        """训练前处理"""
        pass

    def after_train(self, **kwargs):
        """训练后处理"""
        pass

    def train(self, **kwargs):
        """训练（基础版本为空实现）"""
        pass

    def update_position(self, new_position: Tuple[int, int]):
        """更新位置"""
        self.current_position = new_position
        self.position_history.append(new_position)

    def get_action_vector(self, action: int) -> Tuple[int, int]:
        """获取动作向量"""
        return self.ACTION_VECTORS.get(action, (0, 0))

    def get_available_actions(self) -> List[int]:
        """获取可用动作"""
        available_actions = [0]  # 等待动作总是可用

        for action in range(1, 5):
            next_pos = self._get_next_position(self.current_position, action)
            if self._is_valid_position(next_pos):
                available_actions.append(action)

        return available_actions

    def get_state_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            'position': self.current_position,
            'target': self.target_position,
            'path_length': len(self.path),
            'path_index': self.path_index,
            'strategy': self.movement_strategy,
            'exploration_rate': self.exploration_rate,
            'position_history_length': len(self.position_history),
            'action_history_length': len(self.action_history)
        }

    def reset(self):
        """重置智能体状态"""
        self.current_position = (0, 0)
        self.target_position = None
        self.path = []
        self.path_index = 0
        self.position_history = []
        self.action_history = []
        self.reward_history = []
        self.turns = 0
        self.alive = True

    def __repr__(self):
        return f"<GridAgent id={self.agent_id} pos={self.current_position} target={self.target_position}>"
