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
from sky_executor.grid_factory.factory.grid_factory_env.Component.Assigner.template_assigner.assigner import (
    BaseAssigner,
)


class Coordinator:
    """
    每次step时都进行调用。
    """

    def __init__(
        self,
        job_solver: JobSolver = None,
        route_solver: RouteSolver = None,
        assigner: BaseAssigner = None,
    ):

        self.job_solver = job_solver if job_solver is not None else JobSolver()
        self.route_solver = route_solver if route_solver is not None else RouteSolver()
        self.assigner = assigner if route_solver is not None else BaseAssigner()

    def decide(self, obs):
        # 解包输入
        job_observation = obs.get("job_observation", None) # 当前的Job，解析出任务
        assert job_observation is not None, "请提供机器观测信息"
        agent_observation = obs.get("agent_observation", None) # Pogema处理即可
        assert agent_observation is not None, "请提供智能体观测信息"
        task_observation = obs.get("task_observation", None) # 当前完成任务的AGV、任务列表、Machine列表等
        assert task_observation is not None, "请提供任务观测信息"

        # 1 获取 Job 层计划
        job_decision = self.job_solver.plan(job_observation)
        # job_actions = job_decision["job_actions"]
        transfer_requests = job_decision["transfer_requests"]  # 获取转移请求

        # 2 获取 环境状态 并分配
        assign_decision = self.assigner.plan(task_observation)

        # 3 获取 Route 层动作
        route_decision = self.route_solver.plan(agent_observation)

        # 4 任务结算层,确定当前已经完成的任务,交付给协调器

        return {
            "job_actions": transfer_requests,
            "agent_actions": route_decision,
            "assign_actions": assign_decision,
        }

