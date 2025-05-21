from cmd import PROMPT

from .BaseAgent import BaseAgent
from typing import List, Optional, Tuple
from sky_dag_rl.sky_dag.sky_env.Graph.Machine import Machine
from sky_dag_rl.sky_dag.sky_env.Graph.Operation import Operation
from sky_dag_rl.sky_dag.sky_env.Graph.AGV import AGV

import time
import random

# Agent:
# input: 状态
# output: [(Operation, AGV, Machine), ...] （job可以混合）


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

    def sample(self, agvs, machines, jobs):
        """
        返回本次采样结果
        """
        time_start = time.time()
        current_sample = []

        cnt =0
        for i, job in enumerate(jobs):
            if job.is_finished():
                cnt+=1
                continue

            for j in range(job.get_operation_count()):
                op: Operation = job.get_operation(j)
                # todo to fix 状态转移需要调整
                # print(op.get_status())
                if op.get_status() != "ready":
                    continue


                # 随机选择可处理当前操作的机器
                # todo to fix 均为ready状态没有决策
                valid_machines = [m for m in machines if op.is_machine_capable(m.id) and m.is_available()]
                machine = random.choice(valid_machines) if valid_machines else None

                # 随机选择可用AGV（考虑当前是否正在运输）
                available_agvs = [agv for agv in agvs if agv.is_available()]
                agv = random.choice(available_agvs) if available_agvs else None
                # print(machine, agvs, agv)

                # 如果有机器和AGV则分配任务
                if agv and op and machine:
                    # 都存在 添加该op的调度
                    current_sample.append((op, agv, machine))
                else:
                    continue

        time_end = time.time()
        if cnt == len(jobs):
            self.alive=False
            return [],233
        return current_sample, (time_end - time_start)*500+1

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.agent_id} name={self.name}>"