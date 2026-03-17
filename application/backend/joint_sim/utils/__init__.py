"""
Utils 模块 - 数据结构与工具函数

此模块包含仿真环境使用的核心数据结构和工具函数。

====== 数据结构 ======
任务层:
  - Operation: 工序
  - Job: 任务
  - Machine: 机器

路由层:
  - RoutingTask: 路由任务
  - AGV: 自动导引车

配置类:
  - MachineConfig: 机器配置
  - JobConfig: 任务配置

结果类:
  - JobSolverResult: 调度结果

枚举:
  - DispatchRule: 调度规则 (SPT, LPT, EDD, FIFO, MWKR, MOPNR, FDD_MWKR)
  - ObsType: 观察类型
  - OnTargetType: 目标处理类型
  - CollisionSystem: 碰撞系统
  - ActionType: 动作类型

====== 工具函数 ======
生成器:
  - generate_jobs: 生成任务
  - generate_machines: 生成机器
  - MachineGenerator: 机器生成器类

绘图:
  - draw_svg: 绘制 SVG
  - draw_svg_with_machines_and_targets: 带机器和目标的 SVG
  - pretty_print_step: 打印步骤信息
  - pretty_print_jobs: 打印任务信息

====== 使用示例 ======
from joint_sim.utils import Operation, Job, Machine, RoutingTask, AGV

# 创建工序
op = Operation(
    job_id=0,
    op_id=0,
    machine_options=[0, 1],
    proc_time=5.0
)

# 创建任务
job = Job(job_id=0, ops=[op])

# 创建机器
machine = Machine(machine_id=0, location=(5, 5))

# 创建路由任务
task = RoutingTask(
    task_id=0,
    job_id=0,
    op_id=0,
    source=(0, 0),
    destination=(5, 5),
    ready_time=0.0
)

# 创建 AGV
agv = AGV(id=0, pos=(0, 0), current_task=None, finished_tasks=[])
"""

# 数据结构
from joint_sim.utils.structure import (
    # 任务层
    Operation,
    Job,
    Machine,
    # 配置类
    MachineConfig,
    JobConfig,
    # 结果类
    JobSolverResult,
    # 路由层
    RoutingTask,
    AGV,
    # 枚举
    DispatchRule,
)

# 枚举常量
from joint_sim.utils.env_const import (
    ObsType,
    OnTargetType,
    CollisionSystem,
    ActionType,
)

# 生成器
from joint_sim.utils.job import generate_jobs
from joint_sim.utils.machine import (
    MachineGenerator,
    generate_machines,
    revert_to_relative,
    revert_to_absolute,
)

# 绘图工具
from joint_sim.utils.pic_drawer import (
    draw_svg,
    draw_svg_with_machines_and_targets,
    pretty_print_step,
    pretty_print_jobs,
    refactor_drawing_render,
    get_relative_position,
)

__all__ = [
    # 任务层
    "Operation",
    "Job",
    "Machine",
    # 配置类
    "MachineConfig",
    "JobConfig",
    # 结果类
    "JobSolverResult",
    # 路由层
    "RoutingTask",
    "AGV",
    # 枚举
    "DispatchRule",
    "ObsType",
    "OnTargetType",
    "CollisionSystem",
    "ActionType",
    # 生成器
    "generate_jobs",
    "MachineGenerator",
    "generate_machines",
    "revert_to_relative",
    "revert_to_absolute",
    # 绘图
    "draw_svg",
    "draw_svg_with_machines_and_targets",
    "pretty_print_step",
    "pretty_print_jobs",
    "refactor_drawing_render",
    "get_relative_position",
]
