"""
@Project ：SkyEngine
@File    ：model.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 23:02
"""

from joint_sim.component.JobSolver.template_solver.job_solver import (
    JobSolver,
)
from joint_sim.component.JobSolver.utils.op_priority_greedy import (
    priority_greedy,
)
from joint_sim.utils.structure import (
    JobSolverResult,
    RoutingTask,
)
from typing import List

#  在线动态调度 (Online Scheduling) 场景下：
# 环境本身就维护所有状态（机器是否忙、AGV是否空闲、任务是否完成）；
# JobSolver 每步都能从 obs 获取完整信息；
# → 因此可以是 无状态（stateless）决策器。


# 但是我们这里是离线静态调度 (Offline Scheduling) 所以还是需要维护缓存的。
# 暂时不接收新的job

from joint_sim.component.JobSolver.job_solver_factory import (
    JobSolverFactory,
)


@JobSolverFactory.register_solver("greedy")
class GreedyJobSolver(JobSolver):
    """
    离线贪心调度器：
    - 首次调用 plan() 时执行一次全局离线调度；
    - 后续每个时间片，根据当前时间 t 判断：
        - 是否有 operation 到达开始时间；
        - 是否有 transfer_request 到达 ready_time；
    - 只做时间推进，不再动态重新规划。
    """

    def __init__(self):
        super().__init__()
        self.initialized = False
        self.fixed_plan: JobSolverResult | None = None
        self.transfer_requests = []  # 待触发的转运请求
        self.time_stamp = 0
        self.task_idx = 0

    def create_routing_task(self, task_dict: dict) -> RoutingTask:
        """
        将任务字典（包含 job_id、op_id、from_machine、to_machine 等字段）
        转换为 RoutingTask 对象。
        """
        job_id = task_dict.get("job_id")
        op_id = task_dict.get("op_id")
        from_machine = task_dict.get("from_machine")
        to_machine = task_dict.get("to_machine")
        ready_time = task_dict.get("ready_time")
        # 起点为 from_machine（用 tuple 包装成坐标格式）
        source = (from_machine, 0) if isinstance(from_machine, int) else from_machine

        # 若 to_machine 有效，则指定 destination
        destination = (to_machine, 0) if to_machine is not None else None

        # 如果后续希望支持多目标机器，可以自动加入 candidate_machines
        candidate_machines = [to_machine] if to_machine is not None else []

        routing_task = RoutingTask(
            task_id=self.task_idx,
            job_id=job_id,
            op_id=op_id,
            source=source,
            destination=destination,
            candidate_machines=candidate_machines,
            ready_time=ready_time,
        )
        self.task_idx += 1
        return routing_task

    # 核心接口：每个时间步调用一次
    # ---------------------------------------------------------
    def plan(self, obs: dict) -> dict:
        """
        输入:
            obs = {
                "jobs": [Job],
                "machines": [Machine],
            }

        输出:
            {
                "transfer_requests": [RoutingTask]
            }
        """
        self.time_stamp = self.time_stamp + 1
        jobs = obs["jobs"]
        machines = obs["machines"]

        # === 第一次调用,初始化计划 ===
        if not self.initialized:
            print(
                f"\n[JobSolver] Initializing schedule with {len(jobs)} jobs and {len(machines)} machines"
            )
            # 检查所有Job的Operation
            total_ops = sum(len(job.ops) for job in jobs)
            print(f"[JobSolver] Total Operations: {total_ops}")
            for job in jobs:
                for op in job.ops:
                    if not op.machine_options:
                        print(
                            f"[ERROR] Job {job.job_id} Op {op.op_id} has EMPTY machine_options!"
                        )
                    else:
                        print(
                            f"[JobSolver] Job {job.job_id} Op {op.op_id}: machine_options={op.machine_options}"
                        )

            # 调用离线调度算法生成完整计划
            self.fixed_plan = priority_greedy(
                jobs,
                machines,
            )
            print(
                f"[JobSolver] Generated {len(self.fixed_plan.transfer_requests)} transfer requests"
            )
            if len(self.fixed_plan.transfer_requests) < total_ops - len(jobs):
                print(
                    f"[WARNING] Transfer requests ({len(self.fixed_plan.transfer_requests)}) "
                    f"< Expected ({total_ops - len(jobs)})"
                )
                print(f"[WARNING] Some operations may not be scheduled!")

            self.transfer_requests = [
                self.create_routing_task(task)
                for task in self.fixed_plan.transfer_requests
            ]
            self.transfer_requests.sort(key=lambda x: x.ready_time)
            self.initialized = True

        # === 检查是否有可启动的 转运任务 ===
        ready_transfers = self._trigger_ready_transfers(self.time_stamp)

        return {
            "transfer_requests": ready_transfers,
        }

    def _trigger_ready_transfers(self, current_time: float) -> List[RoutingTask]:
        """根据时间触发新的 transfer 请求"""
        ready_transfers = []
        while (
            self.transfer_requests
            and self.transfer_requests[0].ready_time <= current_time + 1e-6
        ):
            ready_transfers.append(self.transfer_requests.pop(0))
        return ready_transfers
