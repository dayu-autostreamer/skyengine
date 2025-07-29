# 测试事件动态启动 管理等功能
from sky_simulator.lifecycle import context_creator
from sky_simulator.registry import component_registry, scan_and_register_components, create_component_by_id
from sky_simulator.registry.scanner import load_config
from sky_simulator.event.event_manager.EventManager import EventManager
from pathlib import Path
import config

config_path = '../../config/application_config.yaml'

if __name__ == '__main__':
    load_config(config_path)
    scan_and_register_components()
    config = component_registry.get('config')
    path = config.get('config_path')

    event_config = config.get(config.get("env_type")).get('event_config').get('file')
    target_path = path.parent / './config_set/event_config.yaml'

    event_manager=EventManager()
    event_manager.load_event(target_path)
    event=event_manager.create_event('packet_factory.MACHINE_FAIL','trigger',payload={})
    print(event_manager.init_event)
    event()
