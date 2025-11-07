'''
@Project ：tiangong 
@File    ：EventType.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/6/27 21:59 
'''
import os
import yaml
from pettingzoo import ParallelEnv

# 基本的事件管理类,作为实际上系统的特性,不应动态创建,事件本身动态创建即可。
# 主要管理事件本身的合法性 与 调用相关事宜

from sky_executor.utils.event.event.BaseEvent import BaseEvent
from sky_executor.utils.registry.factory import get_event_class_by_id


class EventManager:
    def __init__(self):
        self.events = {
        }
        self.init_event = []  # 记录数据集初始化时的Event
        self.history = []  # 已执行事件的历史记录
        self.env = None
        self.event_generation_configs = {}

    def add_event(self, event_name):
        # 确保当前事件还没被记录
        if event_name in self.events.keys():
            raise ValueError(f"[EventManager] 重复声明 '{event_name}' 事件")
        self.events[event_name] = get_event_class_by_id(event_name)

    def create_event(self, event_name, *args):
        """输入事件类型和参数,返回对应的事件实例"""

        status = args[0]
        assert status in ["trigger", "recover"]
        payload = args[1]
        assert isinstance(payload, dict)

        event: BaseEvent = self.events[event_name](status, payload)

        return event

    def load_event(self, config_path):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        if "config" not in raw_config:
            raise ValueError("Missing 'config' section in configuration.")

        event_config = raw_config["config"]

        event_type_list = event_config.get("event_type", None)

        if event_type_list is not None and len(event_type_list) > 0:
            for event_item in event_type_list:
                if isinstance(event_item, str):
                    # 简单的事件类型名称
                    self.add_event(event_item)
                elif isinstance(event_item, dict):
                    # 带配置的事件类型
                    for event_name, event_config_data in event_item.items():
                        self.add_event(event_name)
                        self.event_generation_configs[event_name] = event_config_data

        event_timeline = event_config.get("event_timeline", None)
        if event_timeline is not None and len(event_timeline) > 0:
            for event in event_timeline:
                self.init_event.append(event['event'])

    def get_event_generation_configs(self):
        """获取事件生成配置"""
        return self.event_generation_configs

    def deal_event(self, event: BaseEvent, env: ParallelEnv):
        """
        记录执行过的事件，同时说明该事件是否顺利执行
        """
        self.history.append((event, event(env)))

    def list_all_history(self):
        return self.history
