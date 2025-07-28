
from sky_simulator.event.event_manager.EventManager import EventManager
from sky_simulator.registry.factory import create_component_by_id


def initialize_event_manager(config):
    event_config = config.get(config.get("env_type")).get('event_config')

    # 获取配置路径
    path = config.get('config_path')
    event_config = event_config.get('file')
    # 拼接目标事件的路径
    target_path = path.parent / event_config
    event_manager=EventManager()
    event_manager.load_event(target_path)

    return event_manager