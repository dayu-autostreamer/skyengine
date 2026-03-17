"""
@Project ：SkyEngine
@File    ：solver.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/12/01 17:01
"""

from joint_sim.component.JobSolver.template_solver.job_solver import (
    JobSolver,
)
from joint_sim.component.JobSolver.utils.ORScheduler import (
    OptimalORToolsSolver,
)
from joint_sim.utils.structure import (
    JobSolverResult,
    RoutingTask,
)
from typing import List
from joint_sim.component.JobSolver.job_solver_factory import (
    JobSolverFactory,
)


# 最优调度器
@JobSolverFactory.register_solver("best")
class OptimalORToolsJobSolver(JobSolver):
    """
    离线最优调度器：
    - 首次调用 plan() 时执行一次全局离线调度；
    - 后续每个时间片，根据当前时间 t 判断：
        - 是否有 operation 到达开始时间；
        - 是否有 transfer_request 到达 ready_time；
    - 只做时间推进，不再动态重新规划。
    
    参数：
    - consider_agv_delay: 是否在最优化模型中考虑AGV运输时延（默认False）
      False: 假设AGV运输时间=0，更激进的调度
      True: 基于距离估计AGV运输时延，更现实的调度
    - n_agvs: AGV数量限制（默认None表示无限AGV）
    """

    def __init__(self, consider_agv_delay: bool = False, n_agvs: int = None):
        super().__init__()
        self.initialized = False
        self.fixed_plan: JobSolverResult | None = None
        self.transfer_requests = []  # 待触发的转运请求
        self.time_stamp = 0
        self.task_idx = 0
        self.solver = None
        self.consider_agv_delay = consider_agv_delay
        self.n_agvs = n_agvs

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
            print("\n[BestSolver] ========== STARTING OPTIMAL SOLVER ==========")
            print(f"[BestSolver] Configuration: consider_agv_delay={self.consider_agv_delay}, n_agvs={self.n_agvs}")
            print(f"[BestSolver] Jobs: {len(jobs)}, Machines: {len(machines)}")
            for job in jobs:
                ops_str = ", ".join([f"Op{op.op_id}(m={op.machine_options})" for op in job.ops])
                print(f"[BestSolver]   Job {job.job_id}: {ops_str}")
            
            # 调用离线调度算法生成完整计划
            self.solver = OptimalORToolsSolver(
                jobs,
                machines,
                consider_agv_delay=self.consider_agv_delay,
                n_agvs=self.n_agvs
            )
            self.fixed_plan = self.solver.solve()
            
            print(f"[BestSolver] Generated plan with makespan: {self.fixed_plan.stats.get('makespan', 'N/A')}")
            print(f"[BestSolver] Transfer requests: {len(self.fixed_plan.transfer_requests)}")
            
            # 打印机器调度
            for mid, tasks in self.fixed_plan.machine_schedule.items():
                ops_str = ", ".join([f"(J{jid}Op{oid}: {s}-{e})" for s,e,jid,oid in tasks])
                print(f"[BestSolver]   Machine {mid}: {ops_str}")
            
            # 打印transfer请求
            for tr in self.fixed_plan.transfer_requests[:5]:  # 只打印前5个
                print(f"[BestSolver]   Transfer: Job{tr['job_id']}Op{tr['op_id']} "
                      f"from M{tr['from_machine']} to M{tr['to_machine']} at t={tr['ready_time']}")
            if len(self.fixed_plan.transfer_requests) > 5:
                print(f"[BestSolver]   ... and {len(self.fixed_plan.transfer_requests) - 5} more transfers")
            
            self.transfer_requests = [
                self.create_routing_task(task)
                for task in self.fixed_plan.transfer_requests
            ]
            self.transfer_requests.sort(key=lambda x: x.ready_time)
            self.initialized = True
            print("[BestSolver] ========== OPTIMAL SOLVER READY ==========\n")

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
