from sky_simulator.event.event.BaseEvent import BaseEvent
from sky_simulator.event.EventType import EventType
from sky_simulator.registry.registry import register_event


@register_event('packet_factory.JOB_ADD')
class EventJobAdd(BaseEvent):
    event_type = EventType.JOB_ADD
    def __init__(self,status:str="trigger",payload:dict=None):
        super().__init__(status,payload)

    def trigger(self):
        """
        触发该事件
        """
        return self.event_type

    def recover(self):
        """
        恢复该事件的现场
        """
        return self.event_type



