"""
随机移动智能体
"""

import random
from typing import Dict, Any

from sky_executor.grid_factory.factory.Agent.GridAgent import GridAgent
from sky_executor.utils.registry import register_component


@register_component("factory.RandomAgent")
class RandomAgent(GridAgent):
    """
    随机移动智能体
    
    功能特性:
    1. 完全随机移动
    2. 不考虑目标位置
    3. 适合探索环境
    """
    
    def __init__(self, name=None, agent_id=None, parameter: dict = None):
        """
        初始化随机智能体
        
        Args:
            name: 智能体名称
            agent_id: 智能体ID
            parameter: 参数配置
        """
        # 设置默认参数
        default_params = {
            "movement_strategy": "random",
            "exploration_rate": 1.0,  # 完全随机
            "path_planning_enabled": False,
            "obstacle_avoidance": True
        }
        
        if parameter:
            default_params.update(parameter)
        
        super().__init__(name, agent_id, default_params)
        
        # 随机移动参数
        self.random_walk_probability = parameter.get("random_walk_probability", 0.8) if parameter else 0.8
        self.wait_probability = parameter.get("wait_probability", 0.2) if parameter else 0.2
    
    def sample(self, observations=None, **kwargs):
        """随机动作采样"""
        # 根据概率决定是否等待
        if random.random() < self.wait_probability:
            return 0  # 等待
        
        # 随机选择移动动作
        available_actions = self.get_available_actions()
        if len(available_actions) > 1:  # 除了等待动作还有其他动作
            return random.choice(available_actions[1:])  # 排除等待动作
        else:
            return 0  # 只能等待
    
    def reward(self, observations=None, **kwargs):
        """计算奖励（随机智能体奖励较低）"""
        reward = 0.0
        
        # 基础存活奖励
        reward += 1.0
        
        # 碰撞惩罚
        if not self._is_valid_position(self.current_position):
            reward -= 10.0
        
        # 停滞惩罚（随机智能体允许更多停滞）
        if len(self.position_history) > 3 and self.position_history[-1] == self.position_history[-3]:
            reward -= 0.5
        
        return reward
    
    def is_finish(self, observations=None, **kwargs):
        """随机智能体没有明确的完成条件"""
        return False
    
    def get_state_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        info = super().get_state_info()
        info.update({
            'random_walk_probability': self.random_walk_probability,
            'wait_probability': self.wait_probability,
            'strategy': 'random'
        })
        return info
