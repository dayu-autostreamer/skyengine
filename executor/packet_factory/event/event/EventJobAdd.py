from executor.packet_factory.event.event.BaseEvent import BaseEvent
from executor.packet_factory.event.EventType import EventType
from executor.packet_factory.registry.registry import register_event


@register_event('packet_factory.JOB_ADD')
class EventJobAdd(BaseEvent):
    event_type = EventType.JOB_ADD

    def __init__(self,status:str="trigger",payload:dict=None):
        super().__init__(status,payload)

        assert payload is not None, "payload不能为None"
        assert 'job' in payload, "payload必须包含job字段"
        self.job=payload['job']

    def trigger(self):
        """
        触发该事件
        """
        from executor.packet_factory.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
        self.judge_env(PacketFactoryEnv)
        self.env: PacketFactoryEnv

        self.env.jobs.append(self.job)




