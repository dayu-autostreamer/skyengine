"""
@Project ：SkyEngine
@File    ：coordinator.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 22:37
"""

from joint_sim.component.JobSolver.template_solver.job_solver import (
    JobSolver,
)
from joint_sim.component.RouteSolver.template_solver.route_solver import (
    RouteSolver,
)
from joint_sim.component.Assigner.template_assigner.assigner import (
    Assigner,
)
from joint_sim.component.RouteSolver.route_solver_factory import RouteSolverFactory
from joint_sim.component.JobSolver.job_solver_factory import JobSolverFactory
from joint_sim.component.Assigner.assigner_factory import AssignerFactory


class Coordinator:
    """
    每次step时都进行调用。
    """

    def __init__(
        self,
        job_solver: JobSolver | str = None,
        route_solver: RouteSolver | str = None,
        assigner: Assigner | str = None,
    ):
        if isinstance(job_solver, str):  # 创建
            self.job_solver = JobSolverFactory.create(job_solver)
        elif isinstance(job_solver, JobSolver):  # 已经是实例，直接使用
            self.job_solver = job_solver
        elif job_solver is None:  # 默认
            self.job_solver = JobSolverFactory.create("greedy")

        if isinstance(route_solver, str):  # 创建
            self.route_solver = RouteSolverFactory.create(route_solver)
        elif isinstance(route_solver, RouteSolver):  # 已经是实例，直接使用
            self.route_solver = route_solver
        elif route_solver is None:  # 默认
            self.route_solver = RouteSolverFactory.create("astar")

        if isinstance(assigner, str):  # 创建
            self.assigner = AssignerFactory.create(assigner)
        elif isinstance(assigner, Assigner):  # 已经是实例，直接使用
            self.assigner = assigner
        elif assigner is None:  # 默认
            self.assigner = AssignerFactory.create("random")
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
        route_decision = self.route_solver.plan(agent_observation)

        # 4 任务结算层,确定当前已经完成的任务,交付给协调器
        return {
            "job_actions": job_decision,
            "agent_actions": route_decision,
            "assign_actions": assign_decision,
        }
