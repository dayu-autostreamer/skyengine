from typing import Optional, Tuple, List
import math
import numpy as np

from .util import AGVStatus, OperationStatus, MachineStatus
from sky_simulator.packet_factory.packet_factory_env.Graph.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Graph.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Graph.Graph import Graph
from sky_simulator.packet_factory.packet_factory_env.Utils.logger import LOGGER
from sky_simulator.registry import register_component

class AGVUncertaintySimulator:
    def __init__(self, base_seed=None, probability=0.3):
        """
        :param base_seed: 基础种子, 用于初始化随机流, None 表示系统随机
        :param probability: 不确定事件发生的概率 [0, 1]
        """
        self.base_seed = base_seed
        self.probability = probability
        self.cache = {}
        # 创建一个独立的随机数生成器
        self.seed_seq = np.random.SeedSequence(base_seed)
        self.rng = np.random.Generator(np.random.PCG64(self.seed_seq))
        # 从上次调用uncertain_event_occurred函数开始，是否发生过不确定事件
        self.is_occurred = False

    def uncertain_event_ratio(self, agv_id, machine_id, operation_id):
        """
        :param agv_id: AGV ID
        :param operation_id: 操作ID (unload步骤) 或者 None (load步骤)
        :param machine_id: 机器ID
        :return: 若随机事件发生, 返回实际agv移动时间和原始移动时间的比例, 否则返回1
        """
        key = (agv_id, machine_id, operation_id)
        if key in self.cache:
            return self.cache[key]

        # 使用类内部的 rng 生成随机值
        random_value = self.rng.random()
        result = random_value < self.probability

        if result:
            LOGGER.info(f"AGV {agv_id} Machine {machine_id} operation {operation_id} has uncertain event")
            self.is_occurred = True
            # todo: 通过yaml配置随机事件后的具体影响
            random_ratio = np.random.uniform(1, 1.5)
        else:
            random_ratio = 1

        self.cache[key] = random_ratio
        return random_ratio
    
    def uncertain_event_occurred(self):
        """
        :return: 若发生随机事件, 返回True, 否则返回False
        :rtype: bool
        """
        result = self.is_occurred
        self.is_occurred = False
        return result

