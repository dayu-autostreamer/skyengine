from pogema.envs import PogemaLifeLong, GridConfig
import random
from typing import Optional, List, Dict, Union
from joint_sim.utils.structure import (
    Machine,
    Job,
    RoutingTask,
    AGV,
    Operation,
)
import pickle, json


class PogemaLifeLongWithAssign(PogemaLifeLong):
    def __init__(
        self,
        grid_config: Optional[GridConfig] = None,  # [修复] 避免使用可变对象作为默认参数
        random_target=False,
        padding_init_request=True,
        debug_mode=False,
    ):
        # [修复] 如果未传入配置，则在内部初始化
        if grid_config is None:
            grid_config = GridConfig(num_agents=2)

        super().__init__(grid_config)
        self.debug_mode = debug_mode
        self.env_timeline = 0
        self.random_target = random_target
        self.padding_init_request = padding_init_request

        # machine机器相关信息
        self.machines: List[Machine] = []
        self.activated_machines: List[Machine] = []
        self.machine_process_time = {}
        self.hash_machines = {}

        # job任务相关信息
        self.jobs: List[Job] = []
        self.hash_operations: Dict[tuple[int, int], Operation] = {}
        self.pending_transfers: List[RoutingTask] = []
        self.transfers_to_assign: List[RoutingTask] = []
        self.active_transfers: List[RoutingTask] = []
        self.active_transfers: List[RoutingTask] = []
        # [新增] 物理约束缓冲池
        # 存放那些 Solver 发过来了，但因为前置工序没做完，暂时不能执行的任务
        self.buffered_tasks: List[RoutingTask] = []

        # AGV相关的路由信息
        self.agv_current_task: List[Union[RoutingTask, None]] = [
            None
        ] * self.grid_config.num_agents
        self.agv_finished_tasks: List[List[RoutingTask]] = [
            [] for _ in range(self.grid_config.num_agents)
        ]

        # 初始化统计信息
        self.agv_stats = {
            i: {"dist": 0, "loaded": 0, "empty": 0, "idle": 0}
            for i in range(self.grid_config.num_agents)
        }

    def get_agv_info(self):
        agv_list = []
        # 确保统计数据存在
        if not hasattr(self, "agv_stats"):
            self.agv_stats = {
                i: {"dist": 0, "loaded": 0, "empty": 0, "idle": 0}
                for i in range(self.grid_config.num_agents)
            }

        for idx in range(self.grid_config.num_agents):
            stats = self.agv_stats[idx]
            agv_list.append(
                AGV(
                    id=idx,
                    pos=self.grid.positions_xy[idx],
                    current_task=self.agv_current_task[idx],
                    finished_tasks=self.agv_finished_tasks[idx],
                    total_distance=stats["dist"],
                    total_loaded_time=stats["loaded"],
                    total_empty_time=stats["empty"],
                    total_idle_time=stats["idle"],
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

        super().reset(seed, return_info, options)

        for idx in range(self.grid_config.num_agents):
            if self.padding_init_request and self.grid_config.possible_targets_xy:
                self.grid.finishes_xy[idx] = random.choice(
                    self.grid_config.possible_targets_xy
                )
                self.agv_current_task[idx] = None
            else:
                self.grid.finishes_xy[idx] = self.grid.positions_xy[idx]
                self.agv_current_task[idx] = None

        if return_info:
            return self._obs(), self._get_infos()
        return self._obs()

    def create_hash_machines(self):
        hash_machines = {}
        for m in self.machines:
            hash_machines[m.location] = m
        return hash_machines

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

        self.hash_machines = self.create_hash_machines()

        obs = {
            "machines": self.machines,
            "pending_transfers": self.pending_transfers,
            "agents": self.get_agv_info(),
        }
        infos = {"num_machines": len(self.machines)}
        return obs, infos

    def job_reset(self, jobs: list[Job]):
        self.jobs = jobs if jobs else []
        self.pending_transfers.clear()
        self.active_transfers.clear()
        self.hash_operations = self.create_hash_operations()

        obs = {"jobs": self.jobs, "machines": self.machines}
        infos = {"num_jobs": len(self.jobs)}
        return obs, infos

    def machine_process(self):
        """
        [修复] 机器处理逻辑：
        1. 处理当前任务。
        2. 如果完成或空闲，检查输入队列 (input_queue)。
        3. 自动管理 activated_machines 列表。
        """
        # 使用副本遍历，因为我们可能会在循环中从 activated_machines 移除机器
        for m in list(self.activated_machines):

            # --- 阶段 1: 尝试加载新任务 ---
            if m.current_op is None:
                if m.input_queue:
                    # 从队列取出一个任务开始做
                    m.current_op = m.input_queue.pop(0)
                    self.machine_process_time[m.id] = 0
                else:
                    # 既没有当前任务，队列也是空的 -> 休眠
                    self.activated_machines.remove(m)
                    self.machine_process_time[m.id] = 0
                    continue

            # --- 阶段 2: 执行加工逻辑 ---
            current_op = m.current_op
            # 获取 Operation 的真身引用
            hash_op = (current_op.job_id, current_op.op_id)
            real_op = self.hash_operations[hash_op]

            # [Metrics] 记录开始时间
            if self.machine_process_time[m.id] == 0:
                real_op.start_process_at = self.env_timeline
                real_op.status = "PROCESSING"

            # 推进时间
            self.machine_process_time[m.id] += 1
            m.total_work_time += 1

            # --- 阶段 3: 检查完成 ---
            if self.machine_process_time[m.id] >= current_op.proc_time:
                # [Metrics] 记录完成
                real_op.finish_process_at = self.env_timeline
                real_op.status = "FINISHED"

                # 记录历史
                m.processed_ops_count += 1
                m.history_ops.append(
                    (
                        real_op.job_id,
                        real_op.op_id,
                        real_op.start_process_at,
                        real_op.finish_process_at,
                    )
                )

                # 任务完成，清空槽位
                m.current_op = None
                self.machine_process_time[m.id] = 0

                # 检查 Job 是否全部完成 (Metrics)
                job = self.jobs[real_op.job_id]
                hash_ops_completed = all(
                    self.hash_operations[(job.job_id, op.op_id)].status == "FINISHED"
                    for op in job.ops
                )

                if hash_ops_completed and job.completion_time == -1:
                    job.completion_time = self.env_timeline
                    if self.debug_mode:
                        print(
                            f"  - [SUCCESS] Job {job.job_id} finished at {self.env_timeline}"
                        )

                # 注意：这里不从 activated_machines 移除
                # 下一次循环会检查 input_queue，如果有新任务则继续，没有则移除

    def job_step(self, actions=None):
        if actions is not None:
            new_transfers = actions.get("transfer_requests", [])
            self.pending_transfers = new_transfers

        rewards = {}
        terminations = {}
        truncations = {}
        infos = {}
        observations = {
            "jobs": self.jobs,
            "machines": self.machines,
        }
        return observations, rewards, terminations, truncations, infos

    def task_step(self, action: dict):
        # === Step 0: 获取输入 ===
        assignments = action.get("assignments", {})
        # 上一步未分配的任务 (可能因为没有 AGV)
        last_step_unassigned = action.get("pending_transfers", [])

        # 来自 Solver 的新请求 (基于时间的)
        new_requests_from_solver = self.pending_transfers

        # 给新任务打时间戳
        for task in new_requests_from_solver:
            task.create_time = self.env_timeline

        # 清空 pending，防止重复
        self.pending_transfers = []

        # === [核心修复] Step 1: 物理约束检查 (Gatekeeping) ===
        # 将新任务加入缓冲池
        self.buffered_tasks.extend(new_requests_from_solver)

        ready_to_assign = []
        still_buffered = []

        for task in self.buffered_tasks:
            if self._check_physical_precondition(task):
                ready_to_assign.append(task)
            else:
                still_buffered.append(task)

        # 更新缓冲池 (剩下的继续等)
        self.buffered_tasks = still_buffered

        # 只有物理上就绪的任务，才会被加入待分配列表
        # 待分配列表 = 上次没分配完的 + 这次刚就绪的
        self.transfers_to_assign = last_step_unassigned + ready_to_assign

        # === Step 3: 机器处理 (先处理机器，可能腾出位置或者消耗队列) ===
        self.machine_process()

        # === Step 4: AGV 逻辑 ===
        infos = [dict() for _ in range(self.grid_config.num_agents)]

        for agent_idx in range(self.grid_config.num_agents):
            on_goal = self.grid.on_goal(agent_idx)
            active = self.grid.is_active[agent_idx]
            current_transfer = self.agv_current_task[agent_idx]

            # --- Case A: AGV 到达目标 (卸货) ---
            if on_goal and active and current_transfer is not None:
                pos = self.grid.finishes_xy[agent_idx]
                target_machine = self.hash_machines.get(pos, None)

                # [修复] 检查目标是否真的是机器
                if target_machine is not None:
                    # [Metrics] 记录完成
                    current_transfer.finish_time = self.env_timeline
                    hash_op = (current_transfer.job_id, current_transfer.op_id)
                    real_op = self.hash_operations[hash_op]

                    real_op.arrive_machine_at = self.env_timeline
                    real_op.assigned_machine = target_machine.id

                    # [修复] 核心逻辑：放入队列而不是覆盖 current_op
                    # 确保 input_queue 存在 (在 machine_reset 中初始化，但防御性编程)
                    if not hasattr(target_machine, "input_queue"):
                        target_machine.input_queue = []

                    target_machine.input_queue.append(real_op)

                    # 如果机器当前不在活跃列表中（说明它是休眠的），激活它
                    if target_machine.id not in [m.id for m in self.activated_machines]:
                        self.activated_machines.append(target_machine)
                        # 注意：不需要重置 machine_process_time，因为它是休眠状态，应该是0

                    # 记录任务完成
                    self.agv_finished_tasks[agent_idx].append(current_transfer)
                    if current_transfer in self.active_transfers:
                        self.active_transfers.remove(current_transfer)
                    self.agv_current_task[agent_idx] = None
                else:
                    # 如果到达的不是机器位置（异常情况），可能需要LogError或者暂时忽略
                    if self.debug_mode:
                        print(
                            f"[WARNING] Agent {agent_idx} arrived at {pos} but no machine found."
                        )

            # --- Case B: AGV 空闲分配新任务 ---
            if self.agv_current_task[agent_idx] is None:
                if self.random_target:
                    if self.grid_config.possible_targets_xy:
                        self.grid.finishes_xy[agent_idx] = random.choice(
                            self.grid_config.possible_targets_xy
                        )
                    continue

                if assignments.get(agent_idx) is not None:
                    new_transfer = assignments[agent_idx]
                    new_transfer.assign_time = self.env_timeline

                    self.agv_current_task[agent_idx] = new_transfer
                    self.active_transfers.append(new_transfer)
                    self.grid.finishes_xy[agent_idx] = new_transfer.destination

            infos[agent_idx]["is_active"] = self.grid.is_active[agent_idx]

        obs = {
            "machines": self.machines,
            "pending_transfers": self.transfers_to_assign,
            "agents": self.get_agv_info(),
        }
        terminated = [False] * self.grid_config.num_agents
        truncated = [False] * self.grid_config.num_agents
        return obs, [], terminated, truncated, infos

    def step(self, action: list):
        prev_positions = self.grid.positions_xy.copy()

        rewards = []
        infos = [dict() for _ in range(self.grid_config.num_agents)]
        self.move_agents(action)
        obs = self._obs()
        terminated = [False] * self.grid_config.num_agents
        truncated = [False] * self.grid_config.num_agents

        # [Metrics] 更新统计
        if not hasattr(self, "agv_stats"):
            self.agv_stats = {
                i: {"dist": 0, "loaded": 0, "empty": 0, "idle": 0}
                for i in range(self.grid_config.num_agents)
            }

        for idx in range(self.grid_config.num_agents):
            current_pos = self.grid.positions_xy[idx]
            prev_pos = prev_positions[idx]
            dist = abs(current_pos[0] - prev_pos[0]) + abs(current_pos[1] - prev_pos[1])

            stats = self.agv_stats[idx]
            stats["dist"] += dist

            has_task = self.agv_current_task[idx] is not None
            is_moving = dist > 0

            if has_task and is_moving:
                stats["loaded"] += 1
            elif not has_task and is_moving:
                stats["empty"] += 1
            else:
                stats["idle"] += 1

        self.env_timeline += 1
        return obs, rewards, terminated, truncated, infos

    def get_state(self) -> dict:
        grid_state = {
            "positions_xy": list(self.grid.positions_xy),
            "finishes_xy": list(self.grid.finishes_xy),
            "is_active": list(self.grid.is_active),
        }

        # 序列化时需要包含 input_queue
        # 由于 Machine 对象是自定义类，pickle 会自动保存其属性包括 input_queue
        state_dict = {
            "env_timeline": self.env_timeline,
            "machines": self.machines,
            "jobs": self.jobs,
            "activated_machines": self.activated_machines,
            "machine_process_time": self.machine_process_time,
            "pending_transfers": self.pending_transfers,
            "buffered_tasks": self.buffered_tasks,  # [新增]
            "transfers_to_assign": self.transfers_to_assign,
            "active_transfers": self.active_transfers,
            "agv_current_task": self.agv_current_task,
            "agv_finished_tasks": self.agv_finished_tasks,
            "agv_stats": getattr(self, "agv_stats", None),
            "grid_state": grid_state,
        }
        return state_dict

    def set_state(self, state_files):
        if isinstance(state_files, dict):
            state_dict = state_files
        else:
            try:
                with open(state_files, "rb") as f:
                    state_dict = pickle.load(f)
            except Exception:
                with open(state_files, "r", encoding="utf-8") as f:
                    state_dict = json.load(f)

        self.env_timeline = state_dict["env_timeline"]
        self.machines = state_dict["machines"]
        self.jobs = state_dict["jobs"]
        self.activated_machines = state_dict["activated_machines"]
        self.machine_process_time = state_dict["machine_process_time"]
        self.pending_transfers = state_dict["pending_transfers"]
        self.buffered_tasks = state_dict.get("buffered_tasks", [])  # [新增]
        self.transfers_to_assign = state_dict["transfers_to_assign"]
        self.active_transfers = state_dict["active_transfers"]
        self.agv_current_task = state_dict["agv_current_task"]
        self.agv_finished_tasks = state_dict["agv_finished_tasks"]

        if state_dict.get("agv_stats") is not None:
            self.agv_stats = state_dict["agv_stats"]
        elif hasattr(self, "agv_stats"):
            del self.agv_stats

        g_state = state_dict["grid_state"]
        self.grid.positions_xy[:] = g_state["positions_xy"]
        self.grid.finishes_xy[:] = g_state["finishes_xy"]
        self.grid.is_active[:] = g_state["is_active"]

        self.hash_machines = self.create_hash_machines()
        self.hash_operations = self.create_hash_operations()

    def job_all_done(self):
        return all([job.is_completed for job in self.jobs])

    def _check_physical_precondition(self, task: RoutingTask) -> bool:
        """
        检查任务的物理前置条件是否满足。
        对于 JSSP，主要是检查前置工序是否 FINISHED。
        """
        # 第一道工序，无前置约束，直接通过
        if task.op_id == 0:
            return True

        # 获取 Job 信息
        # 注意：self.jobs 里的状态是由 machine_process 实时更新的
        job = self.jobs[task.job_id]

        # 边界检查
        if task.op_id > 0 and task.op_id < len(job.ops):
            prev_op = job.ops[task.op_id - 1]
            # 只有前置工序彻底完成了，物料才存在，才能开始运输
            if prev_op.status == "FINISHED":
                return True
        else:
            # 异常 op_id
            return False

        return False
