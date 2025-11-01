"""
@Project ：SkyEngine
@File    ：coordinator.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 22:37
"""

from sky_executor.grid_factory.factory.grid_factory_env.Component.JobSolver.template_solver.job_solver import (
    JobSolver,
)
from sky_executor.grid_factory.factory.grid_factory_env.Component.RouteSolver.template_solver.route_solver import (
    RouteSolver,
)


class Coordinator:
    """
    每次step时都进行调用。
    """

    def __init__(self, job_solver: JobSolver = None, route_solver: RouteSolver = None):
        if job_solver is not None:
            self.job_solver = job_solver
        if route_solver is not None:
            self.route_solver = route_solver

    def decide(self, obs):
        # 解包输入
        machine_observation = obs.get("machine_observation", None)
        assert machine_observation is not None, "请提供机器观测信息"
        agent_observation = obs.get("agent_observation", None)
        assert agent_observation is not None, "请提供智能体观测信息"

        # 1 获取 Job 层计划
        job_decision = self.job_solver.plan(machine_observation)
        machine_actions = job_decision["machine_actions"]
        transfer_requests = job_decision["transfer_requests"]

        # 3 获取 Route 层动作
        route_decision = self.route_solver.plan(agent_observation)

        # 4 任务结算层,确定当前已经完成的任务,交付给协调器

        return {"machine_actions": machine_actions, "agent_actions": route_decision}

    def assign(self):
        pass
