from executor.packet_factory.call_back.callback_manager.CallbackManager import CallbackManager
from executor.packet_factory.lifecycle.initializer.event_initializer import initialize_event_manager
from executor.packet_factory.registry.factory import create_component_by_id,get_component_class_by_id


def initialize_env(config, agent):
    """
    寻找环境中预留的各个回调,并根据config进行插入替换、
    """

    env_type = config.get("env_type")
    if not env_type:
        raise ValueError("[Context] 配置中未指定 'env_type'，请检查配置文件")

    # todo 后续根据real还是sim更换创建流程
    env_name = config.get(env_type).get("env_name")
    env = create_component_by_id(env_name, agent)
    env: get_component_class_by_id(env_name)

    callback_config = config.get(env_type).get('callback').get('map_callback')

    # ---------- 创建回调管理器 ----------
    callback_manager = CallbackManager()  # 调用对应的构造函数,使用时直接加括号就能使用
    callback_manager.register("load_graph", create_component_by_id(callback_config.get('graph_loader').get('name'),
                                                                   *callback_config.get('graph_loader').get('args')))
    callback_manager.register("initialize_visualizer",
                              create_component_by_id(callback_config.get('visualizer').get('name'),
                                                     *callback_config.get('visualizer').get('args')))

    # ---------- 创建事件管理器 ----------
    event_manager = initialize_event_manager(config)

    callback_manager.register("event_queue",
                              create_component_by_id(callback_config.get('event_queue').get('name'),
                                                     event_manager))
    env.set_callback_manager(callback_manager)
    print(f"[Callback] Added to Context...")

    return env
