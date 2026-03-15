'''
@Project ：tiangong 
@File    ：EventEnvPaused.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/7/2 17:29 
'''
from executor.packet_factory.event.event.BaseEvent import BaseEvent
from executor.packet_factory.event.EventType import EventType
from executor.packet_factory.registry.registry import register_event


@register_event('packet_factory.ENV_RESTART')
class EventEnvFail(BaseEvent):
    event_type = EventType.ENV_RESTART
    def __init__(self,status:str="trigger",payload:dict=None):
        super().__init__(status,payload)

    def trigger(self):
        """
        触发该事件
        """
        from executor.packet_factory.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
        self.judge_env(PacketFactoryEnv)
        self.env: PacketFactoryEnv

        # 触发环境重新初始化
        self.env.reset()
