from .BaseAgent import BaseAgent
from typing import List, Optional
from sky_executor.packet_factory.packet_factory.packet_factory_env.Machine.Machine import Machine
from sky_executor.packet_factory.packet_factory.packet_factory_env.Job.Operation import Operation
from sky_executor.packet_factory.packet_factory.packet_factory_env.Agv.AGV import AGV
import time

from sky_executor.utils.registry import register_component
from sky_logs.logger import LOGGER


@register_component("packet_factory.GreedyAgent")
class GreedyAgent(BaseAgent):
    def __init__(self, name=None, agent_id=None, context=None):
        """
        贪心策略智能体
        :param name: 智能体名称
        :param agent_id: 智能体ID或唯一标识
        :param context: 可选的上下文或环境句柄
        """
        super().__init__(name, agent_id, context)

    def get_min_machine(self, machines: List[Machine], operation: Operation) -> Machine:
        min_timer = float("inf")
        min_machine: Machine = machines[0]
        for machine in machines:
            if operation.is_machine_available(machine.get_id()) and machine.get_timer() < min_timer:
                min_timer = machine.get_timer()
                min_machine = machine
        return min_machine

    def get_min_agv(self, agvs: List[AGV]) -> AGV:
        min_timer = float("inf")
        min_agv: AGV = agvs[0]
        for agv in agvs:
            if agv.get_timer() < min_timer:
                min_timer = agv.get_timer()
                min_agv = agv
        return min_agv

    def reward(self, *args, **kwargs):
        """Agent 计算自身的reward"""
        pass

    def train(self, *args, **kwargs):
        """GreedyAgent 不需训练"""
        pass

    def sample(self, agvs, machines, jobs):
        """
        返回本次采样结果
        """
        time_start = time.time()
        current_sample = []
        total_timer = 0.0
        for i, job in enumerate(jobs):
            machine: Optional[Machine] = None
            for j in range(job.get_operation_count()):
                op = job.get_operation(j)
                if machine is None and op:
                    machine = self.get_min_machine(machines, op)
                min_agv = self.get_min_agv(agvs)
                if j == 0 and min_agv and op and machine:
                    min_agv.set_operation(op)
                elif min_agv and machine:
                    current_op = min_agv.get_operation()
                    if current_op:
                        new_machine = self.get_min_machine(machines, current_op)
                        if new_machine:
                            machine = new_machine
                LOGGER.info(
                    f"Job {i}, Operation {j}: AGV={min_agv.get_id() if min_agv else -1}, Machine={machine.get_id() if machine else -1}, Duration={op.get_duration(machine.get_id()) if op and machine else 0}")
                current_sample.append((op, min_agv, machine))
                if machine:
                    total_timer = max(total_timer, machine.get_timer())
        time_end = time.time()
        return current_sample, time_end - time_start
