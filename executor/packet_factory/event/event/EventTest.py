from executor.packet_factory.event.event.BaseEvent import BaseEvent
from executor.packet_factory.event.EventType import EventType
from executor.packet_factory.registry.registry import register_event


@register_event('packet_factory.JUST_TEST')
class EventTest(BaseEvent):
    event_type = EventType.JUST_TEST
    def __init__(self, status: str = "trigger", payload: dict = None):
        super().__init__(status, payload)
        self.payload = payload

    def trigger(self):
        """
        触发该事件
        """
        print('EventTest.trigger()')
        return self.event_type

    def recover(self):
        """
        恢复该事件的现场
        """
        print('EventTest.recover()')
        return self.event_type
