from enum import Enum


# 定义一个枚举类
class EventType(Enum):
    just_test = 0
    task_finish = 1
    machine_fail = 2


class Event:
    def __init__(self, timestamp, event_type, payload):
        self.timestamp = timestamp  # 事件发生的时间
        self.event_type = event_type  # 如 'task_finish', 'machine_fail'
        self.payload = payload  # json对象 不同事件请自行携带不同负载


class EventQueue:
    def __init__(self):
        self.events = []
        self.idx = 0

    def __len__(self):
        return len(self.events)

    def add_event(self, event: Event):
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)

    def pop_ready_events(self, current_time):
        ready = [e for e in self.events if e.timestamp <= current_time]
        self.events = [e for e in self.events if e.timestamp > current_time]
        return ready
