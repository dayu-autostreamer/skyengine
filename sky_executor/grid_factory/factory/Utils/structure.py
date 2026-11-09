"""
@Project ：SkyEngine
@File    ：structure.py.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/17 19:27
"""

# 此处列举了常用的结构

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel, Field
from enum import Enum


# ========= 任务层  =========
@dataclass
class Operation:
    # ----------- 静态任务属性（初始化时确定） -----------
    job_id: int
    op_id: int
    machine_options: List[int] = None  # 可选机器列表
    machine_options_with_time: List[Tuple[int, int]] = (
        None  # (machine_id,proc_time)列表
    )
    proc_time: float = 0.0  # 实际处理时间；启用波动时在工序开始加工时采样
    nominal_proc_time: Optional[float] = None  # 配置/调度层看到的基准加工时间
    sampled_proc_time: Optional[float] = None  # 本次执行采样得到的加工时间
    processing_time_config: Optional[dict] = None  # 工序级加工时间分布配置
    processing_time_distribution: Optional[dict] = None  # 实际使用的分布描述
    release: float = 0.0  # 发布时间
    due: Optional[float] = None  # 交期
    priority: int = 0
    request_id: Optional[str] = None
    # ----------- 调度决策相关属性 -----------
    assigned_machine: Optional[int] = None  # 决策阶段选定
    assigned_robot: Optional[int] = None  # 负责运送的小车
    assigned_node: Optional[int] = None  # 实际执行节点（如果机器和物理节点分离）
    # ----------- 动态状态与指标记录 -----------
    # 状态标记
    status: str = "PENDING"  # PENDING, PROCESSING, FINISHED

    # 时间戳记录 (用于计算 Flow time, Lateness 等)
    created_at: float = 0.0  # 任务产生时间
    arrive_machine_at: float = -1  # 物料到达机器的时间
    start_process_at: float = -1  # 机器开始加工的时间 这个用不上了,arrive了立刻开始加工
    finish_process_at: float = -1  # 机器完成加工的时间

    # 过程指标
    wait_for_machine_time: float = 0.0  # 在机器前的排队时间
    remaining_proc_time: Optional[float] = None  # 被特急任务暂停后尚需加工的时间
    accumulated_process_time: float = 0.0  # 抢占前已完成的加工时间
    processed_time: float = 0.0  # 执行反馈确认的累计实际加工量
    preemption_count: int = 0
    deviation_reported: bool = False


@dataclass
class Job:
    job_id: int
    ops: List[Operation]
    release: float = 0.0  # 发布时间
    due: Optional[float] = None  # 交期
    priority: int = 0
    request_id: Optional[str] = None
    name: Optional[str] = None
    # ----------- 指标记录 -----------
    completion_time: float = -1.0  # 整个 Job 完成的时间 (Makespan calculation)
    raw_material_source: Optional[Tuple[int, int]] = None
    finished_goods_destination: Optional[Tuple[int, int]] = None
    material_location: Optional[Tuple[int, int]] = None
    carrier_id: Optional[int] = None
    transport_task_id: Optional[int] = None
    delivered: bool = False

    @property
    def is_completed(self) -> bool:
        return self.delivered


class Machine:
    """Machine 逻辑节点"""

    def __init__(self, machine_id: int, location: Tuple[int, int] = (-1, -1)):
        self.id = machine_id
        self.location = location
        self.current_op: Optional[Operation] = None
        self.input_queue: List[Operation] = []
        self.suspended_ops: List[Operation] = []
        self.urgent_reservations: set[Tuple[int, int]] = set()
        # ----------- 异常事件状态 -----------
        self.status: str = "OK"  # OK, DOWN, MAINTENANCE
        self.repair_remaining: int = 0
        self.down_elapsed: float = 0
        self.down_reason: Optional[str] = None
        self.buffer_capacity: int = 4
        self.buffer_jobs: set[int] = set()
        self.buffer_blocked_steps: int = 0
        # ----------- 指标记录 -----------
        self.total_work_time: float = 0.0  # 累计实际加工量 (用于计算利用率)
        self.processed_ops_count: int = 0  # 完成工序数量
        self.history_ops: List[Tuple[int, int, float, float]] = (
            []
        )  # 记录 (job_id, op_id, start, end)

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
    custom_positions: Optional[List[Tuple[int, int]]] = None


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
    strategy: str = "random"
    # 新增：自定义Job列表 (strategy="custom" 时使用)
    # 格式: List[Job] -> Job = List[(machine_options, proc_time)]
    # 例如: [[([0, 1], 5), ([2], 3)], [[0], 4)] 表示两个 Job
    custom_jobs: Optional[List[List[list]]] = None


