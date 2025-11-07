'''
@Project ：tiangong 
@File    ：agent_service.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/18 15:48 
'''


def create_agv_agent(agent_config):
    """
    创建智能体,这些智能体包括宏观job的决策与微观上AGV的决策
    """
    agent_name = agent_config['agent_name']
    if agent_name == 'random':
        from sky_executor.grid_factory.factory.Agent import RandomAgent
        return RandomAgent()
    elif agent_name == 'greedy':
        from sky_executor.grid_factory.factory.Agent.GreedyAgent import GreedyAgent
        return GreedyAgent()
    elif agent_name == 'path_planning':
        from sky_executor.grid_factory.factory.Agent import PathPlanningAgent
        return PathPlanningAgent()
    elif agent_name == 'deterministic_policy':
        from sky_executor.grid_factory.factory.Agent.DeterministicPolicy import DeterministicPolicy
        return DeterministicPolicy()


def create_system_policy(agent_config):
    """
    创建智能体,这些智能体包括宏观job的决策与微观上AGV的决策
    """
    agent_name = agent_config['agent_name']
    if agent_name == 'deterministic_policy':
        from sky_executor.grid_factory.factory.Agent.DeterministicPolicy import SystemDeterministicPolicy
        return SystemDeterministicPolicy()
