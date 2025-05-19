from typing import Optional, Tuple
import math

from sky_dag_rl.sky_dag.sky_env.Graph.Operation import Operation
from sky_dag_rl.sky_dag.sky_env.Graph.Machine import Machine

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

    def __repr__(self):
        # 获取当前操作的名称（如果有）
        operation_name = self.operation.id if self.operation else "None"

        # 格式化坐标和速度，保留两位小数
        return (
            f"<{self.__class__.__name__} "
            f"id={self.id} "
            f"pos=({self.x:.2f}, {self.y:.2f}) "
            f"v={self.velocity:.2f} "
            f"timer={self.timer:.2f} "
            f"operation={operation_name}>"
        )

    def get_id(self) -> int:
        return self.id

    def get_xy(self) -> Tuple[float, float]:
        return self.x, self.y

    def set_xy(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def get_timer(self) -> float:
        return self.timer
    
    def set_timer(self, timer: float) -> None:
        self.timer = timer

    def get_operation(self) -> Optional[Operation]:
        return self.operation

    def set_operation(self, operation: Optional[Operation]) -> None:
        self.operation = operation

    def dist(self, target_x: float, target_y: float) -> float:
        dx = self.x - target_x
        dy = self.y - target_y
        return math.sqrt(dx * dx + dy * dy)

    def load(self, machine: Machine, final_time: float) -> None:
        if self.operation is not None:
            print("AGV is already loading an operation")
            return
        machine_operation: Optional[Operation] = machine.get_operation()
        if machine_operation is None:
            print("Machine is not loaded")
            return
        
        mx, my = machine.get_xy()
        distance = self.dist(mx, my)
        travel_time = distance / self.velocity

        if self.get_timer() + travel_time > final_time:
            agv_x, agv_y = self.get_xy()
            dx: float = mx - agv_x
            dy: float = my - agv_y
            agv_x = agv_x + dx * (final_time - self.get_timer()) / travel_time
            agv_y = agv_y + dy * (final_time - self.get_timer()) / travel_time
            self.set_xy(agv_x, agv_y)
            self.set_timer(final_time)
            return

        self.set_xy(mx, my)
        self.timer += travel_time
        if not machine_operation.is_finished():
            machine.work(final_time)
        self.timer = max(self.timer, machine.get_timer())

        if machine_operation.is_finished():
            self.set_operation(machine_operation)
            machine_operation.set_current_machine(None)
            machine.set_operation(None)

    def unload(self, machine: Machine, final_time: float) -> None:
        if self.operation is None:
            print("AGV is not loaded")
            return

        mx, my = machine.get_xy()
        distance = self.dist(mx, my)
        travel_time = distance / self.velocity

        if self.get_timer() + travel_time > final_time:
            agv_x, agv_y = self.get_xy()
            dx: float = mx - agv_x
            dy: float = my - agv_y
            agv_x = agv_x + dx * (final_time - self.get_timer()) / travel_time
            agv_y = agv_y + dy * (final_time - self.get_timer()) / travel_time
            self.set_xy(agv_x, agv_y)
            self.set_timer(final_time)
            return

        self.set_xy(mx, my)
        self.timer += travel_time

        machine_operation: Optional[Operation] = machine.get_operation()

        if machine_operation is None:
            machine.set_timer(max(machine.get_timer(), self.timer))
            machine.set_operation(self.operation)
            self.operation.set_current_machine(machine)
            self.set_operation(None)
        else:
            if not machine_operation.is_finished():
                machine.work(final_time)
            machine.set_timer(max(machine.get_timer(), self.timer))
            if machine_operation.is_finished():
                machine_operation.set_current_machine(None)
                machine.set_operation(self.operation)
                self.operation.set_current_machine(machine)
                self.set_operation(machine_operation)

        machine.work(final_time)


if __name__ == '__main__':
    k=10
    agvs = []
    for i in range(k):
        x = float(1)
        y = float(1)
        velocity = float(1)
        agvs.append(AGV(i, x, y, velocity))