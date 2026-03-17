"""
最近距离任务分配器
根据 AGV 到任务源位置的距离，选择最近的任务进行分配
"""

from typing import Dict, Any, List
from joint_sim.component.Assigner.assigner_factory import AssignerFactory
from joint_sim.component.Assigner.template_assigner.assigner import Assigner
from joint_sim.utils.structure import RoutingTask, Machine, AGV


@AssignerFactory.register_solver("nearest")
class NearestAssigner(Assigner):
    """
    贪心最近距离任务分配器
    """

    def plan(self, obs: Dict[str, Any]):
        """
        基于距离的任务分配
        优先分配距离 AGV 最近的任务源位置
        """
        agents: List[AGV] = obs.get("agents", [])
        machines: List[Machine] = obs.get("machines", [])
        transfers_to_assign: List[RoutingTask] = obs.get("pending_transfers", [])

        if not agents or not machines:
            return {"assignments": {}, "pending_transfers": transfers_to_assign}

        available_tasks = transfers_to_assign.copy()
        assignments = {}

        for agent in agents:
            agv_id = agent.id
            
            # AGV 已有任务，跳过
            if agent.current_task is not None:
                assignments[agv_id] = None
                continue

            if not available_tasks:
                assignments[agv_id] = None
                continue

            # 计算 AGV 到各任务源的距离
            agent_pos = agent.pos
            
            def calc_distance(task: RoutingTask):
                # task.source 是 (machine_id, 0) 格式
                source_machine_id = task.source[0] if isinstance(task.source, tuple) else task.source
                
                # 查找对应机器的位置
                for machine in machines:
                    if machine.id == source_machine_id:
                        return abs(agent_pos[0] - machine.location[0]) + abs(agent_pos[1] - machine.location[1])
                return float('inf')

            # 选择距离最近的任务
            nearest_task = min(available_tasks, key=calc_distance)
            available_tasks.remove(nearest_task)
            
            # 分配目标机器位置
            if nearest_task.destination is None and machines:
                nearest_task.destination = machines[0].location
            
            assignments[agv_id] = nearest_task

        return {"assignments": assignments, "pending_transfers": available_tasks}
