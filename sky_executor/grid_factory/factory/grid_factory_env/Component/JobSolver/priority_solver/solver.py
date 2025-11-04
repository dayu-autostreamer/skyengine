"""
@Project ：SkyEngine
@File    ：solver.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 23:02
"""

from sky_executor.grid_factory.factory.grid_factory_env.Component.JobSolver.template_solver.job_solver import (
    JobSolver,
)
from sky_executor.grid_factory.factory.grid_factory_env.Component.JobSolver.utils.op_priority_greedy import (
    priority_greedy,
)
from sky_executor.grid_factory.factory.grid_factory_env.Utils.structure import (
    JobSolverResult,
)


#  在线动态调度 (Online Scheduling) 场景下：
# 环境本身就维护所有状态（机器是否忙、AGV是否空闲、任务是否完成）；
# JobSolver 每步都能从 obs 获取完整信息；
# → 因此可以是 无状态（stateless）决策器。


# 但是我们这里是离线静态调度 (Offline Scheduling) 所以还是需要维护缓存的。
# 不接收新的job


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
        self.pending_ops = []  # 尚未执行的操作
        self.active_ops = []  # 执行中的操作
        self.finished_ops = []  # 已完成的操作
        self.transfer_requests = []  # 待触发的转运请求
        self.time_stamp = 0

    def load_observation(self, env) -> dict:
        return {
            "jobs": env.jobs,
            "machines": env.machines,
        }

    # ---------------------------------------------------------
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
                "machine_actions": [...],
                "transfer_requests": [...]
            }
        """
        self.time_stamp = self.time_stamp + 1
        jobs = obs["jobs"]
        machines = obs["machines"]

        # === 初始化阶段 ===
        if not self.initialized:
            # 调用离线调度算法生成完整计划
            self.fixed_plan = priority_greedy(
                jobs,
                machines,
            )
            self.initialized = True
            # 缓存任务列表
            self._load_plan(self.fixed_plan)

        # === 检查是否有可启动的 转运任务 ===
        ready_transfers = self._trigger_ready_transfers(self.time_stamp)

        # === 4. 输出 ===
        return {
            "transfer_requests": ready_transfers,
        }

    # ---------------------------------------------------------
    # 辅助函数
    # ---------------------------------------------------------
    def _load_plan(self, plan: JobSolverResult):
        """把离线调度结果转换成 pending_ops / transfer_requests 缓存"""
        for mid, tasks in plan.machine_schedule.items():
            for s, e, jid, oid in tasks:
                self.pending_ops.append(
                    {
                        "machine_id": mid,
                        "job_id": jid,
                        "op_id": oid,
                        "start_time": s,
                        "expected_end": e,
                    }
                )
        self.transfer_requests = list(plan.transfer_requests)

    def _trigger_ready_transfers(self, current_time: float):
        """根据时间触发新的 transfer 请求"""
        ready_transfers = []
        for req in list(self.transfer_requests):
            if req["ready_time"] <= current_time + 1e-6:
                ready_transfers.append(req)
                self.transfer_requests.remove(req)
        return ready_transfers

    # ---------------------------------------------------------
    # 状态同步接口：由环境在每步执行后调用
    # ---------------------------------------------------------
    def update_after_step(self, infos: dict):
        """
        由环境反馈执行结果后调用：
        infos = {
            "finished_ops": [...],
            "finished_transfers": [...],
        }
        """
        finished_ops = infos.get("finished_ops", [])
        finished_transfers = infos.get("finished_transfers", [])

        # 更新 active_ops
        for fo in finished_ops:
            for op in list(self.active_ops):
                if op["job_id"] == fo["job_id"] and op["op_id"] == fo["op_id"]:
                    self.active_ops.remove(op)
                    self.finished_ops.append(op)
                    break

        # 更新 transfer_requests 状态
        for ft in finished_transfers:
            for req in list(self.transfer_requests):
                if req["job_id"] == ft["job_id"] and req["op_id"] == ft["op_id"]:
                    req["done"] = True
                    req["actual_ready_time"] = ft.get("time")
                    break

    def reset(self):
        """重置 solver 到未初始化状态"""
        self.initialized = False
        self.fixed_plan = None
        self.pending_ops.clear()
        self.active_ops.clear()
        self.finished_ops.clear()
        self.transfer_requests.clear()
        self.time_stamp = 0
