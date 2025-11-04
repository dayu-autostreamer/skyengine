# 根据当前环境中的pending_transfer的任务，和agv、machine本身的特点和信息，
# 从pending_transfer任务与可行的machine中按照一定策略构建一个,分配给当前的agent

from abc import ABC, abstractmethod


class BaseAssigner(ABC):
    """
    Assigner 基类模板：
    - 输入: agent_idx, 当前 grid/环境状态
    - 输出: 分配给该 agent 的 transfer 任务 (dict) 或 None
    """

    def __init__(
        self,
    ):
        """
        - env.pending_transfers: 当前待执行的搬运任务列表
        - env.agents: AGV 列表，包含状态信息 (位置、是否空闲等)
        """
        pass

    def assign(self, agent_idx, pending_transfers, machines):
        """
        分配一个任务给指定 agent
        返回:
            pending_transfers: dict 或 None
            machines: list
        """
        pass
