"""
Component 模块 - 调度与路由组件

此模块包含调度、路由、分配三大核心组件及其工厂类。

====== 主要组件 ======
1. Coordinator - 协调器，统一调度 job_solver, route_solver, assigner
2. BaseSolver - 求解器基类

====== 工厂类 ======
1. JobSolverFactory - 任务调度求解器工厂
2. RouteSolverFactory - 路由求解器工厂
3. AssignerFactory - 分配器工厂

====== 可用算法 ======
JobSolver:
  - "greedy": 贪心调度
  - "best": 最优调度
  - "priority": 优先级调度

RouteSolver:
  - "astar": A* 路由
  - "greedy": 贪心路由
  - "instant": 即时路由
  - "mapf_gpt": GPT 路由

Assigner:
  - "nearest": 最近分配
  - "random": 随机分配
  - "load_balance": 负载均衡
  - "greedy": 贪心分配

====== 使用示例 ======
from joint_sim.component import Coordinator

# 方式1: 使用字符串创建
coordinator = Coordinator(
    job_solver="greedy",
    route_solver="astar",
    assigner="nearest"
)

# 方式2: 传入已创建的实例
from joint_sim.component.JobSolver.job_solver_factory import JobSolverFactory
job_solver = JobSolverFactory.create("greedy")
coordinator = Coordinator(job_solver=job_solver, ...)

# 决策
actions = coordinator.decide(observation)
"""

from joint_sim.component.BaseSolver import BaseSolver
from joint_sim.component.Coordinator.coordinator import Coordinator
from joint_sim.component.JobSolver.job_solver_factory import JobSolverFactory
from joint_sim.component.RouteSolver.route_solver_factory import RouteSolverFactory
from joint_sim.component.Assigner.assigner_factory import AssignerFactory

__all__ = [
    "BaseSolver",
    "Coordinator",
    "JobSolverFactory",
    "RouteSolverFactory",
    "AssignerFactory",
]
