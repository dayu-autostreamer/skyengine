"""
贪心移动智能体
"""

import random
from typing import Dict, Any

from sky_executor.grid_factory.factory.Agent.GridAgent import GridAgent
from sky_executor.utils.registry import register_component


@register_component("factory.GreedyAgent")
class GreedyAgent(GridAgent):
    """
    贪心移动智能体
    
    功能特性:
    1. 总是朝向目标移动
    2. 选择距离目标最近的动作
    3. 支持探索和利用平衡
    """
    
    def __init__(self, name=None, agent_id=None, parameter: dict = None):
        """
        初始化贪心智能体
        
        Args:
            name: 智能体名称
            agent_id: 智能体ID
            parameter: 参数配置
        """
        # 设置默认参数
        default_params = {
            "movement_strategy": "greedy",
            "exploration_rate": 0.1,  # 10%探索
            "path_planning_enabled": False,
            "obstacle_avoidance": True
        }
        
        if parameter:
            default_params.update(parameter)
        
        super().__init__(name, agent_id, default_params)
        
        # 贪心移动参数
        self.greedy_factor = parameter.get("greedy_factor", 0.9) if parameter else 0.9
        self.exploration_decay = parameter.get("exploration_decay", 0.995) if parameter else 0.995
        self.min_exploration_rate = parameter.get("min_exploration_rate", 0.01) if parameter else 0.01
    
    def sample(self, observations=None, **kwargs):
        """贪心动作采样"""
        # 探索vs利用
        if random.random() < self.exploration_rate:
            return self._random_action()
        else:
            return self._greedy_action()
    
    def _greedy_action(self) -> int:
        """贪心动作（朝向目标移动）"""
        if not self.target_position:
            return 0  # 等待
        
        best_action = 0
        best_distance = float('inf')
        
        # 评估所有可能的动作
        for action in range(1, 5):  # 跳过等待动作
            next_pos = self._get_next_position(self.current_position, action)
            if self._is_valid_position(next_pos):
                distance = self._heuristic(next_pos, self.target_position)
                if distance < best_distance:
                    best_distance = distance
                    best_action = action
        
        return best_action
    
    def _random_action(self) -> int:
        """随机动作（探索）"""
        available_actions = self.get_available_actions()
        if len(available_actions) > 1:
            return random.choice(available_actions[1:])  # 排除等待动作
        else:
            return 0  # 只能等待
    
    def reward(self, observations=None, **kwargs):
        """计算奖励"""
        reward = 0.0
        
        # 目标奖励
        if self.target_position and self.current_position == self.target_position:
            reward += 100.0
        
        # 距离奖励（负距离，鼓励接近目标）
        if self.target_position:
            current_distance = self._heuristic(self.current_position, self.target_position)
            reward -= current_distance * 0.1
            
            # 距离改善奖励
            if len(self.position_history) > 1:
                prev_distance = self._heuristic(self.position_history[-2], self.target_position)
                if current_distance < prev_distance:
                    reward += 5.0  # 距离改善奖励
                elif current_distance > prev_distance:
                    reward -= 2.0  # 距离恶化惩罚
        
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
    
    def after_sample(self, observations=None, **kwargs):
        """采样后处理（更新探索率）"""
        # 衰减探索率
        self.exploration_rate = max(
            self.min_exploration_rate,
            self.exploration_rate * self.exploration_decay
        )
    
    def get_state_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        info = super().get_state_info()
        info.update({
            'greedy_factor': self.greedy_factor,
            'exploration_rate': self.exploration_rate,
            'exploration_decay': self.exploration_decay,
            'min_exploration_rate': self.min_exploration_rate,
            'strategy': 'greedy'
        })
        return info
