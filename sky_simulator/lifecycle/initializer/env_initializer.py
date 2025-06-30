from sky_simulator.call_back.callback_manager.CallbackManager import CallbackManager
from sky_simulator.lifecycle.initializer.event_initializer import initialize_event
from sky_simulator.registry.factory import create_component_by_id

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
                                                                   *callback_config.get('graph_loader').get('args')))
    callback_manager.register("initialize_visualizer",
                              create_component_by_id(callback_config.get('visualizer').get('name'),
                                                     *callback_config.get('visualizer').get('args')))

    env.set_callback_manager(callback_manager)
    print(f"[Callback] 添加至环境上下文...")

    # ---------- 添加事件队列 ----------
    event_queue=initialize_event(config)
    env.set_event_queue(event_queue)
    print(f"[Event] 添加至环境上下文...")

    return env
