'''
@Project ：tiangong 
@File    ：factory.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:39 
'''
from executor.packet_factory.registry import component_registry,event_registry

def create_component_by_id(component_id: str, *args, **kwargs):
    cls = component_registry.get(component_id)
    if cls is None:
        raise ValueError(f"Unknown component ID: {component_id}")
    return cls(*args, **kwargs)

def get_component_class_by_id(component_id: str):
    cls = component_registry.get(component_id)
    if cls is None:
        raise ValueError(f"Unknown component ID: {component_id}")
    return cls

def get_event_class_by_id(event_id: str):
    cls = event_registry.get(event_id)
    if cls is None:
        raise ValueError(f"Unknown event ID: {event_id}")
    return cls
