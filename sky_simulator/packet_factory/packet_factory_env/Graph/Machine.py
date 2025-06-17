import numpy as np
from typing import Optional, Tuple, List

from .Operation import Operation
from .util import OperationStatus, MachineStatus
from sky_simulator.packet_factory.packet_factory_env.Utils.logger import LOGGER

from sky_simulator.registry import register_component

class MachineUncertaintySimulator:
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

    def uncertain_event_ratio(self, machine_id, operation_id):
        """
        :param machine_id: 机器 ID
        :param operation_id: 操作 ID
        :return: 若随机事件发生, 返回实际机器执行时间和原始执行时间的比例, 否则返回1
        :rtype: float
        """
        key = (machine_id, operation_id)
        if key in self.cache:
            return self.cache[key]

        # 使用类内部的 rng 生成随机值
        random_value = self.rng.random()
        result = random_value < self.probability

        if result:
            LOGGER.info(f"Machine {machine_id} operation {operation_id} has uncertain event")
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

@register_component("packet_factory.Machine")
class Machine:
    def __init__(self, machine_id: int, x: float, y: float):
        """
        :param id_: 机器 ID
        :param x: 坐标 X
        :param y: 坐标 Y
        """

        self.id: int = machine_id
        self.x: float = x
        self.y: float = y
        self.timer: float = 0.0

        self.status: MachineStatus = MachineStatus.READY
        # 缓存的Operation
        self.input_queue: List[Operation] = []
        self.output_queue: List[Operation] = []

        # todo: 通过yaml配置是否开启、随机种子、随机概率
        self.uncertainty_simulator = MachineUncertaintySimulator()

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
            duration *= self.uncertainty_simulator.uncertain_event_ratio(self.id, current_operation.id)
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
        if self.get_status() == MachineStatus.READY or self.get_status() == MachineStatus.WORKING:
            self.push_process(final_time)
        else:
            LOGGER.info(f"Machine {self.id} is failed")

    # ---------- 模拟异常事件 ----------
    def machine_fail(self):
        self.status = MachineStatus.FAILED
