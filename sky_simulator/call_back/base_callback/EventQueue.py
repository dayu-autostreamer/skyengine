
from sky_simulator.event.event import BaseEvent
import heapq
from sky_simulator.registry import register_component
from sky_simulator.event.event_manager.EventManager import EventManager
from sky_simulator.call_back.EnvCallback import EnvCallback

# 事件队列应该输入当前时间,输出应该执行的任务

# 朴素的FIFO事件队列
@register_component("base_callback.EventQueue")
class EventQueue(EnvCallback):
    def __init__(self,event_manager:EventManager=None):
        if event_manager is None:
            self.event_manager = EventManager() # 管理事件本次系统启动中支持的事件,若未指定则使用默认事件组
        self.queue = []  # 最小堆，按时间排序
        self.counter = 0  # 保持插入顺序，解决时间相同时的排序问题

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        print("队列调用")

    def __len__(self):
        return len(self.queue)

    def add_event(self,timestamp,event: BaseEvent):
        heapq.heappush(self.queue, (timestamp,self.counter, event))
        self.counter += 1

    def pop_ready_events(self, current_time: float):
        """弹出当前时间及以前的所有事件"""
        ready = []
        # ready = [e for e in self.events if e.timestamp <= current_time]
        # self.events = [e for e in self.events if e.timestamp > current_time]
        # return ready
        while self.queue and self.queue[0][0] <= current_time:
            _, _, event = heapq.heappop(self.queue)
            ready.append(event)
        return ready

    def peek_next_event_time(self):
        """查看下一个事件的时间"""
        if not self.queue:
            return None
        return self.queue[0][0]

    def list_all_events(self):
        """调试用：列出当前所有事件"""
        return [e for (_, _, e) in self.queue]


