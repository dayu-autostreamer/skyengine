'''
@Project ：tiangong 
@File    ：context_creator.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 1:28 
'''
from sky_simulator.call_back.callback_manager.CallbackManager import CallbackManager
from sky_simulator.registry.factory import create_component_by_id
from sky_simulator.registry.registry import component_registry
from sky_simulator.lifecycle.initializer.env_initializer import initialize_env
from sky_simulator.lifecycle.initializer.agent_initializer import initialize_agent

def create_context():
    '''
    创建环境并整合组件
    '''
    print(f"[Context] Creating 'Env,Agent'...")

    config = component_registry.get('config')

    assert isinstance(config, dict) and config is not None

    # ---------- 智能体创建 ----------
    # 初始化智能体相关的回调
    agent = initialize_agent(config)

    # ---------- 环境创建 ----------
    # 初始化环境本身的文件（例如地图、数据源等）
    env = initialize_env(config, agent)

    print(f"[Context] Created.")
    return env, agent
