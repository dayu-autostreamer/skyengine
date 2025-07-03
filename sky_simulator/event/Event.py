# 该文件内提供预定义的一些事件类型和事件类，同时提供事件队列，所有的事件均需要依照这种方法添加
# 具体的事件处理函数在回调中体现。

from enum import Enum
import heapq


# 定义一个枚举类
class EventType(Enum):
    JUST_TEST = 0

    JOB_FINISH = 100
    JOB_ADD = 101
    JOB_CANCEL = 102

    MACHINE_FAIL = 200

    AGV_REFRESH = 300
    AGV_FAIL = 301
    AGV_BLOCK = 302

    OPERATION_DELAY = 400


class Event:
    def __init__(self, timestamp: float, event_type: EventType, payload: dict):
        self.timestamp = timestamp  # 事件发生的时间
        self.event_type = event_type  # 事件类型
        self.payload = payload or {}  # 事件携带的数据

    def __repr__(self):
        return f"[Event] ⏰{self.timestamp} - {self.event_type.name} - Payload: {self.payload}"


class EventQueue:
    def __init__(self):
        self._queue = []  # 最小堆，按时间排序
        self._counter = 0  # 为了保持插入顺序，解决相同时间的排序问题

    def __len__(self):
        return len(self._queue)

    def add_event(self, event: Event):
        heapq.heappush(self._queue, (event.timestamp, self._counter, event))
        self._counter += 1

    def pop_ready_events(self, current_time: float):
        """弹出当前时间及以前的所有事件"""
        ready = []
        while self._queue and self._queue[0][0] <= current_time:
            _, _, event = heapq.heappop(self._queue)
            ready.append(event)
        return ready

    def peek_next_event_time(self):
        """查看下一个事件的时间"""
        if not self._queue:
            return None
        return self._queue[0][0]

    def list_all_events(self):
        """调试用：列出当前所有事件"""
        return [e for (_, _, e) in self._queue]
