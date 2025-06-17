'''
@Project ：tiangong 
@File    ：context_creator.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 1:28 
'''
from sky_simulator.registry.factory import create_component_by_id
from sky_simulator.registry.registry import component_registry
def create_context():
    '''
    创建环境并整合组件
    '''
    config= component_registry.get_component('config')

    assert isinstance(config,dict) and config is not None
    env_type = config.get("env_type")
    if not env_type:
        raise ValueError("[Context] 配置中未指定 'env_type'，请检查配置文件")

    print(f"[Context] 创建 {env_type} 环境上下文...")

    if env_type == "simulation":
        env_name= config.get(env_type).get("env_name")
        env = create_component_by_id(env_name)
    elif env_type == "real":
        env_name= config.get(env_type).get("env_name")
        env = create_component_by_id(env_name)
    else:
        raise ValueError(f"[Context] 未知环境类型: {env_type}")

    # 初始化常规配置
    common_config=config.get("common")
    env.setcommon(common_config)

    # 初始化环境本身（例如地图、数据源等）
    env.initialize()

    # 创建并装配所有组件（AGV、Machine 等）
    env.build_context()

    print(f"[Context] 环境上下文创建完成: {env_type}")
    return env

def check_context(context):
    pass