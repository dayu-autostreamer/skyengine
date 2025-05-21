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
        # todo 状态转移需要实现

        self.id: int = machine_id
        self.x: float = x
        self.y: float = y
        self.timer: float = 0.0
        self.operation: Optional[Operation] = operation

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"

    def is_available(self):
        op = self.get_operation()
        if op is None:
            return True
        else:
            return op.is_finished()

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

    def work(self, final_time: float) -> None:
        if self.operation is not None:
            duration = self.operation.get_duration(self.id)
            work_time: float = duration - self.operation.process_time
            if self.timer + work_time > final_time:
                self.operation.process_time += final_time - self.timer
                self.set_timer(final_time)
                return

            self.timer += work_time
            self.operation.set_process_time(duration)
            self.operation.set_finished(True)
            self.operation.set_status("finished")
            
            self.operation.set_current_machine(None)
            self.operation = self.operation.get_next_operation()
            if self.operation is not None:
                self.operation.set_current_machine(self)
        else:
            print(f"Machine {self.id} is idle")