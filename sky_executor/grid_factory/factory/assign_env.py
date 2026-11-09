from pogema.envs import PogemaLifeLong, GridConfig
import random
from threading import RLock
from typing import Optional, List, Dict, Sequence, Union
from sky_executor.grid_factory.factory.Utils.structure import (
    Machine,
    Job,
    RoutingTask,
    AGV,
    Operation,
)
from sky_executor.grid_factory.factory.business import (
    AGV_PHASE_IDLE,
)


class PogemaLifeLongWithAssign(PogemaLifeLong):
    def __init__(
        self,
        grid_config: Optional[GridConfig] = None,  # [修复] 避免使用可变对象作为默认参数
        random_target=False,
        padding_init_request=True,
        debug_mode=False,
        material_handling_config: Optional[dict] = None,
    ):
        if grid_config is None:
            grid_config = GridConfig(num_agents=2)

        super().__init__(grid_config)
        # Shared by callers that combine fact/business writes and snapshot reads.
        # Keep this object across resets; it is not part of saved business state.
        self.state_lock = RLock()
        self.debug_mode = debug_mode
        self.env_timeline = 0
        self.episode_seed = int(self.grid_config.seed or 0)
        self._rng = random.Random(self.episode_seed)
        self.random_target = random_target
        self.padding_init_request = padding_init_request
        handling_config = material_handling_config or {}
        raw_source = handling_config.get("raw_material_source")
        self.raw_material_source = tuple(raw_source) if raw_source is not None else None
        sink = handling_config.get("finished_goods_destination")
        self.finished_goods_destination = tuple(sink) if sink is not None else None
        self.buffer_capacity = int(handling_config.get("buffer_capacity", 4))
        self.machine_buffer_capacities = dict(handling_config.get("machine_buffer_capacities", {}))
        self._shipping_sequence = -1

        # machine机器相关信息
        self.machines: List[Machine] = []
        self.activated_machines: List[Machine] = []
        self.machine_process_time = {}
        self.hash_machines = {}

        # job任务相关信息
        self.jobs: List[Job] = []
        self._all_jobs: List[Job] = []
        self._future_jobs: List[Job] = []
        self.hash_operations: Dict[tuple[int, int], Operation] = {}
        self.pending_transfers: List[RoutingTask] = []
        self.transfers_to_assign: List[RoutingTask] = []
        self.active_transfers: List[RoutingTask] = []
        # 存放那些 Solver 发过来了，但因为前置工序没做完，暂时不能执行的任务
        self.buffered_tasks: List[RoutingTask] = []

        # AGV相关的路由信息
        self.agv_current_task: List[Union[RoutingTask, None]] = [
            None
        ] * self.grid_config.num_agents
        self.agv_finished_tasks: List[List[RoutingTask]] = [
            [] for _ in range(self.grid_config.num_agents)
        ]
        self.agv_status: List[str] = ["OK"] * self.grid_config.num_agents
        self.agv_repair_remaining: List[int] = [0] * self.grid_config.num_agents
        self.agv_down_elapsed: List[float] = [0] * self.grid_config.num_agents
        self.agv_down_reason: List[Union[str, None]] = [None] * self.grid_config.num_agents
        self.agv_task_phase: List[str] = [AGV_PHASE_IDLE] * self.grid_config.num_agents
        self.agv_handling_remaining: List[int] = [0] * self.grid_config.num_agents
        self.agv_loaded: List[bool] = [False] * self.grid_config.num_agents
        self.agv_last_step_phase: List[str] = [AGV_PHASE_IDLE] * self.grid_config.num_agents
        self._assigned_this_step = set()

        self.event_epoch = 0
        self.map_epoch = 0
        self.machine_epoch = 0
        self.agv_epoch = 0
        self.job_epoch = 0
        self.last_events = []
        self.event_metrics = {}
        self.reported_temporary_obstacles: set[tuple[int, int]] = set()

        # 初始化统计信息
        self.agv_stats = {
            i: {"dist": 0, "loaded": 0, "empty": 0, "idle": 0, "handling": 0, "task_waiting": 0}
            for i in range(self.grid_config.num_agents)
        }

    def get_agv_info(self):
        agv_list = []
        # 确保统计数据存在
        if not hasattr(self, "agv_stats"):
            self.agv_stats = {
                i: {"dist": 0, "loaded": 0, "empty": 0, "idle": 0, "handling": 0, "task_waiting": 0}
                for i in range(self.grid_config.num_agents)
            }

        for idx in range(self.grid_config.num_agents):
            stats = self.agv_stats[idx]
            agv_list.append(
                AGV(
                    id=idx,
                    pos=self._to_public_xy(self.grid.positions_xy[idx]),
                    current_task=self.agv_current_task[idx],
                    finished_tasks=self.agv_finished_tasks[idx],
                    status=self.agv_status[idx] if idx < len(self.agv_status) else "OK",
                    repair_remaining=(
                        self.agv_repair_remaining[idx]
                        if idx < len(self.agv_repair_remaining) else 0
                    ),
                    down_reason=(
                        self.agv_down_reason[idx]
                        if idx < len(self.agv_down_reason) else None
                    ),
                    down_elapsed=self.agv_down_elapsed[idx],
                    task_phase=self.agv_task_phase[idx],
                    handling_remaining=self.agv_handling_remaining[idx],
                    loaded=self.agv_loaded[idx],
                    total_distance=stats["dist"],
                    total_loaded_time=stats["loaded"],
                    total_empty_time=stats["empty"],
                    total_idle_time=stats["idle"],
                    total_handling_time=stats.get("handling", 0),
                    total_task_waiting_time=stats.get("task_waiting", 0),
                )
            )
        return agv_list

    def reset(
        self,
        seed: Optional[int] = None,
        return_info: bool = True,
        options: Optional[dict] = None,
    ):
        # 确保 possible_targets_xy 存在 (防止在 machine_reset 之前调用 reset 报错)
        if (
            not hasattr(self.grid_config, "possible_targets_xy")
            or not self.grid_config.possible_targets_xy
        ):
            # 如果没有机器位置信息，暂时用全图或当前位置兜底
            self.grid_config.possible_targets_xy = list(self.grid.positions_xy)

        self.episode_seed = int(self.grid_config.seed or 0) if seed is None else int(seed)
        self._rng = random.Random(self.episode_seed)
        super().reset(seed, return_info, options)
        self.env_timeline = 0
        if hasattr(self, "reported_temporary_obstacles"):
            self.reported_temporary_obstacles.clear()
        else:
            self.reported_temporary_obstacles = set()

        for idx in range(self.grid_config.num_agents):
            if self.padding_init_request and self.grid_config.possible_targets_xy:
                self.grid.finishes_xy[idx] = self._to_internal_xy(
                    self._rng.choice(self.grid_config.possible_targets_xy)
                )
                self.agv_current_task[idx] = None
            else:
                self.grid.finishes_xy[idx] = self.grid.positions_xy[idx]
                self.agv_current_task[idx] = None

        self.agv_status = ["OK"] * self.grid_config.num_agents
        self.agv_repair_remaining = [0] * self.grid_config.num_agents
        self.agv_down_elapsed = [0] * self.grid_config.num_agents
        self.agv_down_reason = [None] * self.grid_config.num_agents
        self.agv_task_phase = [AGV_PHASE_IDLE] * self.grid_config.num_agents
        self.agv_handling_remaining = [0] * self.grid_config.num_agents
        self.agv_loaded = [False] * self.grid_config.num_agents
        self.agv_last_step_phase = [AGV_PHASE_IDLE] * self.grid_config.num_agents
        self.agv_finished_tasks = [[] for _ in range(self.grid_config.num_agents)]
        self.agv_stats = {
            i: {"dist": 0, "loaded": 0, "empty": 0, "idle": 0, "handling": 0, "task_waiting": 0}
            for i in range(self.grid_config.num_agents)
        }

        if return_info:
            return self._obs(), self._get_infos()
        return self._obs()

    def create_hash_machines(self):
        hash_machines = {}
        for m in self.machines:
            hash_machines[m.location] = m
        return hash_machines

    def _to_internal_xy(self, pos):
        """Convert map-local coordinates to Pogema's obs_radius-padded grid coordinates."""
        if pos is None:
            return None
        offset = getattr(self.grid_config, "obs_radius", 0) or 0
        x, y = pos
        return (int(x) + offset, int(y) + offset)

    def _to_public_xy(self, pos):
        """Convert Pogema's padded coordinates to map-local coordinates."""
        if pos is None:
            return None
        offset = getattr(self.grid_config, "obs_radius", 0) or 0
        x, y = pos
        return (int(x) - offset, int(y) - offset)

    def create_hash_operations(self):
        hash_operations = {}
        for job in self.jobs:
            for op in job.ops:
                hash_operations[(job.job_id, op.op_id)] = op
        return hash_operations

    def machine_reset(self, machines: list[Machine]):
        self.machines = machines if machines else []
        self.grid_config.possible_targets_xy = [m.location for m in self.machines]
        self.activated_machines = []
        self.machine_process_time = {m.id: 0 for m in self.machines}

        # [修复] 为每个机器初始化输入缓冲区 (Input Queue)，防止任务覆盖
        for m in self.machines:
            if not hasattr(m, "input_queue"):
                m.input_queue = []
            else:
                m.input_queue.clear()  # 清空旧数据
            m.current_op = None  # 确保初始状态为空
            m.suspended_ops = []
            m.urgent_reservations = set()
            m.status = "OK"
            m.repair_remaining = 0
            m.down_elapsed = 0
            m.down_reason = None
            m.buffer_capacity = int(self.machine_buffer_capacities.get(str(m.id), self.buffer_capacity))
            if m.buffer_capacity < 1:
                raise ValueError("machine buffer capacity must be positive")
            m.buffer_jobs = set()
            m.buffer_blocked_steps = 0

        self.hash_machines = self.create_hash_machines()

        obs = {
            "machines": self.machines,
            "pending_transfers": self.pending_transfers,
            "agents": self.get_agv_info(),
        }
        infos = {"num_machines": len(self.machines)}
        return obs, infos

    def job_reset(self, jobs: list[Job]):
        self._all_jobs = list(jobs)
        self.jobs = self._all_jobs
        self._future_jobs = []
        self.reschedule_count = self.reassigned_operation_count = self.reassigned_transport_count = 0
        self.pending_transfers.clear()
        self.active_transfers.clear()
        self.transfers_to_assign.clear()
        self.buffered_tasks.clear()
        self._shipping_sequence = -1
        for job in self.jobs:
            job.completion_time = -1.0
            for op in job.ops:
                nominal = op.nominal_proc_time if op.nominal_proc_time is not None else op.proc_time
                op.proc_time = nominal
                op.sampled_proc_time = None
                op.processing_time_distribution = None
                op.assigned_machine = None
                op.assigned_robot = None
                op.assigned_node = None
                op.status = "PENDING"
                op.arrive_machine_at = -1
                op.start_process_at = -1
                op.finish_process_at = -1
                op.wait_for_machine_time = 0.0
                op.remaining_proc_time = None
                op.accumulated_process_time = 0.0
                op.processed_time = 0.0
                op.preemption_count = 0
                op.deviation_reported = False
        self.hash_operations = self.create_hash_operations()
        self.event_epoch = 0
        self.map_epoch = 0
        self.machine_epoch = 0
        self.agv_epoch = 0
        self.job_epoch = 0
        self.last_events = []
        self.event_metrics = {}

        obs = {"jobs": self.jobs, "machines": self.machines}
        infos = {"num_jobs": len(self.jobs)}
        return obs, infos

    def build_job_observation(self) -> dict:
        """Project the current job and machine state without mutating it."""
        return {
            "jobs": self.jobs,
            "machines": self.machines,
        }

    def _set_agv_phase(self, agent_idx: int, phase: str, remaining: int = 0) -> None:
        self.agv_task_phase[agent_idx] = phase
        self.agv_handling_remaining[agent_idx] = max(0, int(remaining))

    def _set_agv_target(self, agent_idx: int, target) -> None:
        if target is not None:
            self.grid.finishes_xy[agent_idx] = self._to_internal_xy(target)

    def build_task_observation(self) -> dict:
        """Project the current task and AGV state without advancing time."""
        return {
            "machines": self.machines,
            "pending_transfers": self.transfers_to_assign,
            "agents": self.get_agv_info(),
            "env_timeline": self.env_timeline,
            "obstacle_grid": self.grid.obstacles,
            "grid_height": self.grid.obstacles.shape[0],
            "grid_width": self.grid.obstacles.shape[1],
            "event_epoch": getattr(self, "event_epoch", 0),
            "map_epoch": getattr(self, "map_epoch", 0),
            "machine_epoch": getattr(self, "machine_epoch", 0),
            "agv_epoch": getattr(self, "agv_epoch", 0),
            "job_epoch": getattr(self, "job_epoch", 0),
            "events": getattr(self, "last_events", []),
            "event_metrics": getattr(self, "event_metrics", {}),
            "agv_status": list(getattr(self, "agv_status", [])),
            "agv_repair_remaining": list(getattr(self, "agv_repair_remaining", [])),
            "agv_task_phase": list(getattr(self, "agv_task_phase", [])),
            "agv_handling_remaining": list(getattr(self, "agv_handling_remaining", [])),
            "agv_loaded": list(getattr(self, "agv_loaded", [])),
        }

    def build_agent_observation(self):
        """Project the current Pogema routing observation without mutation."""
        return self._obs()

    def replace_agent_positions(self, positions_xy: Sequence[tuple[int, int]]) -> None:
        """Atomically replace the complete internal AGV position layer."""
        if len(positions_xy) != self.grid_config.num_agents:
            raise ValueError(
                "positions_xy must contain exactly one position per AGV"
            )

        new_positions = [tuple(position) for position in positions_xy]
        is_active = self.grid.is_active
        for agent_id, old_position in enumerate(self.grid.positions_xy):
            active = (
                is_active.get(agent_id, False)
                if isinstance(is_active, dict)
                else is_active[agent_id]
            )
            if active:
                self.grid.positions[old_position] = self.grid.config.FREE

        self.grid.positions_xy[:] = new_positions
        for agent_id, new_position in enumerate(new_positions):
            active = (
                is_active.get(agent_id, False)
                if isinstance(is_active, dict)
                else is_active[agent_id]
            )
            if active:
                self.grid.positions[new_position] = self.grid.config.OBSTACLE

    def get_state(self):
        raise RuntimeError("saving execution is unsupported in this stage")

    def set_state(self, state_files):
        raise RuntimeError("restoring execution is unsupported; use full reset")

    def job_all_done(self):
        return bool(self._all_jobs) and all(job.is_completed for job in self._all_jobs)
