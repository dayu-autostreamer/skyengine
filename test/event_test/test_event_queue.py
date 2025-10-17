from sky_executor.utils.call_back.base_callback.EventQueue import EventQueue
from sky_executor.packet_factory.packet_factory_callback import CallbackManager
from sky_executor.utils.registry import component_registry, scan_and_register_components, create_component_by_id
from sky_executor.utils.registry.scanner import load_config
from sky_executor.utils.event.event_manager.EventManager import EventManager

config_path = '../../config/application_config.yaml'

if __name__ == '__main__':
    load_config(config_path)
    scan_and_register_components()
    config = component_registry.get('config')
    path = config.get('config_path')

    event_config = config.get(config.get("env_type")).get('event_config').get('file')
    target_path = path.parent / './template_config_set/event_config.yaml'

    event_manager=EventManager()
    event_manager.load_event(target_path)
    env_type = config.get("env_type")
    callback_config = config.get(env_type).get('callback').get('map_callback')

    callback_manager = CallbackManager()  # 调用对应的构造函数,使用时直接加括号就能使用
    callback_manager.register("event_queue",
                              create_component_by_id(callback_config.get('event_queue').get('name'),
                                                     event_manager))

    # 事件队列 不需要当场调用
    event_queue:EventQueue = callback_manager.get('event_queue')
    print(event_queue.queue)
    print(event_queue.queue[0][2])

    event_queue()

    len(event_queue)

    event_queue.peek_next_event_time()

    event_queue.list_all_events()

    time_line=0
    while True:
        res=event_queue.pop_ready_events(time_line)
        print(res)
        time_line+=1
        if time_line>=5:
            break

