from executor.packet_factory.event.event.BaseEvent import BaseEvent
from executor.packet_factory.event.EventType import EventType
from executor.packet_factory.packet_factory.packet_factory_env.Machine.Machine import Machine
from executor.packet_factory.registry.registry import register_event


@register_event('packet_factory.MACHINE_FAIL')
class EventMachineFail(BaseEvent):
    event_type = EventType.MACHINE_FAIL

    def __init__(self, status: str = "trigger", payload: dict = None):
        super().__init__(status, payload)

        assert payload is not None, "payload不能为None"
        assert 'id' in payload, "payload必须包含id字段"

        self.machine_id = payload['id']

    def trigger(self):
        """
        触发该事件 触发时调用machine的record。
        """
        from executor.packet_factory.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
        self.judge_env(PacketFactoryEnv)
        self.env: PacketFactoryEnv

        target_machine: Machine=self.env.hash_index['machines'][self.machine_id]

        # 记录本次事件
        target_machine.record(self)
        # 实际执行事件
        target_machine.event_set_fail()

    def recover(self):
        """
        恢复该事件的现场
        """
        from executor.packet_factory.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
        self.judge_env(PacketFactoryEnv)
        self.env: PacketFactoryEnv

        target_machine: Machine=self.env.hash_index['machines'][self.machine_id]
        # 回复事件
        target_machine.event_set_restart()


