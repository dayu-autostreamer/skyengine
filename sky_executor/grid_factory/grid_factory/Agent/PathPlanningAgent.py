"""
路径规划智能体
"""

from typing import Dict, Any

from sky_executor.grid_factory.grid_factory.Agent.GridAgent import GridAgent
from sky_executor.utils.registry import register_component


@register_component("grid_factory.PathPlanningAgent")
class PathPlanningAgent(GridAgent):
    """
    路径规划智能体
    
    功能特性:
    1. 使用A*算法进行路径规划
    2. 跟随规划好的路径移动
    3. 支持动态重新规划
    4. 支持避障和碰撞检测
    """
    
    def __init__(self, name=None, agent_id=None, parameter: dict = None):
        """
        初始化路径规划智能体
        
        Args:
            name: 智能体名称
            agent_id: 智能体ID
            parameter: 参数配置
        """
        # 设置默认参数
        default_params = {
            "movement_strategy": "path_following",
            "exploration_rate": 0.05,  # 5%探索
            "path_planning_enabled": True,
            "obstacle_avoidance": True
        }
        
        if parameter:
            default_params.update(parameter)
        
        super().__init__(name, agent_id, default_params)
        
        # 路径规划参数
        self.replan_threshold = parameter.get("replan_threshold", 0.1) if parameter else 0.1
        self.path_deviation_tolerance = parameter.get("path_deviation_tolerance", 2) if parameter else 2
        self.dynamic_replanning = parameter.get("dynamic_replanning", True) if parameter else True
        
        # 路径规划状态
        self.last_plan_time = 0
        self.path_following_errors = 0
        self.replan_count = 0
    
    def sample(self, observations=None, **kwargs):
        """路径规划动作采样"""
        # 检查是否需要重新规划
        if self._should_replan():
            self._plan_path()
        
        # 路径跟随
        if self.path and self.path_index < len(self.path):
            return self._path_following_action()
        else:
            # 如果没有路径，使用贪心策略
            return self._greedy_action()
    
    def _should_replan(self) -> bool:
        """判断是否需要重新规划路径"""
        if not self.dynamic_replanning:
            return False
        
        # 检查是否偏离路径
        if self.path and self.path_index < len(self.path):
            expected_pos = self.path[self.path_index]
            if self.current_position != expected_pos:
                self.path_following_errors += 1
                if self.path_following_errors > self.path_deviation_tolerance:
                    return True
        
        # 检查目标是否改变
        if self.target_position and hasattr(self, '_last_target'):
            if self.target_position != self._last_target:
                return True
        
        return False
    
    def _path_following_action(self) -> int:
        """路径跟随动作"""
        if not self.path or self.path_index >= len(self.path):
            return 0  # 等待
        
        target_pos = self.path[self.path_index]
        
        # 如果已经到达路径点，移动到下一个
        if self.current_position == target_pos:
            self.path_index += 1
            if self.path_index < len(self.path):
                target_pos = self.path[self.path_index]
            else:
                return 0  # 路径完成，等待
        
        # 找到朝向目标位置的动作
        for action in range(1, 5):
            next_pos = self._get_next_position(self.current_position, action)
            if next_pos == target_pos:
                return action
        
        # 如果找不到直接动作，使用贪心策略
        return self._greedy_action()
    
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
    
    def _plan_path(self):
        """路径规划"""
        if not self.target_position:
            return
        
        # 记录规划时间
        self.last_plan_time = time.time()
        self._last_target = self.target_position
        
        # 使用A*算法规划路径
        self.path = self._a_star_pathfinding(self.current_position, self.target_position)
        self.path_index = 0
        self.path_following_errors = 0
        self.replan_count += 1
        
        LOGGER.debug(f"[PathPlanningAgent] 重新规划路径，路径长度: {len(self.path)}")
    
    def reward(self, observations=None, **kwargs):
        """计算奖励"""
        reward = 0.0
        
        # 目标奖励
        if self.target_position and self.current_position == self.target_position:
            reward += 100.0
        
        # 路径跟随奖励
        if self.path and self.path_index < len(self.path):
            expected_pos = self.path[self.path_index]
            if self.current_position == expected_pos:
                reward += 5.0  # 正确跟随路径
            else:
                reward -= 2.0  # 偏离路径惩罚
        
        # 距离奖励
        if self.target_position:
            current_distance = self._heuristic(self.current_position, self.target_position)
            reward -= current_distance * 0.1
        
        # 碰撞惩罚
        if not self._is_valid_position(self.current_position):
            reward -= 10.0
        
        # 停滞惩罚
        if len(self.position_history) > 1 and self.position_history[-1] == self.position_history[-2]:
            reward -= 1.0
        
        # 重新规划惩罚（鼓励一次性规划成功）
        if self.replan_count > 0:
            reward -= self.replan_count * 0.5
        
        return reward
    
    def is_finish(self, observations=None, **kwargs):
        """判断任务是否完成"""
        if self.target_position:
            return self.current_position == self.target_position
        return False
    
    def get_state_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        info = super().get_state_info()
        info.update({
            'replan_threshold': self.replan_threshold,
            'path_deviation_tolerance': self.path_deviation_tolerance,
            'dynamic_replanning': self.dynamic_replanning,
            'path_following_errors': self.path_following_errors,
            'replan_count': self.replan_count,
            'strategy': 'path_planning'
        })
        return info
