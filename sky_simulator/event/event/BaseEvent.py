# 该文件内提供预定义的一些事件类型和事件类，同时提供事件队列，所有的事件均需要依照这种方法添加
# 具体的事件处理函数在回调中体现。

from sky_simulator.event.EventType import EventType

class BaseEvent:
    event_type = EventType.BASE_EVENT
    def __init__(self,status:str="trigger",payload:dict=None):
        # 保证是已声明的事件类型
        self.status = status # 事件初始行为
        self.payload = payload or {}  # 事件携带的数据

    def __repr__(self):
        return f"[Event] {self.event_type.name} - Payload: {self.payload}"

    def __call__(self):
        if self.status=="trigger":
            self.trigger()
        elif self.status=="recover":
            self.recover()
        else:
            raise ValueError(f"[Event] {self.event_type} Event {self.status} Wrong!")

        print(f"[Event] {self.event_type} Event {self.status} | Payload: {self.payload}")

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
