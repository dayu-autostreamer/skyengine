'''
@Project ：tiangong 
@File    ：factory.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:39 
'''
from sky_simulator.registry import component_registry

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

