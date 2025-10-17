from sky_executor.utils.event.event.BaseEvent import BaseEvent
from sky_executor.packet_factory.packet_factory_event.EventType import EventType
from sky_executor.packet_factory.packet_factory.packet_factory_env.Agv.AGV import AGV
from sky_executor.utils.registry.registry import register_event


@register_event('packet_factory.AGV_FAIL')
class EventAgvFail(BaseEvent):
    event_type = EventType.AGV_FAIL

    def __init__(self, status: str = "trigger", payload: dict = None):
        super().__init__(status, payload)
        assert payload is not None, "payload不能为None"
        assert 'id' in payload, "payload必须包含id字段"

        self.agv_id = payload['id']

    def trigger(self):
        """
        触发该事件
        """
        print('EventAGV.trigger()')

        from sky_executor.packet_factory.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
        self.judge_env(PacketFactoryEnv)
        self.env: PacketFactoryEnv

        target_AGV: AGV = self.env.hash_index['agvs'][self.agv_id]

        # 记录本次事件
        target_AGV.record(self)
        # 实际执行事件
        target_AGV.event_set_fail()

    def recover(self):
        """
        恢复该事件的现场
        """
        print('EventAGV.recover()')
        from sky_executor.packet_factory.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
        self.judge_env(PacketFactoryEnv)
        self.env: PacketFactoryEnv

        target_AGV: AGV = self.env.hash_index['agvs'][self.agv_id]
        # 回复事件
        target_AGV.event_set_restart()
