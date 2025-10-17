'''
@Project ：SkyEngine 
@File    ：sky_test_event_generator.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/8 12:45
'''
from sky_executor.utils.call_back.base_callback.EventQueue import EventQueue
from sky_executor.packet_factory.packet_factory_callback import CallbackManager
# 测试事件动态启动 管理等功能
from sky_executor.utils.registry import component_registry, selective_scan_and_register_components, create_component_by_id

from sky_executor.utils.registry.scanner import load_config
from sky_executor.utils.event.event_manager.EventManager import EventManager
import config

config_path = config.CONFIG_DIR + "/application_config.yaml"

if __name__ == '__main__':
    load_config(config_path)
    selective_scan_and_register_components(scan_all=True,
                                           exclude_dirs=["environment.grid_factory",
                                                         "call_back.grid_factory_callback",
                                                         "event.event.grid_factory_event",
                                                         "environment.packet_factory.Trainer"
                                                         ])
    config = component_registry.get('config')
    path = config.get('config_path')

    event_config = config.get(config.get("env_type")).get('event_config').get('file')
    target_path = path.parent / './template_config_set/event_config.yaml'

    event_manager = EventManager()
    event_manager.load_event(target_path)
    env_type = config.get("env_type")
    callback_config = config.get(env_type).get('callback').get('map_callback')

    callback_manager = CallbackManager()  # 调用对应的构造函数,使用时直接加括号就能使用
    callback_manager.register("event_queue",
                              create_component_by_id(callback_config.get('event_queue').get('name'),
                                                     event_manager))

    # 事件队列 不需要当场调用
    event_queue: EventQueue = callback_manager.get('event_queue')
    print(event_queue.queue)
    print(event_queue.queue[0][2])

    event_queue()

    print(len(event_queue))

    event_queue.list_all_events()

    print(event_queue.event_generator.event_configs)
    print(event_queue.event_generator.generation_stats)

    time_line = 0
    while True:
        event_list = event_queue.event_generator.generate_events_for_timestep(time_line, event_manager)
        print(f"{time_line}时生成的事件:{event_list}")
        time_line += 1
        if time_line >= 10:
            break
