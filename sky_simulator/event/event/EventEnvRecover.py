'''
@Project ：tiangong 
@File    ：EventEnvPaused.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/7/2 17:29 
'''
from sky_simulator.event.event.BaseEvent import BaseEvent
from sky_simulator.event.EventType import EventType
from sky_simulator.registry.registry import register_event


@register_event('packet_factory.ENV_RECOVER')
class EventEnvFail(BaseEvent):
    event_type = EventType.ENV_RECOVER
    def __init__(self,status:str="trigger",payload:dict=None):
        super().__init__(status,payload)

    def trigger(self):
        """
        触发该事件
        """
        from sky_simulator.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
        self.judge_env(PacketFactoryEnv)
        self.env: PacketFactoryEnv

        self.env.event_set_running()