@register_component("packet_factory.Agv")
class AGV:
    def __init__(self, id: int, x: float, y: float, point_id: int, velocity: float, graph: Graph):
        """
        :param id: AGV ID
        :param x: 坐标 X
        :param y: 坐标 Y
        :param velocity: 移动速度
        """
        self.id: int = id
        self.x: float = x
        self.y: float = y
        self.point_id = point_id
        self.path_stage = 1
        self.graph: Graph = graph
        self.timer: float = 0.0
        self.velocity: float = velocity
        self.operation: Optional[Operation] = None
        self.todo_queue: List[Tuple[str, Machine | Operation]] = []
        self.running_queue: List[Tuple[str, Machine | Operation]] = []

        self.status = AGVStatus.READY
        
        # todo: 通过yaml配置是否开启、随机种子、随机概率
        self.uncertainty_simulator = AGVUncertaintySimulator()
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
            f"operation={operation_name}> "
            f"status={self.status}> "
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
            LOGGER.info(f"AGV id={self.id} Operation clear.")

    def get_status(self) -> AGVStatus:
        return self.status

    def set_status(self, status: AGVStatus):
        self.status = status

    def dist(self, target_x: float, target_y: float) -> float:
        """
        计算与给定坐标之间的距离
        """
        dx = self.x - target_x
        dy = self.y - target_y
        return math.sqrt(dx * dx + dy * dy)

    def load_from_warehouse(self, operation: Operation):
        """
        将AGV从仓库中获取operation, 目前没有仓库, 直接赋值
        """
        self.set_operation(operation)
        self.status = AGVStatus.LOADED

    # ---------- ready和assigned态使用 ----------
    def load(self, operation: Operation, final_time: float) -> bool:
        """
        从machine上获得对应的operation
        :return: 是否成功, 若失败需要在下一轮step重新调用该函数
        """
        
        if self.status == AGVStatus.READY:
            self.set_status(AGVStatus.ASSIGNED)

        if self.status != AGVStatus.ASSIGNED:
            LOGGER.info(f"AGV id={self.id} is already loading an operation id={self.operation}")
            return False

        if operation.current_machine is None:
            LOGGER.warning(f"Operation id={operation.id} is not assigned to any machine")
            return False
        machine: Machine = operation.current_machine

        path = self.graph.get_path(self.point_id, machine.point_id)
        if not self.heading(machine, path, final_time):
            return False

        self.timer = max(self.timer, machine.get_timer())

        if operation.get_status() == OperationStatus.MOVING:
            # 上个阶段结束顺利获得物料
            self.set_status(AGVStatus.LOADED)
            self.set_operation(operation)
            # operation.set_status(OperationStatus.MOVING)
            operation.set_current_machine(None)
            machine.output_pop_operation(operation)
        else:
            LOGGER.info(f"Machine id={machine.id} is not finished.")
            return False

        self.point_id = machine.point_id
        self.path_stage = 1
        return True

    # ---------- assigned和loaded态使用 ----------
    def heading(self, machine: Machine, path: List[int], final_time: float) -> bool:
        """
        将AGV前往machine
        :return: 是否成功, 若失败则调用该函数的上一级步骤也失败
        """
        
        # todo: 维护一个agv的状态（event队列去修改的），如果当前agv状态=宕机，把self.timer变成final_time，但是不移动坐标

        # todo: 现在的改成：随机生成宕机若干秒的事件

        # update event
        # check state


        if self.status != AGVStatus.ASSIGNED and self.status != AGVStatus.LOADED:
            LOGGER.info(f"AGV id={self.id} can't go to point {path[-1]}")
            return False

        while self.path_stage < len(path):
            point = self.graph.get_point_by_id(path[self.path_stage])
            if point is None:
                LOGGER.info(f"AGV id={self.id} can't go to point {path[self.path_stage]}")
                return False
            nx, ny = point.get_xy()
            distance = self.dist(nx, ny)
            travel_time = distance / self.velocity
            agv_operation_id = None if self.operation is None else self.operation.id
            travel_time *= self.uncertainty_simulator.uncertain_event_ratio(self.id, machine.id, agv_operation_id)

            if self.get_timer() + travel_time > final_time:
                agv_x, agv_y = self.get_xy()
                dx: float = nx - agv_x
                dy: float = ny - agv_y
                agv_x = agv_x + dx * (final_time - self.get_timer()) / travel_time
                agv_y = agv_y + dy * (final_time - self.get_timer()) / travel_time
                self.set_xy(agv_x, agv_y)
                self.set_timer(final_time)
                return False

            self.set_xy(nx, ny)
            self.timer += travel_time

            self.path_stage += 1

        return True

    # ---------- loaded态使用 ----------
    def unload(self, machine: Machine, final_time: float) -> bool:
        """
        将AGV上的operation卸载到对应machine上
        :return: 是否成功, 若失败需要在下一轮step重新调用该函数
        """
        if self.status is not AGVStatus.LOADED:
            LOGGER.info(f"AGV id={self.id} is not loaded")
            return False
        
        if self.operation is None:
            LOGGER.warning(f"AGV id={self.id} has no operation")
            return False

        path = self.graph.get_path(self.point_id, machine.point_id)
        if not self.heading(machine, path, final_time):
            return False
        
        agv_operation: Operation = self.operation
        machine.input_push_operation(agv_operation)
        agv_operation.set_current_machine(machine)
        agv_operation.set_status(OperationStatus.WORKING)

        self.set_status(AGVStatus.READY)
        self.set_operation(None)

        machine.set_timer(max(machine.get_timer(), self.timer))
        machine.work(final_time)

        self.point_id = machine.point_id
        self.path_stage = 1
        return True

    def todo_queue_push(self, todo: Tuple[str, Machine | Operation]):
        self.todo_queue.append(todo)

    def todo_queue_pop(self) -> Optional[Tuple[str, Machine | Operation]]:
        if len(self.todo_queue) == 0:
            return None
        else:
            return self.todo_queue.pop(0)

    def todo_queue_is_empty(self):
        return len(self.todo_queue) == 0
    
    def todo_queue_clear(self):
        self.todo_queue.clear()
    
    def running_queue_push(self, todo: Tuple[str, Machine | Operation]):
        self.running_queue.append(todo)

    def running_queue_pop(self) -> Optional[Tuple[str, Machine | Operation]]:
        if len(self.running_queue) == 0:
            return None
        else:
            return self.running_queue.pop(0)
        
    def running_queue_is_empty(self):
        return len(self.running_queue) == 0

    def push_process(self,final_time: float):
        """
        执行队列中的任务, running队列代表执行了一半不能被中断的任务, todo队列代表还没被分配可以重新分配的任务
        """
        while True:
            if self.running_queue_is_empty():
                if self.todo_queue_is_empty():
                    return
                else:
                    todo_load = self.todo_queue[0]
                    todo_unload = self.todo_queue[1]

                    if todo_load[0] == "load":
                        if type(todo_load[1]) != Operation:
                            raise ValueError(f"Invalid todo type: {todo_load}")
                        
                        # 如果operation是等待状态, 前序operation的机器没有处理完成, 则直接返回, 等待下次调用再处理
                        if todo_load[1].get_status() == OperationStatus.WAITING:
                            return
                        
                        assert todo_load[1].get_status() == OperationStatus.READY, f"{todo_load[1]} is not ready"
                        
                        todo_load[1].set_status(OperationStatus.MOVING) # 修改Operation的状态, 代表已经开始执行了, 不能被中断
                        last_machine = todo_load[1].get_current_machine()
                        if last_machine is None:
                            # 从头开始
                            self.load_from_warehouse(todo_load[1])
                            self.todo_queue_pop()
                        else:
                            self.todo_queue_pop()
                            self.running_queue_push(("load", todo_load[1]))
                    else:
                        raise ValueError(f"Invalid todo type: {todo_load}")
                            
                    if todo_unload[0] == "unload":
                        if type(todo_unload[1]) != Machine:
                            raise ValueError(f"Invalid todo type: {todo_unload}")
                        self.todo_queue_pop()
                        self.running_queue_push(("unload", todo_unload[1]))
                    else:
                        raise ValueError(f"Invalid todo type: {todo_unload}")


            todo = self.running_queue[0]
            LOGGER.info(f"AGV id={self.id} current todo: {todo}")
            if todo[0] == "load":
                if type(todo[1]) != Operation:
                    raise ValueError(f"Invalid todo type: {todo}")
                if self.load(todo[1], final_time):
                    self.running_queue_pop()
                else:
                    return
            elif todo[0] == "unload":
                if type(todo[1]) != Machine:
                    raise ValueError(f"Invalid todo type: {todo}")
                if self.unload(todo[1], final_time):
                    self.running_queue_pop()
                else:
                    return


    def work(self, final_time: float, action: Optional[Tuple[Operation, Machine]] = None):
        """
        向todo队列中加入任务, 执行队列中的任务
        :param final_time: 模拟的截止时间
        :param action: 最新待执行的任务
        """
        if action is not None:
            self.todo_queue_push(("load", action[0]))
            self.todo_queue_push(("unload", action[1]))
            LOGGER.info(f"AGV id={self.id} assigned todo: {action}")
        self.push_process(final_time)




if __name__ == '__main__':
    k = 10
    agvs = []
    for i in range(k):
        x = float(1)
        y = float(1)
        velocity = float(1)
        agvs.append(AGV(i, x, y, velocity))
