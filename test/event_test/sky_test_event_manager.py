# 测试事件动态启动 管理等功能
from sky_executor.utils.registry import component_registry, selective_scan_and_register_components
from sky_executor.utils.registry.scanner import load_config
from sky_executor.utils.event.event_manager.EventManager import EventManager
import config

config_path = config.CONFIG_DIR + "/application_config.yaml"

if __name__ == '__main__':
    load_config(config_path)
    selective_scan_and_register_components(scan_all=True,
                                           exclude_dirs=["environment.factory",
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
    event = event_manager.create_event('packet_factory.MACHINE_FAIL', 'trigger', {"id": 1})
    print(event.event_type)
    print(event_manager.init_event)
    event_generation_config = event_manager.get_event_generation_configs()
    print(event_generation_config)




