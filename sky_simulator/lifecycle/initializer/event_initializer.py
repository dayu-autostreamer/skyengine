from sky_simulator.event.event_manager.EventManager import EventManager
from sky_simulator.registry.factory import create_component_by_id
import config as global_config
from pathlib import Path

def initialize_event_manager(config):
    event_config = config.get(config.get("env_type")).get('event_config')
    event_file = event_config.get('file')

    # 获取配置路径
    path = Path(config.get('config_path'))

    # 判断是绝对路径还是相对路径
    if Path(event_file).is_absolute():
        target_path = Path(event_file)
    else:
        target_path = path.parent / event_file

    event_manager = EventManager()
    event_manager.load_event(target_path)

    return event_manager
