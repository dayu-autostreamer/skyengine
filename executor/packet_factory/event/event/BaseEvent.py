# 该文件内提供预定义的一些事件类型和事件类，同时提供事件队列，所有的事件均需要依照这种方法添加
# 具体的事件处理函数在回调中体现。
from pettingzoo import ParallelEnv

from executor.packet_factory.event.EventType import EventType

from executor.packet_factory.logger.logger import LOGGER

class BaseEvent:
    # 类变量 事件ID计数器
    _next_event_id = 1
    event_type = EventType.BASE_EVENT

    @classmethod
    def _get_next_event_id(cls) -> int:
        """获取下一个唯一事件ID并递增计数器"""
        current_id = cls._next_event_id
        cls._next_event_id += 1
        return current_id

    def __init__(self, status: str = "trigger", payload: dict = None):
        # 分配唯一ID并递增计数器
        self.event_id = self._get_next_event_id()

        # 保证是已声明的事件类型
        self.status = status  # 事件初始行为
        self.payload = payload or {}  # 事件携带的数据
        self.env = None  # 事件可以手动绑定环境使用 或者每次传入不同的env使用

    def __repr__(self):
        return f"[Event] {self.event_type.name} - Payload: {self.payload}"

    def __call__(self, env: ParallelEnv) -> bool:
        """
        返回当前事件是否执行成功
        """
        LOGGER.info(f"[Event] {self.event_type} Event {self.status} | Payload: {self.payload}")

        if self.status == "trigger":
            res = self.trigger()
        elif self.status == "recover":
            res = self.recover()
        else:
            raise ValueError(f"[Event] {self.event_type} Event {self.status} Wrong!")

        return res

    def trigger(self) -> bool:
        """
        触发该事件
        """
        return True

    def recover(self) -> bool:
        """
        恢复该事件的现场
        """
        return True

    def judge_env(self, env_type: type):
        """指定当前环境,确定当前事件和环境是对应的"""
        assert isinstance(self.env, env_type), f"env必须是{env_type}的实例,当前为{type(self.env)}"

    def set_env(self, env):
        self.env = env
        LOGGER.info(f"[Event] {self.event_type} Event combined with env")
