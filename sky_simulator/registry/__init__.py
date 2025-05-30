'''
@Project ：tiangong 
@File    ：__init__.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:38 
'''

from .registry import component_registry, register_component
from .scanner import scan_and_register_components
from .factory import create_component_by_id,get_component_class_by_id

__all__ = ['component_registry', 'register_component', 'scan_and_register_components','create_component_by_id',
           'get_component_class_by_id']
