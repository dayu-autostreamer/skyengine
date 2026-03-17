# 根据当前环境中的pending_transfer的任务，和agv、machine本身的特点和信息，
# 从pending_transfer任务与可行的machine中按照一定策略构建一个,分配给当前的agent

from abc import ABC, abstractmethod

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class Assigner(ABC):
    """
    任务分配器基类（Assigner）
    - 输入：agent_idx、环境观测信息 obs
    - 输出：为 agents 分配的任务 (transfers) 或 None
    """

    def plan(
            self,
            obs: Dict[str, Any]
    ):
        """
        输入：
            obs: 环境观测信息，包括：
                {
                    "pending_transfers": list[RoutingTask],
                    "machines": list[Machine],
                    "agents": list[AGV],  # Agent本身应该提供什么信息呢
                }

        输出：
            assignments: list[dict]
                [
                    {
                        "agv_id": int,
                        "task": RoutingTask 或 None
                    },
                ]
            pending_transfers:list[RoutingTask]
        """
        pass
