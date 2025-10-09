from pettingzoo import ParallelEnv
from typing import Dict, Any

from sky_simulator.event.event.BaseEvent import BaseEvent
import heapq
from sky_simulator.registry import register_component
from sky_simulator.event.event_manager.EventManager import EventManager
from sky_simulator.event.event_manager.EventGenerator import EventGenerator
from sky_simulator.call_back.EnvCallback import EnvCallback
from sky_logs.logger import LOGGER


# 集成EventGenerator的智能事件队列
@register_component("base_callback.EventQueue")
class EventQueue(EnvCallback):
    def __init__(self, event_manager: EventManager = None):
        super().__init__()

        # 事件管理器
        self.event_manager = event_manager
        if event_manager is None:
            self.event_manager = EventManager()  # 管理事件本次系统启动中支持的事件,若未指定则使用默认事件组

        # 事件生成器
        self.event_generator = EventGenerator()  # 使用同步EventGenerator
        self.add_event_config(self.event_manager.event_generation_configs)

        self.queue = []  # 最小堆，按时间排序
        self.counter = 0  # 保持插入顺序，解决时间相同时的排序问题
        self.env = None

        # 统计信息
        self.stats = {
            'total_events_generated': 0,
            'events_by_type': {},
        }

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

    def add_event(self, timestamp, event: BaseEvent, generated=False):
        """添加事件到队列"""
        heapq.heappush(self.queue, (timestamp, self.counter, event))
        self.counter += 1

    def get_user_events(self, command_list, time_stamp):
        # ---------- 翻译创建事件 ----------
        for command in command_list:
            payload = {}
            if command['type'] == 'AGV':
                current_agv = command['data']
                payload = current_agv.pack()
            elif command['type'] == 'MACHINE':
                current_machine = command['data']
                payload = current_machine.pack()
            elif command['type'] == 'JOB':
                current_job = command['data']
                payload['job'] = current_job
            else:
                pass

            current_event = self.event_manager.create_event(command['event_type'],
                                                            *[command['event_method'], payload])
            self.add_event( time_stamp, event=current_event)

    def generate_events(self, timestamp, env_info):
        try:
            new_event_list = self.event_generator.generate_events_for_timestep(timestamp, self.event_manager, env_info)
            if new_event_list:
                # 将事件添加到队列，使用当前时间戳
                for event in new_event_list:
                    self.add_event(timestamp, event, generated=True)
                    self.stats.get('events_by_type', {}).setdefault(event.event_type, 0)
                    self.stats['events_by_type'][event.event_type] += 1

                # 更新统计
                self.stats['total_events_generated'] += len(new_event_list)

                LOGGER.debug(f"[EventQueue] 同步生成了 {len(new_event_list)} 个事件")
        except Exception as e:
            LOGGER.error(f"[EventQueue] 同步生成事件失败: {e}")

    def pop_ready_events(self, current_time: float):
        """弹出当前时间及以前的所有事件"""
        ready = []
        while self.queue and self.queue[0][0] <= current_time:
            _, _, event = heapq.heappop(self.queue)

            event: BaseEvent
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

    def deal_event(self, ready_event, env):
        """处理就绪事件"""
        for event in ready_event:
            self.event_manager.deal_event(event, env)

    def add_event_config(self, event_list):
        """添加事件生成配置"""
        if self.event_generator:
            for event_type, kwargs in event_list.items():
                self.event_generator.add_event_config(event_type, **kwargs)
        else:
            LOGGER.warning("[EventQueue] EventGenerator未初始化，无法添加事件配置")

    def get_stats(self) -> Dict[str, Any]:
        """获取事件生成统计信息"""
        stats = self.stats.copy()
        stats.update({
            'queue_size': len(self.queue),
        })
        return stats

    def clear_queue(self):
        """清空事件队列"""
        self.queue.clear()
        self.counter = 0
        LOGGER.info("[EventQueue] 清空事件队列")

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_events_generated': 0,
            'events_by_type': {},
        }
        LOGGER.info("[EventQueue] 重置统计信息")
