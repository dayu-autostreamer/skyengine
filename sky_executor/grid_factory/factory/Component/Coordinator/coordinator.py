"""
@Project ：SkyEngine
@File    ：coordinator.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 22:37
"""

from sky_executor.grid_factory.factory.Component.JobSolver.template_solver.job_solver import (
    JobSolver,
)
from sky_executor.grid_factory.factory.Component.RouteSolver.template_solver.route_solver import (
    RouteSolver,
)
from sky_executor.grid_factory.factory.Component.Assigner.template_assigner.assigner import (
    Assigner,
)
from sky_executor.grid_factory.factory.Component.RouteSolver.route_solver_factory import \
    RouteSolverFactory
from sky_executor.grid_factory.factory.Component.JobSolver.job_solver_factory import JobSolverFactory
from sky_executor.grid_factory.factory.Component.Assigner.assigner_factory import AssignerFactory


class Coordinator:
    """
    每次step时都进行调用。

    支持运输感知: 通过 transfer_time_estimator 参数传入真实运输时间预估，
    FJSP 调度器会在机器选择时考虑运输代价。
    """

    def __init__(
            self,
            job_solver: JobSolver|str = None,
            route_solver: RouteSolver|str = None,
            assigner: Assigner|str = None,
            job_solver_kwargs: dict = None,
            route_solver_kwargs: dict = None,
            assigner_kwargs: dict = None,
            transfer_time_estimator=None,
    ):
        self.transfer_time_estimator = transfer_time_estimator

        # RouteSolver 初始化
        if isinstance(route_solver, str):
            self.route_solver = RouteSolverFactory.create(route_solver, **(route_solver_kwargs or {}))
        elif route_solver is not None:
            self.route_solver = route_solver
        else:
            # todo 删了
            self.route_solver = RouteSolverFactory.create("astar")

        # JobSolver 初始化 — 注入 transfer_time_estimator
        if job_solver_kwargs is None:
            job_solver_kwargs = {}
        if transfer_time_estimator is not None and "transfer_time_estimator" not in job_solver_kwargs:
            job_solver_kwargs["transfer_time_estimator"] = transfer_time_estimator

        if isinstance(job_solver, str):
            self.job_solver = JobSolverFactory.create(job_solver, **(job_solver_kwargs or {}))
        elif job_solver is not None:
            self.job_solver = job_solver
        else:
            # todo 删了
            self.job_solver = JobSolverFactory.create("greedy", **(job_solver_kwargs or {}))

        # Assigner 初始化
        if isinstance(assigner, str):
            self.assigner = AssignerFactory.create(assigner, **(assigner_kwargs or {}))
        elif assigner is not None:
            self.assigner = assigner
        else:
            self.assigner = AssignerFactory.create("random")

    def reset(self):
        """Reset components that keep episode-local state."""
        for component in (self.job_solver, self.route_solver, self.assigner):
            reset = getattr(component, "reset", None)
            if reset is not None:
                reset()

    def decide(self, obs):
        # 解包输入
        job_observation = obs.get("job_observation", None)  # 当前的Job，解析出任务
        assert job_observation is not None, "请提供机器观测信息"
        agent_observation = obs.get("agent_observation", None)  # Pogema处理即可
        assert agent_observation is not None, "请提供智能体观测信息"
        task_observation = obs.get("task_observation", None)  # 当前完成任务的AGV、任务列表、Machine列表等
        assert task_observation is not None, "请提供任务观测信息"

        # 1 获取 Job 层计划
        job_decision = self.job_solver.plan(job_observation)

        # 2 获取 环境状态 并分配
        assign_decision = self.assigner.plan(task_observation)
    
        # 3 获取 Route 层动作
        if getattr(self.route_solver, "accepts_task_observation", False):
            route_decision = self.route_solver.plan(
                agent_observation,
                task_observation=task_observation,
            )
        else:
            route_decision = self.route_solver.plan(agent_observation)

        # 4 任务结算层,确定当前已经完成的任务,交付给协调器
        return {
            "job_actions": job_decision,
            "agent_actions": route_decision,
            "assign_actions": assign_decision,
        }