@dataclass
class JobSolverResult:
    """用于静态调度"""

    machine_schedule: Dict[
        int, List[Tuple[float, float, int, int]]
    ]  # machine_id -> [(start_time, end_time, job_id, op_id)]
    op_meta: Dict[Tuple[int, int], Dict]  # (job_id, op_id) -> {...}
    transfer_requests: List[Dict]
    stats: Dict


# ========= 路由层  =========
class RoutingTask(BaseModel):
    """
    RoutingTask 表示一个待执行的搬运任务。
    无论是静态调度还是动态决策，都通过此结构描述。
    RoutingTask(job_id=1, op_id=2, source=(1, 3))
    """

    task_id: int = Field(..., description="任务 ID")  # 不一定有用,可以删了
    job_id: int = Field(..., description="所属 Job 的 ID")
    op_id: int = Field(..., description="操作 Operation 的 ID")
    source: Tuple[int, int] = Field(..., description="任务起点")
    destination: Optional[Tuple[int, int]] = Field(None, description="任务终点")
    candidate_machines: List[int] = Field(default_factory=list)
    ready_time: float = Field(..., description="任务可开始时间")
    priority: int = Field(default=0, description="所属 Job 优先级")
    request_id: Optional[str] = Field(default=None, description="插单请求 ID")
    pickup_required: bool = Field(default=True, description="是否需要先到 source 取料")
    assigned_agent_id: Optional[int] = Field(default=None, description="执行该搬运任务的 AGV ID")
    kind: str = "operation"  # operation / finished_goods

    # ----------- 指标记录 (Metrics) -----------
    create_time: float = Field(default=-1, description="任务生成时间")
    assign_time: float = Field(default=-1, description="分配给AGV的时间")
    finish_time: float = Field(default=-1, description="AGV送达目的地的时间")
    pickup_start_time: float = Field(default=-1, description="开始取料停留的时间")
    pickup_finish_time: float = Field(default=-1, description="完成取料的时间")
    dropoff_start_time: float = Field(default=-1, description="开始放料停留的时间")

    # 预留给 Monitor 计算
    # wait_time = assign_time - create_time (等待分配时间)
    # transfer_time = finish_time - assign_time (实际运输时间)

    @property
    def dynamic(self) -> bool:
        """是否为动态决策任务（即 destination 尚未确定）"""
        return self.destination is None

    @property
    def first_target(self) -> Optional[Tuple[int, int]]:
        """Return the first physical target used when assigning an idle AGV."""
        return self.source if self.pickup_required else self.destination

    def assign_destination(self, dest: Tuple[int, int]):
        """为动态任务分配目标，并更新状态"""
        object.__setattr__(self, "destination", dest)

    class Config:
        frozen = False  # 允许修改属性
        validate_assignment = True  # 修改时自动类型校验


class AGV(BaseModel):
    """AGV 逻辑节点"""

    id: int  # agent 索引
    pos: Tuple[int, int]  # 当前坐标
    current_task: Optional[RoutingTask]  # 正在执行的任务 或 None
    finished_tasks: list[RoutingTask]  # 已完成任务（可选）
    status: str = "OK"  # OK, DOWN
    repair_remaining: Optional[int] = None
    down_elapsed: float = 0
    down_reason: Optional[str] = None
    task_phase: str = "IDLE"
    handling_remaining: int = 0
    loaded: bool = False

    # ----------- 指标记录 -----------
    total_distance: int = 0  # 累计行驶距离
    total_loaded_time: int = 0  # 负载行驶时间 (有 current_task)
    total_empty_time: int = 0  # 空载行驶时间 (无 task 但在移动)
    total_idle_time: int = 0  # 空闲时间 (无 task 且不移动)
    total_handling_time: int = 0
    total_task_waiting_time: int = 0
