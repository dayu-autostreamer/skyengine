# 从可行解中随机抽一个分配给当前的agent

import random
from sky_executor.grid_factory.factory.grid_factory_env.Component.Assigner.template_assigner import (
    BaseAssigner,
)


class RandomAssigner(BaseAssigner):
    def assign(self, agent_idx):
        pending = self.get_pending_transfers()
        if not pending:
            return None
        task = random.choice(pending)
        self.mark_assigned(task, agent_idx)
        return task
