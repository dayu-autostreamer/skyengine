'''
@Project ：tiangong 
@File    ：EventDealer.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/6/27 21:59 
'''
# 基本的事件处理类

from sky_simulator.call_back.EnvCallback import EnvCallback
from sky_simulator.registry import register_component
from sky_simulator.event import Event, EventType


@register_component("base_callback.EventDealer")
class EventDealer(EnvCallback):
    def __init__(self):
        super().__init__()
        # 注册事件类型到处理函数的映射
        self.events = {
            EventType.JUST_TEST: self.test,
            EventType.JOB_ADD: self.task_finish,
            EventType.JOB_CANCEL: self.task_finish,
            EventType.JOB_FINISH: self.task_finish,

            EventType.MACHINE_FAIL: self.machine_fail,

            EventType.AGV_REFRESH: self.agv_refresh,
            EventType.AGV_FAIL: self.agv_fail,
            EventType.AGV_BLOCK: self.agv_block,

            EventType.OPERATION_DELAY: self.operation_delay,
        }

    def __call__(self, event_data: Event):
        """使类的实例可以像函数一样被调用"""
        event_type = event_data.event_type
        event_payload = event_data.payload

        if event_type not in self.events:
            raise NotImplementedError(f"[EventDealer] 未定义的事件类型: {event_type}")

        handler = self.events[event_type]
        return handler(event_payload)

    # ========== 各类事件处理函数 ==========

    def test(self, payload):
        print(f"[Event] 🧪 Test Event Triggered | Payload: {payload}")

    def task_finish(self, payload):
        operation = payload.get("operation")
        print(f"[Event] ✅ Task Finished | Operation: {operation}")

    def machine_fail(self, payload):
        machine = payload.get("machine")
        if machine:
            machine.set_fail_state(True)
            print(f"[Event] ⚠️ Machine {machine} FAILED!")

    def agv_refresh(self, payload):
        agv = payload.get("agv")
        if agv:
            agv.refresh_status()
            print(f"[Event] 🔄 AGV {agv} Refreshed")

    def agv_fail(self, payload):
        agv = payload.get("agv")
        if agv:
            agv.set_fail_state(True)
            print(f"[Event] ⚠️ AGV {agv} FAILED!")

    def agv_block(self, payload):
        agv = payload.get("agv")
        reason = payload.get("reason", "Unknown")
        if agv:
            agv.set_blocked(True, reason=reason)
            print(f"[Event] 🚧 AGV {agv} Blocked | Reason: {reason}")

    def operation_delay(self, payload):
        operation = payload.get("operation")
        delay_time = payload.get("delay_time", 1.0)
        if operation:
            operation.add_delay(delay_time)
            print(f"[Event] ⏳ Operation {operation} Delayed by {delay_time}s")
