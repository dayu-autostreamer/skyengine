"""
负载均衡任务分配器
根据 AGV 已完成的任务数量，优先分配给任务较少的 AGV
"""

from typing import Dict, Any, List
from joint_sim.component.Assigner.assigner_factory import AssignerFactory
from joint_sim.component.Assigner.template_assigner.assigner import Assigner
from joint_sim.utils.structure import RoutingTask, Machine, AGV


@AssignerFactory.register_solver("load_balance")
class LoadBalanceAssigner(Assigner):
    """
    负载均衡任务分配器
    优先为任务完成数量较少的 AGV 分配任务
    """

    def plan(self, obs: Dict[str, Any]):
        """
        基于 AGV 工作负载的任务分配
        """
        agents: List[AGV] = obs.get("agents", [])
        machines: List[Machine] = obs.get("machines", [])
        transfers_to_assign: List[RoutingTask] = obs.get("pending_transfers", [])

        if not agents or not machines:
            return {"assignments": {}, "pending_transfers": transfers_to_assign}

        available_tasks = transfers_to_assign.copy()
        assignments = {}

        # 按已完成任务数排序 AGV（任务少的优先）
        sorted_agents = sorted(
            agents,
            key=lambda a: len(a.finished_tasks) if hasattr(a, 'finished_tasks') else 0
        )

        for agent in sorted_agents:
            agv_id = agent.id
            
            # AGV 已有任务，跳过
            if agent.current_task is not None:
                assignments[agv_id] = None
                continue

            if not available_tasks:
                assignments[agv_id] = None
                continue

            # 分配第一个可用任务（负载均衡倾向）
            task = available_tasks.pop(0)
            
            # 分配目标机器位置
            if task.destination is None and machines:
                task.destination = machines[0].location
            
            assignments[agv_id] = task

        # 处理其他 AGV（不在排序列表中的）
        for agent in agents:
            if agent.id not in assignments:
                assignments[agent.id] = None

        return {"assignments": assignments, "pending_transfers": available_tasks}
