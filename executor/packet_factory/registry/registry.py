'''
@Project ：tiangong 
@File    ：registry.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:38 
'''
component_registry = {}
event_registry={}

def register_component(component_id):
    def decorator(cls):
        if component_id in component_registry:
            raise ValueError(f"Duplicate component ID: {component_id}")
        component_registry[component_id] = cls
        return cls
    return decorator

def register_event(event_id):
    def decorator(cls):
        if event_id in event_registry:
            raise ValueError(f"Duplicate event ID: {event_id}")
        event_registry[event_id] = cls
        return cls

    return decorator