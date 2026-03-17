"""
Joint Simulation Environment for MAPF + JSSP
A unified simulation framework combining Multi-Agent Path Finding and Job Shop Scheduling.
"""

__version__ = "0.1.6"
__author__ = "Skyrim Forestsea"

from joint_sim.grid_factory_env import GridFactoryEnv
from joint_sim.io import create_env_from_config
from joint_sim.proxy import GridFactoryProxy, ExecutionStatus
from joint_sim.utils import *
from joint_sim.component import (
    BaseSolver,
    Coordinator,
    JobSolverFactory,
    RouteSolverFactory,
    AssignerFactory,
)

__all__ = [
    # 核心环境
    "GridFactoryEnv",
    "GridFactoryProxy",
    "ExecutionStatus",
    # IO
    "create_env_from_config",
    # Utils - 数据结构
    "Operation",
    "Job",
    "Machine",
    "MachineConfig",
    "JobConfig",
    "JobSolverResult",
    "RoutingTask",
    "AGV",
    "DispatchRule",
    # Utils - 枚举
    "ObsType",
    "OnTargetType",
    "CollisionSystem",
    "ActionType",
    # Utils - 生成器
    "generate_jobs",
    "MachineGenerator",
    "generate_machines",
    "revert_to_relative",
    "revert_to_absolute",
    # Utils - 绘图
    "draw_svg",
    "draw_svg_with_machines_and_targets",
    "pretty_print_step",
    "pretty_print_jobs",
    "refactor_drawing_render",
    "get_relative_position",
    # Component
    "BaseSolver",
    "Coordinator",
    "JobSolverFactory",
    "RouteSolverFactory",
    "AssignerFactory",
    # 元信息
    "__version__",
]
