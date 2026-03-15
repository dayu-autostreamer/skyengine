from pettingzoo import ParallelEnv

from executor.packet_factory.event.event import BaseEvent
import heapq
from executor.packet_factory.registry import register_component
from executor.packet_factory.event.event_manager.EventManager import EventManager
from executor.packet_factory.call_back.EnvCallback import EnvCallback


# 朴素的FIFO事件队列
@register_component("base_callback.EventQueue")
class EventQueue(EnvCallback):
    def __init__(self, event_manager: EventManager = None):
        super().__init__()

        self.event_manager = event_manager
        if event_manager is None:
            self.event_manager = EventManager()  # 管理事件本次系统启动中支持的事件,若未指定则使用默认事件组

        self.queue = []  # 最小堆，按时间排序
        self.counter = 0  # 保持插入顺序，解决时间相同时的排序问题
        self.env = None

        # 初始化后 获得管理器中的init_event集合
        for event in self.event_manager.init_event:
            self.add_event(event['timestamp'], self.event_manager.create_event(event['type'], *event['args']))

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        print("队列调用")

    def __len__(self):
        return len(self.queue)

    def set_env(self, env: ParallelEnv):
        self.env = env

    def add_event(self, timestamp, event: BaseEvent):
        heapq.heappush(self.queue, (timestamp, self.counter, event))
        self.counter += 1

    def pop_ready_events(self, current_time: float):
        """弹出当前时间及以前的所有事件"""
        ready = []
        while self.queue and self.queue[0][0] <= current_time:
            _, _, event = heapq.heappop(self.queue)

            event:BaseEvent
            event.set_env(self.env)

            ready.append(event)
        return ready

    def peek_next_event(self):
        """查看下一个事件的时间"""
        if not self.queue:
            return None
        return self.queue[0][0]

    def list_all_events(self):
        """调试用：列出当前所有事件"""
        return self.queue
