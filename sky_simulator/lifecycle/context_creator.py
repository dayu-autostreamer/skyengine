'''
@Project ：tiangong 
@File    ：context_creator.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 1:28 
'''
from sky_simulator.call_back.callback_manager.CallbackManager import CallbackManager
from sky_simulator.registry.factory import create_component_by_id, get_component_class_by_id
from sky_simulator.registry.registry import component_registry


def initialize_agent(config):
    agent_config = config.get(config.get("env_type")).get("agent")
    agent = create_component_by_id(agent_config.get("agent_name"), agent_config.get("name"), agent_config.get("id"))
    return agent


def initialize_env(config, agent):
    """
    寻找环境中预留的各个回调,并根据config进行插入替换、
    """

    env_type = config.get("env_type")
    if not env_type:
        raise ValueError("[Context] 配置中未指定 'env_type'，请检查配置文件")

    if env_type == "simulation":
        env_name = config.get(env_type).get("env_name")
        env = create_component_by_id(env_name, agent, )
    elif env_type == "real":
        env_name = config.get(env_type).get("env_name")
        env = create_component_by_id(env_name, agent)
    else:
        raise ValueError(f"[Context] 未知环境类型: {env_type}")

    callback_config = config.get(env_type).get('callback').get('map_callback')

    # ---------- 创建回调管理器 ----------
    callback_manager = CallbackManager()
    callback_manager.register("load_graph", create_component_by_id(callback_config.get('graph_loader').get('name'),
                                                                   callback_config.get('graph_loader').get('args')))
    callback_manager.register("initialize_visualizer",
                              create_component_by_id(callback_config.get('visualizer').get('name'),
                                                     callback_config.get('visualizer').get('args')))

    env.set_callback_manager(callback_manager)
    print(f"[Callback] 添加至 load_graph 环境上下文...")

    return env


def initialize_visualizer(config, env):
    visualizer_config = config.get(config.get("env_type")).get("visualizer")
    visualizer = create_component_by_id(visualizer_config.get("visualizer_name"), env, visualizer_config.get("fps"))
    return visualizer


def create_context():
    '''
    创建环境并整合组件
    '''
    print(f"[Context] 创建'环境,智能体,可视化器'等上下文...")

    config = component_registry.get('config')

    assert isinstance(config, dict) and config is not None

    # ---------- 智能体创建 ----------
    # 初始化智能体相关的回调
    agent = initialize_agent(config)

    # ---------- 环境创建 ----------
    # 初始化环境本身的文件（例如地图、数据源等）
    env = initialize_env(config, agent)

    print(f"[Context] 环境上下文创建完成! ")
    return env, agent
