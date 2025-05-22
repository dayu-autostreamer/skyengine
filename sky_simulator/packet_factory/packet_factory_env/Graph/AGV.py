from typing import Optional, Tuple, List
import math

from .util import AGVStatus, OperationStatus, MachineStatus
from sky_simulator.packet_factory.packet_factory_env.Graph.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Graph.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Utils.logger import LOGGER


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
        self.todo_queue: List[Tuple[str, Machine | Operation]] = []

        self.status = AGVStatus.READY

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
            f"status={self.status}>"
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
        if operation is None:
            LOGGER.info(f"Operation clear.")

    def get_status(self) -> AGVStatus:
        return self.status

    def set_status(self, status: AGVStatus):
        self.status = status

    def dist(self, target_x: float, target_y: float) -> float:
        dx = self.x - target_x
        dy = self.y - target_y
        return math.sqrt(dx * dx + dy * dy)

    def load_from_warehouse(self, operation: Operation):
        self.set_operation(operation)
        self.status = AGVStatus.LOADED

    # ---------- ready态使用 ----------
    def load(self, machine: Machine, final_time: float) -> bool:
        """
        从machine上获得对应的operation
        """
        if self.status != AGVStatus.READY:
            LOGGER.info(f"AGV id={self.id} is already loading an operation id={self.operation}")
            return False

        machine_operation: Optional[Operation] = machine.get_operation()
        if machine_operation is None:
            LOGGER.info(f"Machine id={machine.id} is not loaded")
            return False

        if not self.heading(machine, final_time):
            return False

        self.timer = max(self.timer, machine.get_timer())

        if machine.get_status() == MachineStatus.FINISHED:
            # 上个阶段结束顺利获得物料
            self.set_status(AGVStatus.ASSIGNED)
            self.set_operation(machine_operation)
            machine_operation.set_status(OperationStatus.MOVING)
            machine_operation.set_current_machine(None)
            machine.set_operation(None)
        else:
            LOGGER.info(f"Machine id={machine.id} is not finished.")
            return False

        return True

    # ---------- moving和loaded态使用 ----------
    def heading(self, machine: Machine, final_time: float) -> bool:
        # if self.status != AGVStatus.READY or self.status != AGVStatus.MOVING:
        #     LOGGER.info(f"AGV id={self.id} can't go to machine={machine.id}")
        #     return False
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
            return False

        self.set_xy(mx, my)
        self.timer += travel_time
        return True

    # ---------- moving态使用 ----------
    def unload(self, machine: Machine, final_time: float) -> bool:
        """
        将AGV上的operation卸载到对应machine上
        """
        if self.status is not AGVStatus.LOADED:
            LOGGER.info(f"AGV id={self.id} is not loaded")
            return False

        if not self.heading(machine, final_time):
            return False

        machine_operation: Optional[Operation] = machine.get_operation()

        if machine_operation is None:
            machine.set_operation(self.operation)
            self.operation.set_current_machine(machine)
            self.operation.set_status(OperationStatus.WORKING)

            self.set_status(AGVStatus.READY)
            self.set_operation(None)
        else:
            if machine.get_status() == MachineStatus.FINISHED:
                machine_operation.set_current_machine(None)
                machine.set_operation(self.operation)
                self.operation.set_current_machine(machine)
                self.operation.set_status(OperationStatus.WORKING)
                self.set_operation(machine_operation)
                # todo 修改为machine缓存版本

        self.set_status(AGVStatus.READY)
        machine.set_timer(max(machine.get_timer(), self.timer))
        machine.work(final_time)

        return True

    def is_available(self):
        return self.status == AGVStatus.READY

    def todo_queue_push(self, todo: Tuple[str, Machine | Operation]):
        self.todo_queue.append(todo)

    def todo_queue_pop(self) -> Optional[Tuple[str, Machine | Operation]]:
        if len(self.todo_queue) == 0:
            return None
        else:
            return self.todo_queue.pop(0)

    def todo_queue_is_empty(self):
        return len(self.todo_queue) == 0

    def push_process(self,final_time: float):

        while not self.todo_queue_is_empty():
            todo = self.todo_queue[0]
            LOGGER.info(f"AGV id={self.id} current todo: {todo}")
            if todo[0] == "load":
                if type(todo[1]) != Operation:
                    raise ValueError(f"Invalid todo type: {todo}")
                last_machine = todo[1].get_current_machine()
                if last_machine is None:
                    # 从头开始
                    self.load_from_warehouse(todo[1])
                    self.todo_queue_pop()
                else:
                    if self.load(last_machine, final_time):
                        # 如果可以就从上一个机器load,并且做完了
                        self.todo_queue_pop()
                    else:
                        break
            elif todo[0] == "unload":
                if type(todo[1]) != Machine:
                    raise ValueError(f"Invalid todo type: {todo}")
                if self.unload(todo[1], final_time):
                    self.todo_queue_pop()
                else:
                    break
        if self.todo_queue_is_empty():
            self.set_status(AGVStatus.READY)

    def work(self, final_time: float = None, action: Tuple[Operation, Machine] = None):
        if self.status == AGVStatus.READY:
            self.set_status(AGVStatus.ASSIGNED)
            if action is not None:
                self.todo_queue_push(("load", action[0]))
                self.todo_queue_push(("unload", action[1]))
                LOGGER.info(f"AGV id={self.id} assigned todo: {action}")
        elif self.status == AGVStatus.ASSIGNED:
            self.push_process(final_time)




if __name__ == '__main__':
    k = 10
    agvs = []
    for i in range(k):
        x = float(1)
        y = float(1)
        velocity = float(1)
        agvs.append(AGV(i, x, y, velocity))
