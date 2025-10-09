"""
智能体工厂类
"""

from typing import Dict, Any, Optional, Type
from sky_simulator.registry import register_component
from sky_simulator.environment.grid_factory.Agent.GridAgent import GridAgent
from sky_simulator.environment.grid_factory.Agent.RandomAgent import RandomAgent
from sky_simulator.environment.grid_factory.Agent.GreedyAgent import GreedyAgent
from sky_simulator.environment.grid_factory.Agent.PathPlanningAgent import PathPlanningAgent
from sky_logs.logger import LOGGER


@register_component("grid_factory.AgentFactory")
class AgentFactory:
    """
    智能体工厂类
    
    功能特性:
    1. 创建不同类型的智能体
    2. 管理智能体配置
    3. 支持自定义智能体类型
    4. 提供智能体注册和发现
    """
    
    # 注册的智能体类型
    _agent_types = {
        'random': RandomAgent,
        'greedy': GreedyAgent,
        'path_planning': PathPlanningAgent,
    }
    
    @classmethod
    def create_agent(cls, agent_type: str, name: str = None, agent_id: str = None, 
                    parameter: Dict[str, Any] = None) -> GridAgent:
        """
        创建智能体
        
        Args:
            agent_type: 智能体类型
            name: 智能体名称
            agent_id: 智能体ID
            parameter: 参数配置
            
        Returns:
            GridAgent: 创建的智能体实例
        """
        if agent_type not in cls._agent_types:
            raise ValueError(f"未知的智能体类型: {agent_type}")
        
        agent_class = cls._agent_types[agent_type]
        
        try:
            agent = agent_class(name=name, agent_id=agent_id, parameter=parameter)
            LOGGER.info(f"[AgentFactory] 创建智能体: {agent_type} - {name}")
            return agent
        except Exception as e:
            LOGGER.error(f"[AgentFactory] 创建智能体失败: {e}")
            raise
    
    @classmethod
    def register_agent_type(cls, agent_type: str, agent_class: Type[GridAgent]):
        """
        注册新的智能体类型
        
        Args:
            agent_type: 智能体类型名称
            agent_class: 智能体类
        """
        if not issubclass(agent_class, GridAgent):
            raise ValueError("智能体类必须继承自GridAgent")
        
        cls._agent_types[agent_type] = agent_class
        LOGGER.info(f"[AgentFactory] 注册智能体类型: {agent_type}")
    
    @classmethod
    def get_available_agent_types(cls) -> list:
        """获取可用的智能体类型"""
        return list(cls._agent_types.keys())
    
    @classmethod
    def create_agent_batch(cls, agent_configs: list) -> list:
        """
        批量创建智能体
        
        Args:
            agent_configs: 智能体配置列表
            
        Returns:
            list: 智能体实例列表
        """
        agents = []
        
        for config in agent_configs:
            agent_type = config.get('type', 'random')
            name = config.get('name', f"Agent_{len(agents)}")
            agent_id = config.get('id', f"agent_{len(agents)}")
            parameter = config.get('parameter', {})
            
            agent = cls.create_agent(
                agent_type=agent_type,
                name=name,
                agent_id=agent_id,
                parameter=parameter
            )
            agents.append(agent)
        
        LOGGER.info(f"[AgentFactory] 批量创建了 {len(agents)} 个智能体")
        return agents
    
    @classmethod
    def create_default_agents(cls, num_agents: int = 5, agent_types: list = None) -> list:
        """
        创建默认智能体集合
        
        Args:
            num_agents: 智能体数量
            agent_types: 智能体类型列表
            
        Returns:
            list: 智能体实例列表
        """
        if agent_types is None:
            agent_types = ['random', 'greedy', 'path_planning']
        
        agents = []
        for i in range(num_agents):
            agent_type = agent_types[i % len(agent_types)]
            name = f"{agent_type}_agent_{i}"
            agent_id = f"agent_{i}"
            
            # 为不同类型的智能体设置不同参数
            parameter = cls._get_default_parameters(agent_type, i)
            
            agent = cls.create_agent(
                agent_type=agent_type,
                name=name,
                agent_id=agent_id,
                parameter=parameter
            )
            agents.append(agent)
        
        LOGGER.info(f"[AgentFactory] 创建了 {len(agents)} 个默认智能体")
        return agents
    
    @classmethod
    def _get_default_parameters(cls, agent_type: str, agent_index: int) -> Dict[str, Any]:
        """获取默认参数"""
        base_params = {
            'step_times': 100,
            'learning_rate': 0.01,
            'max_turns': 1000,
            'device': 'cpu',
            'seed': 42 + agent_index
        }
        
        if agent_type == 'random':
            base_params.update({
                'random_walk_probability': 0.8,
                'wait_probability': 0.2
            })
        elif agent_type == 'greedy':
            base_params.update({
                'greedy_factor': 0.9,
                'exploration_rate': 0.1,
                'exploration_decay': 0.995,
                'min_exploration_rate': 0.01
            })
        elif agent_type == 'path_planning':
            base_params.update({
                'replan_threshold': 0.1,
                'path_deviation_tolerance': 2,
                'dynamic_replanning': True
            })
        
        return base_params
    
    @classmethod
    def get_agent_info(cls, agent_type: str) -> Dict[str, Any]:
        """获取智能体信息"""
        if agent_type not in cls._agent_types:
            return {}
        
        agent_class = cls._agent_types[agent_type]
        
        return {
            'type': agent_type,
            'class': agent_class.__name__,
            'module': agent_class.__module__,
            'description': getattr(agent_class, '__doc__', ''),
            'default_parameters': cls._get_default_parameters(agent_type, 0)
        }
    
    @classmethod
    def list_agent_types(cls) -> Dict[str, Dict[str, Any]]:
        """列出所有智能体类型信息"""
        agent_info = {}
        for agent_type in cls._agent_types:
            agent_info[agent_type] = cls.get_agent_info(agent_type)
        return agent_info
