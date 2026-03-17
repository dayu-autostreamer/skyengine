from pogema.envs import PogemaLifeLong, GridConfig
import random
from typing import Optional, List, Dict
from joint_sim.utils.structure import (
    Machine,
    Job,
    RoutingTask,
    AGV,
    Operation,
)


class PogemaLifeLongWithAssign(PogemaLifeLong):
    def __init__(
            self,
            grid_config=GridConfig(num_agents=2),
            random_target=False,
            padding_init_request=True,
    ):
        super().__init__(grid_config)
        self.env_timeline = 0
        self.random_target = random_target
        self.padding_init_request = padding_init_request
        # machine机器相关信息
        self.machines: List[Machine] = []
        self.activated_machines: List[Machine] = []
        self.machine_process_time = {}
        self.finish_operations = []
        self.hash_machines = {}  # 从(x,y)到machine的映射
        # job任务相关信息
        self.jobs: List[Job] = []
        self.hash_operations: Dict[tuple[int, int], Operation] = {}  # 从(job_id,op_id)到operation的映射
        self.pending_transfers: List[RoutingTask] = (
            []
        )  # Job层达到ready_time的任务,按理应执行的任务

        self.transfers_to_assign: List[RoutingTask] = []  # 待分配任务
        self.active_transfers: List[RoutingTask] = []  # 当前执行中的运输任务
        # AGV相关的路由信息由pogema本身管理
        self.agv_current_task: List[RoutingTask | None] = [
                                                            None
                                                          ] * self.grid_config.num_agents  # 当前的路由任务
        self.agv_finished_tasks: List[List[RoutingTask]] = [
            [] for _ in range(self.grid_config.num_agents)
        ]  # 当前已完成的任务

    def get_agv_info(self):
        agv_list = []
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
                    # 填入统计数据
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
        super().reset(seed, return_info, options)
        # 重新分配可能的目标
        for idx in range(self.grid_config.num_agents):
            if self.padding_init_request:
                # 填充初始目标
                self.grid.finishes_xy[idx] = random.choice(
                    self.grid_config.possible_targets_xy
                )
                # 构造填充初始transfer_requests
                self.agv_current_task[idx] = None
            else:
                # 不填充初始目标
                self.grid.finishes_xy[idx] = self.grid.positions_xy[idx]
                self.agv_current_task[idx] = None

        if return_info:
            return self._obs(), self._get_infos()
        return self._obs()

    def create_hash_machines(self):
        """创建从idx到machine的映射"""
        hash_machines = {}
        for m in self.machines:
            hash_machines[m.location] = m
        return hash_machines

    def create_hash_operations(self):
        """创建从 (job_id, op_id) 到 Operation 对象的映射"""
        hash_operations = {}
        for job in self.jobs:
            for op in job.ops:
                hash_operations[(job.job_id, op.op_id)] = op
        return hash_operations

    def machine_reset(
            self,
            machines: list[Machine],
    ):
        """重置所有机器"""
        self.machines = machines if machines else []
        self.grid_config.possible_targets_xy = [
            m.location for m in self.machines
        ]  # 设置可能的机器位置
        self.activated_machines = []
        self.machine_process_time = {m.id: 0 for m in self.machines}
        self.hash_machines = self.create_hash_machines()
        # 返回obs和info
        obs = {
            "machines": self.machines,
            "pending_transfers": self.pending_transfers,
            "agents": self.get_agv_info(),
        }

        infos = {"num_machines": len(self.machines)}
        return obs, infos

    def job_reset(self, jobs: list[Job]):
        """重置任务状态"""
        self.jobs = jobs if jobs else []
        self.pending_transfers.clear()
        self.active_transfers.clear()
        # 初始化 operation 映射表
        self.hash_operations = self.create_hash_operations()
        # 返回obs和info
        obs = {"jobs": self.jobs, "machines": self.machines}
        infos = {"num_jobs": len(self.jobs)}
        return obs, infos

    def machine_process(self):
        """处理机器的任务推进"""
        finished = []  # 当前时间步完成的机器

        # 遍历活跃机器
        for m in list(self.activated_machines):
            current_op = getattr(m, "current_op", None)

            # 没有操作，无法推进，跳过
            if current_op is None:
                self.activated_machines.remove(m)
                self.machine_process_time[m.id] = 0
                continue

            # 这里的 current_op 可能是来自 Machine 对象的引用
            # 为了保险起见，我们始终通过 hash_operations 获取该操作的“真身”进行状态修改
            op_key = (current_op.job_id, current_op.op_id)
            real_op = self.hash_operations.get(op_key)

            if real_op is None:
                # 理论上不应该发生，除非 op_id 不在 jobs 中
                continue

            # --- [Metrics] 记录开始加工时间 ---
            if self.machine_process_time[m.id] == 0:
                real_op.start_process_at = self.env_timeline
                real_op.status = "PROCESSING"
                # 同时更新 machine 上的引用，保持一致性（虽然如果不更新引用只改属性也行，但这样更安全）
                m.current_op = real_op

            # 推进处理时间
            self.machine_process_time[m.id] += 1
            # --- [Metrics] 累加机器工作时间 ---
            m.total_work_time += 1

            # 判断是否完成
            if self.machine_process_time[m.id] >= real_op.proc_time:
                finished.append((m, real_op))

        # 后处理：统一从 activated_machines 删除
        for m, op in finished:
            self.activated_machines.remove(m)
            self.machine_process_time[m.id] = 0

            # 再次通过 hash map 获取真身 (虽然 op 应该已经是 real_op)
            op_key = (op.job_id, op.op_id)
            real_op_final = self.hash_operations[op_key]

            # --- [Metrics] 记录完成信息 ---
            real_op_final.finish_process_at = self.env_timeline
            real_op_final.status = "FINISHED"

            # --- [Metrics] 记录 Machine 完成的任务 ---
            m.processed_ops_count += 1
            m.history_ops.append(
                (real_op_final.job_id, real_op_final.op_id, real_op_final.start_process_at,
                 real_op_final.finish_process_at)
            )

            self.finish_operations.append(real_op_final)
            m.current_op = None

            # --- [Metrics] 检查 Job 是否全部完成 ---
            job = self.jobs[real_op_final.job_id]
            # 检查 job 是否完成
            if job.is_completed and job.completion_time == -1:
                job.completion_time = self.env_timeline

    def job_step(self, actions=None):
        """
        Job 层根据当前job,输出routing tasks
        """
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

    def get_relative_position(self, tuples, padding=4):
        if isinstance(tuples, tuple):
            new_tuples = (tuples[0] + padding, tuples[1] + padding)
        else:
            tuple_list = tuples
            new_tuples = []
            for tu in tuple_list:
                tu0 = tu[0] + padding
                tu1 = tu[1] + padding
                new_tuples.append((tu0, tu1))
        return new_tuples

    def task_step(self, action: dict):
        """处理任务层,合并任务、移除已分配、整理可调度任务"""
        # === Step 0. 整理任务集合 ===
        assignments = action.get("assignments", {})  # 新分配的任务
        last_step_transfers = action.get(
            "pending_transfers", []
        )  # 上一步未执行完的任务

        # === Step 1. 合并未完成的transfer ===
        all_new_requests = (
            self.pending_transfers
        )  # pending_transfers: Job层本周期新增的任务

        # --- [Metrics] 标记新任务的创建时间 ---
        # 注意：Transfer 是临时的路由对象，在这里修改它是没问题的
        for task in all_new_requests:
            task.create_time = self.env_timeline

        self.pending_transfers = []  # 清空，避免重复加入
        self.transfers_to_assign = last_step_transfers + all_new_requests

        # === Step 2. 更新Job操作的source位置 (如有需要可在此处操作) ===

        # === Step 3. 推进机器处理逻辑 ===
        self.machine_process()

        # === Step 4. 处理每个AGV的当前任务 ===
        infos = [dict() for _ in range(self.grid_config.num_agents)]

        for agent_idx in range(self.grid_config.num_agents):
            on_goal = self.grid.on_goal(agent_idx)
            active = self.grid.is_active[agent_idx]
            current_transfer = self.agv_current_task[agent_idx]

            if on_goal and active:
                # --- Case A: AGV 到达目标位置 ---
                if current_transfer is not None:
                    # --- [Metrics] 记录运输完成 ---
                    current_transfer.finish_time = self.env_timeline

                    pos = self.grid.finishes_xy[agent_idx]
                    target_machine: Optional[Machine] = self.hash_machines.get(pos, None)

                    job_id = current_transfer.job_id
                    op_id = current_transfer.op_id

                    # ✅ 核心修改：从 hash_operations 获取唯一的 Operation 引用
                    # 而不是创建一个新的引用或从可能未更新的列表中获取
                    real_op = self.hash_operations[(job_id, op_id)]

                    # --- [Metrics] 记录物料到达机器的时间 ---
                    real_op.arrive_machine_at = self.env_timeline

                    # 将这个真实的 op 引用赋给机器
                    target_machine.current_op = real_op

                    if target_machine.id not in [m.id for m in self.activated_machines]:
                        self.activated_machines.append(target_machine)
                        self.machine_process_time[target_machine.id] = 0

                    # ✅ 更新该任务状态为完成
                    self.agv_finished_tasks[agent_idx].append(current_transfer)

                    if current_transfer in self.active_transfers:
                        self.active_transfers.remove(current_transfer)
                    self.agv_current_task[agent_idx] = None

                # --- Case B: AGV 空闲且有新任务分配 ---
            if current_transfer is None:
                if self.random_target == True:
                    self.grid.finishes_xy[agent_idx] = random.choice(
                        self.grid_config.possible_targets_xy
                    )
                    continue
                if assignments.get(agent_idx) is not None:
                    new_transfer = assignments[agent_idx]
                    # --- [Metrics] 记录分配时间 ---
                    new_transfer.assign_time = self.env_timeline

                    self.agv_current_task[agent_idx] = new_transfer
                    self.active_transfers.append(new_transfer)
                    self.grid.finishes_xy[agent_idx] = new_transfer.destination
            infos[agent_idx]["is_active"] = self.grid.is_active[agent_idx]

        # 返回需要的观察信息
        obs = {
            "machines": [m for m in self.machines if m.current_op is None],
            "pending_transfers": self.transfers_to_assign,
            "agents": self.get_agv_info(),
        }
        terminated = [False] * self.grid_config.num_agents
        truncated = [False] * self.grid_config.num_agents
        return obs, [], terminated, truncated, infos

    def step(self, action: list):
        """移动小车"""
        # 保存移动前的位置用于计算距离
        prev_positions = self.grid.positions_xy.copy()

        rewards = []
        infos = [dict() for _ in range(self.grid_config.num_agents)]
        self.move_agents(action)
        obs = self._obs()
        terminated = [False] * self.grid_config.num_agents
        truncated = [False] * self.grid_config.num_agents

        # --- [Metrics] 更新 AGV 指标 ---
        for idx in range(self.grid_config.num_agents):
            current_pos = self.grid.positions_xy[idx]
            prev_pos = prev_positions[idx]

            # 1. 计算距离
            dist = abs(current_pos[0] - prev_pos[0]) + abs(current_pos[1] - prev_pos[1])

            if not hasattr(self, "agv_stats"):
                self.agv_stats = {
                    i: {"dist": 0, "loaded": 0, "empty": 0, "idle": 0}
                    for i in range(self.grid_config.num_agents)
                }

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