'''
@Project ：tiangong 
@File    ：EventType.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/6/27 21:59 
'''
import os
import yaml

# 基本的事件管理类,作为实际上系统的特性,不应动态创建,事件本身动态创建即可。
# 主要管理事件本身的合法性 与 调用相关事宜

from sky_simulator.event.event.BaseEvent import BaseEvent
from sky_simulator.event.EventType import EventType
from sky_simulator.registry.factory import get_event_class_by_id

class EventManager:
    def __init__(self):
        self.events = {
        }

    def add_event(self, event_name):
        # 确保当前事件还没被记录
        if event_name in self.events.keys():
            raise ValueError(f"[EventManager] 重复声明 '{event_name}' 事件")
        self.events[event_name] = get_event_class_by_id(event_name)


    def create_event(self,event_name,status='trigger',payload=None):
        """输入事件类型和参数,返回对应的事件实例"""
        return self.events[event_name](status,payload)


    def load_event(self,config_path):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        if "config" not in raw_config:
            raise ValueError("Missing 'config' section in configuration.")

        event_config = raw_config["config"]

        event_type_list=event_config["event_type"]

        for event_name in event_type_list:
            self.add_event(event_name)
