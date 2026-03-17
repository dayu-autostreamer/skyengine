"""
最少拥堵任务分配器
基于路径拥堵情况，选择通过较少拥堵区域的任务进行分配
"""

from typing import Dict, Any, List
from joint_sim.component.Assigner.assigner_factory import AssignerFactory
from joint_sim.component.Assigner.template_assigner.assigner import Assigner
from joint_sim.utils.structure import RoutingTask, Machine, AGV


@AssignerFactory.register_solver("least_congestion")
class LeastCongestionAssigner(Assigner):
    """
    基于路径拥堵的任务分配器
    优先分配经过较少其他 AGV 的路径
    """

    def __init__(self):
        super().__init__()
        self.agv_position_history = {}

    def plan(self, obs: Dict[str, Any]):
        """
        基于拥堵情况的任务分配
        统计路径上的 AGV 数量，优先选择拥堵较少的路径
        """
        agents: List[AGV] = obs.get("agents", [])
        machines: List[Machine] = obs.get("machines", [])
        transfers_to_assign: List[RoutingTask] = obs.get("pending_transfers", [])

        if not agents or not machines:
            return {"assignments": {}, "pending_transfers": transfers_to_assign}

        # 记录 AGV 当前位置（用于评估拥堵）
        agent_positions = {agent.id: agent.pos for agent in agents}

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

            agent_pos = agent.pos

            # 评估每个任务的路径拥堵程度
            def calc_congestion_score(task: RoutingTask):
                # 获取源和目标机器位置
                source_machine_id = task.source[0] if isinstance(task.source, tuple) else task.source
                
                source_pos = None
                dest_pos = task.destination
                
                for machine in machines:
                    if machine.id == source_machine_id:
                        source_pos = machine.location
                        break
                
                if not source_pos or not dest_pos:
                    return float('inf')

                # 计算路径长度
                path_length = (abs(source_pos[0] - dest_pos[0]) + 
                             abs(source_pos[1] - dest_pos[1]))
                
                # 统计路径附近的其他 AGV 数量（简化：只看端点）
                congestion = 0
                for other_id, other_pos in agent_positions.items():
                    if other_id != agv_id:
                        # 距离源或目标较近的 AGV 会增加拥堵评分
                        if (abs(other_pos[0] - source_pos[0]) + abs(other_pos[1] - source_pos[1])) < 5:
                            congestion += 1
                        if (abs(other_pos[0] - dest_pos[0]) + abs(other_pos[1] - dest_pos[1])) < 5:
                            congestion += 1

                # 综合评分：距离 + 拥堵权重
                distance = abs(agent_pos[0] - source_pos[0]) + abs(agent_pos[1] - source_pos[1])
                score = distance + congestion * 2  # 拥堵权重为 2

                return score

            # 选择拥堵评分最低的任务
            least_congestion_task = min(available_tasks, key=calc_congestion_score)
            available_tasks.remove(least_congestion_task)
            
            # 分配目标机器位置
            if least_congestion_task.destination is None and machines:
                least_congestion_task.destination = machines[0].location
            
            assignments[agv_id] = least_congestion_task

        return {"assignments": assignments, "pending_transfers": available_tasks}
