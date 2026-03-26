# 从可行解中随机抽一个分配给当前的agent

import random
from typing import Dict, Any, List

from joint_sim.component.Assigner.assigner_factory import (
    AssignerFactory,
)
from joint_sim.component.Assigner.template_assigner.assigner import (
    Assigner,
)
from joint_sim.utils.structure import (
    RoutingTask,
    Machine,
)


@AssignerFactory.register_solver("random")
class RandomAssigner(Assigner):
    def plan(self, obs: Dict[str, Any]):
        """
        随机任务分配器
        -------------------
        输入:
            obs: 环境观测信息，包括：
                {
                    "pending_transfers": list[RoutingTask],
                    "machines": list[Machine],
                    "agents": list[AGV],  # 每个AGV对象至少应有 id 或 agv_id 字段
                }

        输出:
            assignments: dict # 当前已分配的job
                    {
                        "agv_id": int,
                        "task": RoutingTask 或 None
                    },
            pending_transfers:list[RoutingTask]  # 剩余的job
        """
        agents = obs.get("agents", [])
        machines: List[Machine] = obs.get("machines", [])
        transfers_to_assign: List[RoutingTask] = obs.get("pending_transfers", [])

        if not agents:
            return None

        # 安全检查：确保 machines 列表不为空（修复"Cannot choose from an empty sequence"错误）
        if not machines:
            assignments = {agent.id: None for agent in agents}
            return {"assignments": assignments, "pending_transfers": transfers_to_assign}

        # 为防止重复分配，同步维护一份待分配池
        available_tasks = transfers_to_assign.copy()
        assignments = {}
        for agent in agents:
            agv_id = agent.id
            if not available_tasks:
                # 没任务可分配
                assignments[agv_id] = None
                continue
            elif agent.current_task is not None:
                # 当前任务不为空，无法分配新任务
                assignments[agv_id] = None
                continue
            # 随机选取一个任务
            task = random.choice(available_tasks)
            available_tasks.remove(task)

            # [修复] 正确设置任务目标位置
            # 1. 如果任务有 candidate_machines，从中选择一个机器
            # 2. 否则随机选择一个机器
            if task.candidate_machines:
                # 从候选机器中选择
                valid_machines = [m for m in machines if m.id in task.candidate_machines]
                if valid_machines:
                    target_machine = random.choice(valid_machines)
                else:
                    # 候选机器不在 machines 列表中，随机选择
                    target_machine = random.choice(machines)
            else:
                # 无候选机器，随机选择
                target_machine = random.choice(machines)

            task.destination = target_machine.location
            assignments[agv_id] = task
        actions = {"assignments": assignments, "pending_transfers": available_tasks}
        return actions
