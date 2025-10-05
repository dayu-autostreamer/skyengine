from typing import List, Optional, Tuple
from sky_logs.logger import LOGGER
from sky_simulator.environment.packet_factory.packet_factory_env.Utils.util import OperationStatus
from sky_simulator.registry import register_component

@register_component("packet_factory.Operation")
class Operation:

    def __init__(self, op_id: int, status: OperationStatus, durations: List[Tuple[int, float]], cpu_req=0, mem_req=0):
        """
        :param process_time: 操作的处理时间
        :param durations: 列表，每个元素是 (machine_id, duration) 表示该机器上执行所需时间
        """
        # operation本身的属性
        self.id: int = op_id
        self.process_time: float = 0
        self.durations: List[Tuple[int, float]] = durations
        self.next_operation: Optional['Operation'] = None
        self.current_machine = None
        self.finished = False
        self.status: OperationStatus = OperationStatus.WAITING

        self.cpu_req = cpu_req
        self.mem_req = mem_req

        # operation本身的状态
        self.dependencies = []
        self.successors = []

        # operation处理item相关的状态
        self.processed_item_list = []
        self.current_progress = 0  # 当前物品的加工进度
        self.current_start_time = None

    def __repr__(self):
        # 格式化持续时间列表（最多显示前3个）
        durations_str = "[...]"
        if self.durations:
            durations_short = self.durations[:3]
            durations_str = ", ".join([f"({m_id}, {dur:.1f})" for m_id, dur in durations_short])
            if len(self.durations) > 3:
                durations_str += ", ..."
            durations_str = f"[{durations_str}]"
        return (
            f"<{self.__class__.__name__} "
            f"id={self.id} "
            f"time={self.process_time:.1f} "
            f"durations={durations_str} "
            f"status={self.status} "
        )

    def get_process_time(self) -> float:
        return self.process_time

    def set_process_time(self, process_time: float) -> None:
        self.process_time = process_time

    def is_machine_capable(self, machine_id: int) -> bool:
        """
        :param machine_id: 要检查的机器 ID
        :return: 是否该操作可以在该机器上执行
        """
        for m_id, _ in self.durations:
            if m_id == machine_id:
                return True
        return False

    def get_duration(self, machine_id: int) -> float:
        """
        :param machine_id: 机器 ID
        :return: 该操作在该机器上的执行时间
        """
        for m_id, duration in self.durations:
            if m_id == machine_id:
                return duration
        LOGGER.info(f"Operation {self.id}: Machine {machine_id} not found")
        return 0.0

    def get_next_operation(self) -> Optional['Operation']:
        return self.next_operation

    def set_next_operation(self, next_operation: Optional['Operation']) -> None:
        self.next_operation = next_operation

    def get_current_machine(self):
        return self.current_machine

    def set_current_machine(self, current_machine) -> None:
        self.current_machine = current_machine

    def get_status(self) -> OperationStatus:
        return self.status

    def set_status(self, status: OperationStatus):
        self.status = status

    def clone(self):
        op = Operation(self.id, OperationStatus.WAITING, self.durations)
        return op
