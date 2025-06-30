
from sky_simulator.event.event_manager.EventManager import EventManager
from sky_simulator.registry.factory import create_component_by_id


def initialize_event_manager(config):
    event_config = config.get(config.get("env_type")).get('event_config')

    path = config.get('config_path')
    event_config = event_config.get('file')
    target_path = path.parent / event_config

    event_manager=EventManager()
    event_manager.load_event(target_path)

    return event_manager