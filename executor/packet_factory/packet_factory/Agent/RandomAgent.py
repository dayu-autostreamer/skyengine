from .BaseAgent import BaseAgent
from executor.packet_factory.packet_factory.packet_factory_env.Job.Operation import Operation
from executor.packet_factory.logger.logger import LOGGER
from executor.packet_factory.packet_factory.packet_factory_env.Utils.util import OperationStatus

import time
import random

# Agent:
# input: 状态
# output: [(Operation, AGV, Machine), ...] （job可以混合）

from executor.packet_factory.registry import register_component

@register_component("packet_factory.RandomAgent")
class RandomAgent(BaseAgent):
    def __init__(self, name=None, agent_id=None, context=None):
        """
        通用智能体基类
        :param name: 智能体名称
        :param agent_id: 智能体ID或唯一标识
        :param context: 可选的上下文或环境句柄
        """
        super().__init__(name, agent_id, context)

    def reward(self, *args, **kwargs):
        """Agent 计算自身的reward"""
        pass

    def train(self, *args, **kwargs):
        """GreedyAgent 不需训练"""
        pass

    def before_sample(self, *args, **kwargs):
        return 0

    def after_sample(self, *args, **kwargs):
        return 0

    def decision(self, *args, **kwargs):
        return 0
    def sample(self, agvs, machines, jobs):
        """
        返回本次采样结果
        """
        time_start = time.time()
        current_sample = []

        cnt: int = 0
        for i, job in enumerate(jobs):
            if job.is_finished():
                cnt += 1
                continue

            for j in range(job.get_operation_count()):
                op: Operation = job.get_operation(j)

                # 分配所有尚未开始执行的operation, 其状态为ready或者waiting
                if op.get_status() == OperationStatus.READY or op.get_status() == OperationStatus.WAITING: 

                    # 随机选择可处理当前操作的机器
                    valid_machines = [m for m in machines if op.is_machine_capable(m.id) and m.is_available()]
                    machine = random.choice(valid_machines) if valid_machines else None

                    # 随机选择可用AGV, 由于是对AGV的未来分配指令, 无需考虑当前是否正在运输
                    agv = random.choice(agvs) if agvs else None

                    # 如果有机器和AGV则分配任务
                    if agv and op and machine:
                        # 都存在, 添加该op的调度
                        current_sample.append((op, agv, machine))
                    else:
                        continue

        time_end = time.time()
        LOGGER.info(f"Finished jobs: {cnt}")
        if cnt == len(jobs):
            self.alive = False
            return [],0
        return current_sample, (time_end - time_start)*500+1

    def is_finish(self):
        # 分配完任务后，没有不确定性发生，那么仍执行原决策，不传入新决策
        decisions = []
        # 当全部任务执行完成时，也应该退出循环
        cnt = 0
        for job in self.jobs:
            if job.is_finished():
                cnt += 1
        if cnt == len(self.jobs):
            self.alive = False
            return True

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.agent_id} name={self.name}>"