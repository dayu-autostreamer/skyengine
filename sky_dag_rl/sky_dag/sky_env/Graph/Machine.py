from typing import Optional, Tuple

from .Operation import Operation

class Machine:
    def __init__(self, machine_id: int, x: float, y: float, operation: Optional[Operation]):
        """
        :param id_: 机器 ID
        :param x: 坐标 X
        :param y: 坐标 Y
        :param operation: 当前正在执行的操作
        """
        self.id: int = machine_id
        self.x: float = x
        self.y: float = y
        self.timer: float = 0.0
        self.operation: Optional[Operation] = operation

    def get_id(self) -> int:
        return self.id

    def get_xy(self) -> Tuple[float, float]:
        return self.x, self.y

    def get_timer(self) -> float:
        return self.timer

    def set_timer(self, timer: float) -> None:
        self.timer = timer

    def get_operation(self) -> Optional[Operation]:
        return self.operation

    def set_operation(self, operation: Optional[Operation]) -> None:
        self.operation = operation

    def work(self) -> None:
        if self.operation is not None:
            duration = self.operation.get_duration(self.id)
            self.timer += duration
            self.operation.set_process_time(duration)
            self.operation = self.operation.get_next_operation()
        else:
            print(f"Machine {self.id} is idle")