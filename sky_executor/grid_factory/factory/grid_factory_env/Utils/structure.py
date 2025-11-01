"""
@Project ：SkyEngine
@File    ：structure.py.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/17 19:27
"""

# 此处列举了常用的结构

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Callable
from pydantic import BaseModel


# ========= 任务层  =========
@dataclass
class Operation:
    job_id: int  # 任务编号
    op_id: int  # 工序编号
    machine_options: List[int]  # 可选的机器编号
    proc_time: int  # 处理时间
    release: float = 0  # 释放时间
    due: Optional[float] = None  # 最晚时间


@dataclass
class Job:
    job_id: int
    ops: List[Operation]


# class Machine:
#     m_id: int
@dataclass
class Machine:
    """Machine 逻辑节点"""

    def __init__(self, machine_id: int, location: Tuple[int, int]):
        self.id = machine_id
        self.location = location

    def __repr__(self):
        return f"Machine(id={self.id}, location={self.location})"


class MachineConfig(BaseModel):
    """Machine 配置"""
    num_machines: int = 5
    strategy: str = "random"
    seed: int = 42
    zones: int = 4
    grid_spacing: int = 5
    noise: float = 1.0


class JobConfig(BaseModel):
    """Job 配置"""

    num_jobs: int = 6  # 总任务数
    min_ops_per_job: int = 2  # 每个任务的最少工序数
    max_ops_per_job: int = 4  # 每个任务的最多工序数
    min_proc_time: int = 2  # 工序最短加工时间
    max_proc_time: int = 8  # 工序最长加工时间
    machine_choices: int = 2  # 每个工序可选机器数
    total_machines: int = 5  # 机器总数，用于分配 machine_options
    seed: int = 42  # 随机种子


@dataclass
class JobSolverResult:
    machine_schedule: Dict[
        int, List[Tuple[float, float, int, int]]
    ]  # machine_id -> [(start_time, end_time, job_id, op_id)]
    op_meta: Dict[Tuple[int, int], Dict]  # (job_id, op_id) -> {...}
    transfer_requests: List[Dict]
    stats: Dict


# ========= 路由层  =========
@dataclass
class RouteTask:
    agv_id: int
    start: Tuple[int, int]
    goal: Tuple[int, int]


@dataclass
class RouteProblem:
    map_name: str
    tasks: List[RouteTask]
    policy_name: str = "astar"  # or 'ppo', 'rra', etc.
    max_steps: int = 256
