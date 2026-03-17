# 贪心的assigner

from joint_sim.component.Assigner.assigner_factory import \
    AssignerFactory
from joint_sim.component.Assigner.template_assigner.assigner import \
    Assigner


@AssignerFactory.register_solver("greedy")
class GreedyNearestAssigner(Assigner):
    def assign(self, agent_idx):
        pending = self.get_pending_transfers()
        if not pending:
            return None

        # 获取 AGV 当前坐标
        agent_pos = self.env.agents[agent_idx].pos

        # 找距离最近的任务 (from_machine -> to_machine)
        def distance(task):
            from_pos = self.env.machines[task["from_machine"]].pos
            return abs(agent_pos[0] - from_pos[0]) + abs(agent_pos[1] - from_pos[1])

        task = min(pending, key=distance)
        self.mark_assigned(task, agent_idx)
        return task
