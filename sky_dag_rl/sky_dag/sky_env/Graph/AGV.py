from typing import Optional, Tuple
import math

from .Operation import Operation
from .Machine import Machine

class AGV:
    def __init__(self, id_: int, x: float, y: float, velocity: float):
        """
        :param id_: AGV ID
        :param x: 坐标 X
        :param y: 坐标 Y
        :param velocity: 移动速度
        """
        self.id: int = id_
        self.x: float = x
        self.y: float = y
        self.timer: float = 0.0
        self.velocity: float = velocity
        self.operation: Optional[Operation] = None

    def get_id(self) -> int:
        return self.id

    def get_xy(self) -> Tuple[float, float]:
        return self.x, self.y

    def set_xy(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def get_timer(self) -> float:
        return self.timer

    def get_operation(self) -> Optional[Operation]:
        return self.operation

    def set_operation(self, operation: Optional[Operation]) -> None:
        self.operation = operation

    def dist(self, target_x: float, target_y: float) -> float:
        dx = self.x - target_x
        dy = self.y - target_y
        return math.sqrt(dx * dx + dy * dy)

    def load(self, machine: Machine) -> None:
        if self.operation is not None:
            print("AGV is already loading an operation")
            return

        mx, my = machine.get_xy()
        distance = self.dist(mx, my)
        travel_time = distance / self.velocity
        self.timer += travel_time
        self.timer = max(self.timer, machine.get_timer())

        self.set_xy(mx, my)
        self.set_operation(machine.get_operation())
        machine.set_operation(None)

    def unload(self, machine: Machine) -> None:
        if self.operation is None:
            print("AGV is not loaded")
            return

        mx, my = machine.get_xy()
        distance = self.dist(mx, my)
        travel_time = distance / self.velocity
        self.timer += travel_time

        self.set_xy(mx, my)

        if machine.get_operation() is None:
            machine.set_timer(self.timer)
            machine.set_operation(self.operation)
            self.set_operation(None)
        else:
            machine.set_timer(max(machine.get_timer(), self.timer))
            machine_op = machine.get_operation()
            machine.set_operation(self.operation)
            self.set_operation(machine_op)

        machine.work()


if __name__ == '__main__':
    k=10
    agvs = []
    for i in range(k):
        x = float(1)
        y = float(1)
        velocity = float(1)
        agvs.append(AGV(i, x, y, velocity))