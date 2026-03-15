'''
@Project ：tiangong 
@File    ：context_creator.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 1:28 
'''
from executor.packet_factory.registry.registry import component_registry
from executor.packet_factory.lifecycle.initializer.env_initializer import initialize_env
from executor.packet_factory.lifecycle.initializer.agent_initializer import initialize_agent
from executor.packet_factory.logger.logger import LOGGER


def create_context():
    '''
    创建环境并整合组件
    '''
    LOGGER.info(f"[Context] Creating 'Env,Agent'...")

    config = component_registry.get('config')

    assert isinstance(config, dict) and config is not None

    # ---------- 智能体创建 ----------
    # 初始化智能体相关的回调
    agent = initialize_agent(config)

    # ---------- 环境创建 ----------
    # 初始化环境本身的文件（例如地图、数据源等）
    env = initialize_env(config, agent)

    LOGGER.info(f"[Context] Created.")
    return env, agent
