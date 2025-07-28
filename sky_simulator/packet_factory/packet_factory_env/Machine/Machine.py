from typing import Optional, Tuple, List

from sky_simulator.event.event.BaseEvent import BaseEvent
from sky_simulator.packet_factory.packet_factory_env.Job.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Utils.util import OperationStatus, MachineStatus
from sky_logs.logger import LOGGER

from sky_simulator.registry import register_component


@register_component("packet_factory.Machine")
class Machine:
    def __init__(self, machine_id: int, x: float, y: float, point_id: int):
        """
        :param id: 机器 ID
        :param x: 坐标 X
        :param y: 坐标 Y
        """

        self.id: int = machine_id
        self.x: float = x
        self.y: float = y
        self.point_id: int = point_id
        self.timer: float = 0.0

        self.status: MachineStatus = MachineStatus.READY
        # 缓存的Operation
        self.input_queue: List[Operation] = []
        self.output_queue: List[Operation] = []

        # 事件相关 记录某个状态在修改前的取值
        self.history_stack: List = []

    def pack(self) -> dict:
        """
        将所有可能变化的状态打包（用于事件记录/恢复）
        """
        return {
            "id":self.id,
            "x": self.x,
            "y": self.y,
            "point_id": self.point_id,
            "timer": self.timer,
            "status": self.status.name,
        }

    def unpack(self, field: dict):
        """
        从记录中恢复状态
        """
        self.id = field["id"]
        self.x = field["x"]
        self.y = field["y"]
        self.point_id = field["point_id"]
        self.status = MachineStatus[field["status"]]
        self.timer = field["timer"]

    def __repr__(self):
        return (f"<{self.__class__.__name__} "
                f"id={self.id}> "
                f"status={self.status}> "
                f"input_queue={self.input_queue} "
                f"output_queue={self.output_queue}> "
                )

    # ---------- 模拟Machine运行 ----------
    def is_available(self) -> bool:
        # todo: 若是有限缓冲区，当缓冲区满时不能指派
        return self.get_status() == MachineStatus.READY or self.get_status() == MachineStatus.WORKING

    def get_id(self) -> int:
        return self.id

    def get_xy(self) -> Tuple[float, float]:
        return self.x, self.y

    def get_timer(self) -> float:
        return self.timer

    def set_timer(self, timer: float) -> None:
        self.timer = timer

    def input_push_operation(self, operation: Operation) -> None:
        LOGGER.info(f"Machine id={self.id} input operation {operation.id}")
        self.input_queue.append(operation)

    def input_pop_operation(self) -> Optional[Operation]:
        if len(self.input_queue) == 0:
            LOGGER.warning(f"Machine id={self.id} input queue is empty")
            return None
        else:
            return self.input_queue.pop(0)

    def output_push_operation(self, operation: Operation) -> None:
        self.output_queue.append(operation)

    def output_pop_operation(self, operation: Optional[Operation] = None) -> Optional[Operation]:
        if len(self.output_queue) == 0:
            LOGGER.warning(f"Machine id={self.id} output queue is empty")
            return None
        elif operation is None:
            return self.output_queue.pop(0)
        else:
            return self.output_queue.pop(self.output_queue.index(operation))

    def get_status(self) -> MachineStatus:
        return self.status

    def set_status(self, status: MachineStatus):
        self.status = status

    def push_process(self, final_time):
        """ 
        模拟机器工作
        :param final_time: 模拟的截止时间
        """
        LOGGER.info(f"Machine {self.id} is working")
        while len(self.input_queue) > 0:
            self.set_status(MachineStatus.WORKING)

            current_operation = self.input_queue[0]
            duration = current_operation.get_duration(self.id)

            work_time: float = duration - current_operation.process_time
            if self.timer + work_time > final_time:
                current_operation.process_time += final_time - self.timer
                self.set_timer(final_time)
                return False
            self.timer += work_time
            # 设置完成
            current_operation.set_process_time(duration)
            current_operation.set_status(OperationStatus.FINISHED)
            current_operation.set_current_machine(None)

            next_operation = current_operation.get_next_operation()
            if next_operation is not None:
                next_operation.set_status(OperationStatus.READY)
                next_operation.set_current_machine(self)
                self.output_push_operation(next_operation)

            self.input_pop_operation()
        self.set_status(MachineStatus.READY)

        return True

    def work(self, final_time: float):
        """
        判断机器是否处于正常状态，若正常则开始工作
        :param final_time: 模拟的截止时间
        """
        # todo: 维护一个machine的状态（event队列去修改的），如果当前machine状态=宕机，把self.timer变成final_time，但是不移动坐标

        if self.get_status() == MachineStatus.READY or self.get_status() == MachineStatus.WORKING:
            self.push_process(final_time)
        else:
            LOGGER.info(f"Machine {self.id} is failed")

    # ---------- 修改状态的函数,便于事件使用 ----------

    def record(self, event:BaseEvent):
        """
        执行事件并记录
        """
        self.history_stack.append(
            {
                "field": self.pack(),
                "event_id": event.event_id
            }
        )

    def recover(self, event=None):
        """
        恢复（撤销）事件。
        - 如果不传 event，则撤销最近的一个事件。
        - 如果传入 event_id，则回滚到该事件之前，期间的所有事件都会被撤销。
        """
        if not self.history_stack:
            print("没有可以恢复的事件")
            return
        pass

    def event_set_fail(self):
        self.set_status(MachineStatus.FAILED)

    def event_set_restart(self):
        if self.history_stack is None or len(self.history_stack) == 0:
            self.set_status(MachineStatus.READY)
        else:
            self.unpack(self.history_stack[-1]['field'])
