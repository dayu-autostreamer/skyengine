"""
SkyEngine 仿真控制服务 (sim_server.py)
=========================================

运行在引擎容器内部的 FastAPI 服务。
对引擎本身的运行进行管理。
提供在线仿真控制接口: create / play / pause / reset / stop / SSE stream。

设计原则:
1. 不依赖 run.py（run.py 是实验脚本，环境变量驱动，跑完退出）
2. 直接 import sky_executor 底层组件，自己组装
3. 所有参数通过 HTTP POST JSON 传入，不读环境变量
4. 配置解析逻辑由 sky_executor.session 统一提供

启动: uv run python -u sim_server.py
端口: 8080
"""

import json
import importlib
import threading

import asyncio
import queue as thread_queue
import time
from copy import deepcopy
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from sky_executor.lifecycle import RunReplaced
from sky_executor.grid_factory.factory.Component.RaceFMS.coordinator import RaceFMSCoordinator
from sky_executor.grid_factory.factory.Component.RaceFMS.coupling import CounterfactualCouplingEstimator
from sky_executor.grid_factory.factory.Component.RaceFMS.recovery import AdaptiveRecoveryGate, RecoveryScope
from sky_executor.utils.diff import DiffEmitter, make_envelope
from sky_executor.session import SimulationSession, create_env_from_config as shared_create_env_from_config

@asynccontextmanager
async def _lifespan(app: FastAPI):
    try:
        yield
    finally:
        await asyncio.to_thread(manager.shutdown)


app = FastAPI(lifespan=_lifespan)


class _SimulationRecoveryHandler:
    """Bridge RACE recovery decisions to runtime-owned atomic operations."""

    def __init__(self, manager):
        self.manager = manager

    def recover(self, decision, state, observation, delegate):
        env = self.manager.env
        worker = env.ensure_perception_worker()
        result = self.manager._recover_runtime(decision, delegate)
        # Recovery used to update shared observation references. Refresh only
        # the solver's private working copy after runtime-owned writes finish.
        snapshot = worker.request_snapshot().result()
        env.require_current_run(worker)
        observation.clear()
        observation.update(snapshot.observation)
        return result


def create_env_from_config(config: dict, *, agent_observation_type: str = "default"):
    """Create the shared environment using an explicit vehicle observation format."""
    return shared_create_env_from_config(config, agent_observation_type=agent_observation_type)


# ==================== 仿真管理器 ====================

class SimulationManager:
    """
    L1 传输层：广播 + 快照 + 订阅者模型。

    - 每个订阅者（SSE 连接）拿到一个独立的 bounded threading.Queue。
    - 仿真线程通过 _broadcast 向所有订阅者投递事件。
    - threading.Queue 是线程安全的，解决了原先 asyncio.Queue 跨 event loop
      操作导致的 data race（put 在 self._loop / get 在 uvicorn loop）。
    - _latest_frame / _latest_metrics 快照让晚连接者（刷新页面）立即看到当前状态。
    - _episode_summary / _heatmaps 在 episode 结束后持久保存，新连接也能收到。
    """

    def __init__(self):
        self.env = None
        self.session: SimulationSession | None = None
        self.coordinator = None
        self._replay_enabled = False
        self._replay_actions = []
        self._policy_controller = None
        self.obs = None
        self._machine_metadata: dict[int, dict] = {}

        self.running = False
        self.paused = False
        self.step = 0
        self._last_factory_event_epoch = 0
        self.max_steps = 1000

        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._env_lock = threading.RLock()
        self._run_generation = 0

        # L1: 订阅者集合（每个 SSE 连接一个 bounded threading.Queue）
        self._state_subs: set[thread_queue.Queue] = set()
        self._metrics_subs: set[thread_queue.Queue] = set()
        self._events_subs: set[thread_queue.Queue] = set()
        self._subs_lock = threading.Lock()

        # L1: 最新快照（晚连接 / 刷新页面可看到当前状态）
        self._latest_frame: dict | None = None
        self._latest_metrics: dict | None = None
        self._episode_summary: dict | None = None
        self._heatmaps: dict | None = None
        self._episode_status: str = "idle"  # idle | running | stopped
        self._event_history: list[dict] = []
        self._insert_lock = threading.Lock()
        self._next_insert_id = 1
        self._next_job_id = 0
        self._fjsp_algorithm = ""
        self._assigner_name = ""
        self._recovery_metrics = {
            "race_residual_replan_count": 0,
            "race_residual_replan_failed": 0,
            "race_residual_replan_latency_ms": 0.0,
            "race_replanned_operation_count": 0,
            "race_last_replanned_fraction": 0.0,
            "race_agv_reassign_count": 0,
            "race_agv_reassign_blocked_loaded": 0,
        }

        # events diff 调度器（升级后：Rule 注册表 + 信封归一化，见 sky_executor/utils/diff.py）
        self._diff = DiffEmitter(self._on_diff_event)

    def _broadcast(self, subs: set, event: tuple):
        """向所有订阅者的 queue 投递事件（非阻塞，满了丢最旧）。"""
        for q in list(subs):
            try:
                q.put_nowait(event)
            except thread_queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass

    def subscribe(self, kind: str) -> thread_queue.Queue:
        """
        新订阅者：拿到一个 bounded queue + 立即收到最新快照。

        kind: "state" | "metrics" | "events"
        """
        q = thread_queue.Queue(maxsize=10000 if kind == "events" else 200)
        with self._subs_lock:
            if kind == "events":
                self._events_subs.add(q)
                for envelope in self._event_history:
                    q.put_nowait(("event", deepcopy(envelope)))
                # 开场事件（晚连接者也能看到）—— 走 canonical 信封
                q.put_nowait(("event", make_envelope(
                    self.step, f"T+{self.step}s",
                    etype="sim_started",
                    title="仿真启动",
                    message=f"仿真已启动 (step={self.step})",
                )))
            elif kind == "state":
                self._state_subs.add(q)
                # 补发最新快照（晚连接者能看到当前画面）
                if self._latest_frame is not None:
                    q.put_nowait(("state", {
                        "status": self._episode_status,
                        "frame": self._latest_frame,
                    }))
            elif kind == "metrics":
                self._metrics_subs.add(q)
                if self._episode_status == "stopped" and self._episode_summary is not None:
                    q.put_nowait(("metrics", {
                        "status": "stopped",
                        "step": self.step,
                        "episode_summary": self._episode_summary,
                        "heatmap": self._heatmaps,
                    }))
                elif self._latest_metrics is not None:
                    q.put_nowait(("metrics", self._latest_metrics))
        return q

    def unsubscribe(self, kind: str, q: thread_queue.Queue):
        with self._subs_lock:
            if kind == "state":
                self._state_subs.discard(q)
            elif kind == "metrics":
                self._metrics_subs.discard(q)
            elif kind == "events":
                self._events_subs.discard(q)

    def _on_diff_event(self, envelope: dict):
        """DiffEmitter 的 emit 回调：把 canonical 信封包成 SSE 事件元组广播。
        envelope 来自 sky_executor/utils/diff.py 的 make_envelope。"""
        self._record_stream_event(envelope)

    def _record_stream_event(self, envelope: dict):
        self._event_history.append(deepcopy(envelope))
        if self._events_subs:
            self._broadcast(self._events_subs, ("event", envelope))

    @staticmethod
    def _parse_max_steps(factory_config: dict) -> int | None:
        """Read simulation_control.max_steps; None means run until job_done."""
        control = factory_config.get("simulation_control") or {}
        raw = control.get("max_steps", 1000)
        if raw is None:
            return None
        if isinstance(raw, str):
            value = raw.strip().lower()
            if value in {"", "none", "null", "unlimited", "infinite"}:
                return None
            raw = value
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return 1000

    def _exception_message(self, etype: str, payload: dict) -> tuple[str, str]:
        """Translate ExceptionInjector records into user-facing stream events."""
        if etype == "machine_breakdown":
            mid = payload.get("machine_id")
            duration = payload.get("duration_steps")
            return "机器故障", f"{self._machine_label(mid)} 故障，预计维修 {duration} 步"
        if etype == "machine_recovery":
            return "机器恢复", f"{self._machine_label(payload.get('machine_id'))} 已恢复"
        if etype == "agv_breakdown":
            aid = payload.get("agv_id")
            duration = payload.get("duration_steps")
            return "AGV 故障", f"AGV-{aid} 故障，预计维修 {duration} 步"
        if etype == "agv_recovery":
            return "AGV 恢复", f"AGV-{payload.get('agv_id')} 已恢复"
        if etype == "temporary_obstacle":
            cell = payload.get("cell")
            duration = payload.get("duration_steps")
            return "临时障碍", f"格点 {cell} 出现临时障碍，持续 {duration} 步"
        if etype == "obstacle_clear":
            return "障碍清除", f"格点 {payload.get('cell')} 临时障碍已清除"
        if etype == "urgent_job_arrival":
            return "紧急插单", f"新增紧急 Job{payload.get('job_id')}，共 {payload.get('op_count')} 道工序"
        return "异常事件", etype

    def _machine_label(self, runtime_id) -> str:
        try:
            machine_id = int(runtime_id)
        except (TypeError, ValueError):
            return f"M{runtime_id}"
        metadata = self._machine_metadata.get(machine_id, {})
        return str(metadata.get("display_name") or f"M{machine_id}")

    def _to_public_xy(self, pos):
        """Pogema stores positions with an obs_radius border; UI/config use map-local xy."""
        if self.env is None:
            return list(pos)
        pogema = self.env.pogema_env
        obs_radius = getattr(pogema.grid_config, "obs_radius", 0) or 0
        x, y = pos
        return [int(x) - obs_radius, int(y) - obs_radius]

    def _to_internal_xy(self, pos):
        """UI/config use map-local xy; Pogema stores coordinates with an obs_radius border."""
        if self.env is None:
            return list(pos)
        pogema = self.env.pogema_env
        obs_radius = getattr(pogema.grid_config, "obs_radius", 0) or 0
        x, y = pos
        return [int(x) + obs_radius, int(y) + obs_radius]

    def _public_exception_payload(self, etype: str, payload: dict) -> dict:
        public_payload = deepcopy(payload or {})
        if etype in {"machine_breakdown", "machine_recovery"}:
            machine_id = public_payload.get("machine_id")
            try:
                metadata = self._machine_metadata.get(int(machine_id), {})
            except (TypeError, ValueError):
                metadata = {}
            public_payload["display_name"] = metadata.get("display_name", f"M{machine_id}")
            public_payload["config_key"] = metadata.get("config_key")
        if etype in {"temporary_obstacle", "obstacle_clear"}:
            cell = public_payload.get("cell")
            if isinstance(cell, (list, tuple)) and len(cell) >= 2:
                public_payload["cell"] = list(cell)
        if etype == "agv_breakdown":
            position = public_payload.get("position")
            if isinstance(position, (list, tuple)) and len(position) >= 2:
                public_payload["position"] = list(position)
        return public_payload

    def _public_exception_event(self, event: dict) -> dict:
        public_event = deepcopy(event)
        etype = public_event.get("type", "exception")
        public_event["payload"] = self._public_exception_payload(
            etype,
            public_event.get("payload") or {},
        )
        return public_event

    def _emit_exception_events(self, events: list[dict], step: int):
        """Emit factory event records through the same canonical event stream."""
        if not events:
            return
        for raw_event in events:
            # Business UI events retain the main frame-diff protocol.
            if raw_event.get("type") not in {
                "machine_breakdown", "machine_recovery", "agv_breakdown",
                "agv_recovery", "temporary_obstacle", "obstacle_clear",
            }:
                continue
            epoch = raw_event.get("event_epoch")
            if epoch is not None and epoch <= self._last_factory_event_epoch:
                continue
            event = self._public_exception_event(raw_event)
            etype = event.get("type", "exception")
            payload = event.get("payload") or {}
            title, message = self._exception_message(etype, payload)
            envelope = make_envelope(
                event.get("step", step),
                f"T+{event.get('step', step)}s",
                etype=etype,
                title=title,
                message=message,
                level=event.get("level"),
                payload=payload,
            )
            self._record_stream_event(envelope)
            if epoch is not None:
                self._last_factory_event_epoch = epoch

    def _normalize_manual_exception_event(self, event: dict) -> dict:
        normalized = deepcopy(event or {})
        if "delay_steps" in normalized:
            normalized["start_step"] = int(self.step) + max(0, int(normalized.get("delay_steps") or 0))
        if normalized.get("type") == "temporary_obstacle" and normalized.get("cell") is not None:
            cell = normalized.get("cell")
            if isinstance(cell, (list, tuple)) and len(cell) >= 2:
                normalized["cell"] = list(cell)
        return normalized

    def _normalize_manual_exception_target(self, target: dict | None) -> dict:
        normalized = deepcopy(target or {})
        if normalized.get("type") == "temporary_obstacle" and normalized.get("cell") is not None:
            cell = normalized.get("cell")
            if isinstance(cell, (list, tuple)) and len(cell) >= 2:
                normalized["cell"] = list(cell)
        return normalized

    def _broadcast_current_frame(self):
        if self.env is None:
            return
        frame = self._build_frame()
        self._latest_frame = frame
        with self._subs_lock:
            self._broadcast(self._state_subs, ("state", {"status": self._episode_status, "frame": frame}))

    def _emit_insert_event(self, etype: str, record: dict, **extra):
        step = record["timeline"][-1]["step"]
        payload = {
            "request_id": record["request_id"],
            "job_ids": list(record.get("job_ids", [])),
            "revision": record.get("revision"),
            "latency_ms": record.get("latency_ms"),
            "source": "manual",
            **extra,
        }
        titles = {
            "job_replan_started": ("插单重规划", "正在为紧急订单重排未承诺任务"),
            "urgent_job_arrival": ("紧急插单", "紧急订单已进入执行计划"),
            "job_replan_completed": ("重规划完成", "紧急订单已完成排程"),
            "job_replan_failed": ("重规划失败", record.get("error") or "无法生成新计划"),
        }
        title, message = titles[etype]
        self._record_stream_event(make_envelope(
            step, f"T+{step}s", etype=etype, title=title,
            message=message, level="error" if etype.endswith("failed") else "info",
            payload=payload,
        ))

    def _emit_insert_phase_event(self, record: dict):
        step = record["timeline"][-1]["step"]
        phase = record.get("phase", "queued")
        labels = {
            "queued": "排队", "replanning": "重规划", "scheduled": "已排程",
            "transporting": "运输中", "processing": "加工中",
            "completed": "已完成", "failed": "失败",
        }
        payload = {
            "request_id": record.get("request_id"),
            "phase": phase,
            "job_ids": list(record.get("job_ids", [])),
            "accepted_step": record.get("accepted_step"),
            "revision": record.get("revision"),
            "latency_ms": record.get("latency_ms"),
            "error": record.get("error"),
            "inserted": deepcopy(record.get("inserted", [])),
            "source": "manual",
        }
        self._record_stream_event(make_envelope(
            step, f"T+{step}s", etype="job_insertion_phase_changed",
            title="插单状态更新",
            message=f"{record.get('request_id')}：{labels.get(phase, phase)}",
            level="error" if phase == "failed" else ("success" if phase == "completed" else "info"),
            payload=payload,
        ))

    def _publish_insertion_phase(self, record):
        """Render a copied business update using the existing frontend event schema."""
        self._emit_insert_phase_event(record)
        if record["phase"] == "replanning":
            self._emit_insert_event("job_replan_started", record)
        elif record["phase"] == "scheduled":
            self._emit_insert_event("urgent_job_arrival", record)
            self._emit_insert_event("job_replan_completed", record)
        elif record["phase"] == "failed":
            self._emit_insert_event("job_replan_failed", record)

    @staticmethod
    def _validate_insert_job(raw_job, machine_count):
        if not isinstance(raw_job, list) or not raw_job or len(raw_job) > 20:
            raise ValueError("Job 必须包含 1~20 道工序")
        normalized = []
        for op_index, raw_op in enumerate(raw_job):
            if not isinstance(raw_op, list) or not raw_op:
                raise ValueError(f"工序 {op_index} 缺少候选机器")
            alternatives = []
            seen = set()
            for alt in raw_op:
                if not isinstance(alt, dict):
                    raise ValueError(f"工序 {op_index} 候选项格式错误")
                machine = alt.get("machine")
                processing = alt.get("processing")
                if isinstance(machine, bool) or not isinstance(machine, int) or not 0 <= machine < machine_count:
                    raise ValueError(f"工序 {op_index} 包含非法机器 {machine}")
                if machine in seen:
                    raise ValueError(f"工序 {op_index} 的机器 {machine} 重复")
                if isinstance(processing, bool) or not isinstance(processing, (int, float)) or processing <= 0:
                    raise ValueError(f"工序 {op_index} 加工时间必须大于 0")
                seen.add(machine)
                alternatives.append({"machine": machine, "processing": float(processing)})
            normalized.append(alternatives)
        return normalized

    def enqueue_insert_jobs(self, body: dict) -> dict:
        if self.env is None or not self.running:
            return {"status": "error", "phase": "rejected", "message": "仿真未运行，无法插单"}
        if self._replay_enabled or self._policy_controller is not None:
            return {"status": "error", "phase": "rejected", "message": "策略或回放模式不支持手动插单"}
        if self._fjsp_algorithm.lower() != "pso" or self._assigner_name.lower() != "nearest":
            return {"status": "error", "phase": "rejected", "message": "第一版仅支持 PSO + nearest"}
        pogema = self.env.pogema_env
        machine_count = len(pogema.machines)
        if (isinstance(body.get("machines"), bool)
                or not isinstance(body.get("machines"), int)
                or body.get("machines") != machine_count):
            return {"status": "error", "phase": "rejected", "message": f"机器数必须为 {machine_count}"}
        jobs = body.get("jobs")
        if not isinstance(jobs, list) or not jobs or len(jobs) > 20:
            return {"status": "error", "phase": "rejected", "message": "单次请求必须包含 1~20 个 Job"}
        metadata = (body.get("extensions") or {}).get("job_metadata")
        if metadata is not None and (not isinstance(metadata, list) or len(metadata) != len(jobs)):
            return {"status": "error", "phase": "rejected", "message": "job_metadata 必须与 jobs 一一对应"}
        metadata = metadata or [{} for _ in jobs]

        accepted_step = int(self.step)
        with self._insert_lock:
            request_id = f"insert-{self._next_insert_id:04d}"
            self._next_insert_id += 1
            accepted, rejected, pending_jobs = [], [], []
            for index, (raw_job, raw_meta) in enumerate(zip(jobs, metadata)):
                try:
                    operations = self._validate_insert_job(raw_job, machine_count)
                    raw_meta = raw_meta or {}
                    priority = int(raw_meta.get("priority", 100))
                    if priority <= 0:
                        raise ValueError("priority 必须大于 0")
                    due_in = raw_meta.get("due_in_steps")
                    due = None if due_in in (None, "") else accepted_step + int(due_in)
                    if due is not None and due <= accepted_step:
                        raise ValueError("due_in_steps 必须大于 0")
                    job_id = self._next_job_id
                    self._next_job_id += 1
                    name = str(raw_meta.get("name") or f"急单-{job_id}")
                    item = {"index": index, "job_id": job_id, "name": name,
                            "priority": priority, "due": due, "operations": operations,
                            "request_id": request_id}
                    pending_jobs.append(item)
                    accepted.append({k: item[k] for k in ("index", "job_id", "name", "priority", "due")})
                except (TypeError, ValueError) as exc:
                    rejected.append({"index": index, "reason": str(exc)})
            if not accepted:
                return {"status": "error", "phase": "rejected", "request_id": request_id,
                        "accepted_step": accepted_step, "inserted": [], "rejected": rejected}
        from sky_executor.perception.contracts import JobInsertionRequest
        request = JobInsertionRequest(request_id, tuple(pending_jobs), accepted_step, tuple(accepted), tuple(rejected))
        self.env.job_insertions.on_phase_change = self._publish_insertion_phase
        result = self.session.submit_job_insertion(request)
        if not result.applied:
            return {"status": "error", "phase": "rejected", "request_id": request_id, "message": result.reason}
        self.obs = self.session.obs
        self._broadcast_current_frame()
        return {"status": "partial" if rejected else "ok", "phase": "queued",
                "request_id": request_id, "accepted_step": accepted_step,
                "inserted": accepted, "rejected": rejected}


    def _reassign_unloaded_failed_agvs(self, session, worker):
        """Return physically uncollected tasks to the assignment queue."""
        env = session.env
        with env.process_business_chain(run_worker=worker):
            with env.state_lock:
                agents = [agent_id for agent_id, task in enumerate(env.state.agv_current_task)
                          if task is not None and env.state.agv_status[agent_id] != "OK"
                          and not env.state.agv_loaded[agent_id]]
                blocked_loaded = sum(task is not None and env.state.agv_status[i] != "OK"
                                     and env.state.agv_loaded[i]
                                     for i, task in enumerate(env.state.agv_current_task))
            result = env.apply_reschedule({"release_agvs": agents}) if agents else None
            reassigned = len(agents) if result is not None and result.applied else 0
            if result is not None and not result.applied:
                blocked_loaded += len(agents)
        snapshot = worker.request_snapshot().result()
        with env.read_state():
            env.require_current_run(worker)
            session.obs = snapshot.observation
            self.obs = session.obs
            self._recovery_metrics["race_agv_reassign_count"] += reassigned
            self._recovery_metrics["race_agv_reassign_blocked_loaded"] += blocked_loaded
        return reassigned

    def _recover_runtime(self, decision, delegate):
        """Execute the smallest runtime recovery selected by the RACE gate."""
        session = self.session
        env = session.env
        worker = env.ensure_perception_worker()
        generation = self._run_generation
        scope = decision.scope
        if scope == RecoveryScope.PATH_REPLAN:
            # Route solvers consume the changed map observation on this same step.
            return None
        if scope == RecoveryScope.AGV_REASSIGN:
            with self._env_lock:
                if generation != self._run_generation or self.session is not session:
                    raise RunReplaced("recovery belongs to a reset or closed run")
                self._reassign_unloaded_failed_agvs(session, worker)
        if scope not in {
            RecoveryScope.LOCAL_PRODUCTION_REPLAN,
            RecoveryScope.JOINT_ROLLING_REPLAN,
        }:
            return None

        from sky_executor.job_insertion import build_replan_problem
        with env.read_state():
            problem, _ = build_replan_problem(env, env.scene_adapter.planning_time(), [])
            total_unfinished = sum(operation.status != "FINISHED"
                                   for job in env.pogema_env.jobs for operation in job.ops)
        if not problem["jobs"]:
            if scope == RecoveryScope.JOINT_ROLLING_REPLAN:
                with self._env_lock:
                    if generation != self._run_generation or self.session is not session:
                        raise RunReplaced("recovery belongs to a reset or closed run")
                    self._reassign_unloaded_failed_agvs(session, worker)
            return None
        replanned_keys = frozenset((job["job_id"], op["op_id"]) for job in problem["jobs"] for op in job["operations"])
        replanned_count = len(replanned_keys)
        started = time.perf_counter()
        try:
            result = delegate.job_solver.replan(problem)
        except Exception as error:
            with self._env_lock:
                if generation != self._run_generation or self.session is not session:
                    raise RunReplaced("late recovery failure from a reset or closed run") from error
                with env.processing_lock:
                    try:
                        env.require_current_run(worker)
                    except RunReplaced as replaced:
                        raise replaced from error
                    self._recovery_metrics["race_residual_replan_failed"] += 1
            raise
        with self._env_lock:
            if generation != self._run_generation or self.session is not session:
                raise RunReplaced("late recovery plan from a reset or closed run")
            from sky_executor.perception.contracts import JobPlanningUpdate
            with env.processing_lock:
                env.require_current_run(worker)
                report = env.scene_adapter.job_report(JobPlanningUpdate(None, "scheduled", replanned_keys=replanned_keys))
                handle = worker.submit_report(report)
            applied = handle.result()
            if not applied.applied:
                error = RuntimeError("current recovery plan was rejected: " + applied.reason)
                env.fail_execution(error)
                raise error
            observation = worker.request_snapshot().result().observation
            with env.read_state():
                env.require_current_run(worker)
                session.obs = observation
                self.obs = session.obs
                latency = float(result.get("latency_ms", (time.perf_counter() - started) * 1000))
                self._recovery_metrics["race_residual_replan_count"] += 1
                self._recovery_metrics["race_residual_replan_latency_ms"] += latency
                self._recovery_metrics["race_replanned_operation_count"] += replanned_count
                self._recovery_metrics["race_last_replanned_fraction"] = replanned_count / max(total_unfinished, 1)
            if scope == RecoveryScope.JOINT_ROLLING_REPLAN:
                # Reassign only after the production plan has been accepted.
                self._reassign_unloaded_failed_agvs(session, worker)
        return None


    def inject_exception(self, event: dict) -> dict:
        if self.session is None:
            return {"status": "error", "message": "No simulation environment"}
        normalized = self._normalize_manual_exception_event(event)
        with self._env_lock:
            result = self.session.inject_exception(normalized, self.step)
            self.obs = self.session.obs
            raw_events = list(result.get("events", []))
            public_events = [self._public_exception_event(e) for e in raw_events]
            result["events"] = public_events
            if result.get("status") == "ok":
                self._broadcast_current_frame()
        if result.get("status") == "ok":
            self._emit_exception_events(raw_events, step=self.step)
        return result

    def clear_exceptions(self, target: dict | None = None) -> dict:
        if self.session is None:
            return {"status": "error", "message": "No simulation environment"}
        normalized_target = self._normalize_manual_exception_target(target)
        with self._env_lock:
            result = self.session.clear_exceptions(normalized_target, self.step)
            self.obs = self.session.obs
            raw_events = list(result.get("events", []))
            public_events = [self._public_exception_event(e) for e in raw_events]
            result["events"] = public_events
            if result.get("cleared"):
                self._broadcast_current_frame()
        if result.get("events"):
            self._emit_exception_events(raw_events, step=self.step)
        return result

    def create(self, config: dict):
        print(f"[sim_server] 创建环境: {config}")
        self._stop_internal()
        if self.session is not None:
            self.session.close()

        factory_config = config.get("config", {})
        self._replay_enabled = "replay_trace" in config or "replay_trace" in factory_config
        self._replay_actions = list(config.get("replay_trace") if "replay_trace" in config else factory_config.get("replay_trace") or [])
        policy_config = config.get("policy_controller") or factory_config.get("policy_controller") or {}
        self._policy_controller = None
        if policy_config:
            module_name, class_name = str(policy_config["target"]).rsplit(".", 1)
            policy_class = getattr(importlib.import_module(module_name), class_name)
            self._policy_controller = policy_class(**(policy_config.get("kwargs") or {}))
        fjsp_algo = config.get("fjsp_algorithm", "pso")
        mapf_algo = config.get("mapf_algorithm", "astar")
        assigner = config.get("solver_assign", "nearest")
        self._fjsp_algorithm = fjsp_algo
        self._assigner_name = assigner

        machines = (factory_config.get("topology") or {}).get("machines") or {}
        self._machine_metadata = {
            index: {
                "config_key": config_key,
                "config_id": machine.get("id", config_key),
                "display_name": machine.get("name") or machine.get("id") or config_key,
            }
            for index, (config_key, machine) in enumerate(machines.items())
        }

        # 用 use_io.py 同款逻辑解析配置 → 创建环境
        # Observation format is an explicit protocol field supplied by the caller.
        native_actions = self._policy_controller is not None or self._replay_enabled
        with self._env_lock:
            self.session = SimulationSession.from_config(
                factory_config,
                native_actions=native_actions,
                job_solver="http",
                route_solver="http",
                assigner=assigner,
                agent_observation_type=str(config.get("agent_observation_type", "default")),
                job_solver_kwargs={
                    "service_url": "http://fjsp:8002",
                    "algorithm": fjsp_algo,
                },
                route_solver_kwargs={
                    "service_url": "http://mapf:8001",
                    "pogema_env": None,
                    "accepts_task_observation": bool(config.get("route_accepts_task_observation", False)),
                },
            )
            self.env = self.session.env
            self.obs = self.session.obs

        # Coordinator: 固定用 HTTP 求解器，连接算法容器
        # 算法容器在同一 Docker 网络，用容器名 DNS 通信
        base_coordinator = self.session.coordinator
        if base_coordinator is not None:
            base_coordinator.route_solver.pogema_env = self.env.pogema_env
        race_config = config.get("race_fms") or factory_config.get("race_fms") or {}
        if not native_actions and bool(race_config.get("enabled", False)):
            estimator = None
            estimator_path = race_config.get("estimator_path")
            if estimator_path:
                payload = json.loads(Path(estimator_path).read_text(encoding="utf-8"))
                estimator = CounterfactualCouplingEstimator.from_dict(payload)
            gate = AdaptiveRecoveryGate(
                estimator=estimator,
                coordinate_threshold=float(race_config.get("coordinate_threshold", 0.05)),
                joint_threshold=float(race_config.get("joint_threshold", 0.20)),
                risk_threshold=float(race_config.get("risk_threshold", 0.65)),
                cooldown_steps=int(race_config.get("cooldown_steps", 2)),
                uncertainty_penalty=float(race_config.get("uncertainty_penalty", 0.25)),
                retrigger_margin=float(race_config.get("retrigger_margin", 0.10)),
            )
            self.coordinator = RaceFMSCoordinator(
                delegate=base_coordinator,
                gate=gate,
                recovery_handler=_SimulationRecoveryHandler(self),
            )
        else:
            self.coordinator = base_coordinator
        self.session.coordinator = self.coordinator
        # The online FJSP service owns a stateful schedule. Environment creation
        # must start a new schedule even when callers reuse algorithm containers.
        self.session.reset()
        if self._policy_controller is not None and hasattr(self._policy_controller, "reset"):
            self._policy_controller.reset()
        self.obs = self.session.obs
        self.max_steps = self._parse_max_steps(factory_config)
        self.step = 0
        self._next_insert_id = 1
        self._next_job_id = max((job.job_id for job in self.env.state._all_jobs), default=-1) + 1
        self._recovery_metrics = {
            "race_residual_replan_count": 0,
            "race_residual_replan_failed": 0,
            "race_residual_replan_latency_ms": 0.0,
            "race_replanned_operation_count": 0,
            "race_last_replanned_fraction": 0.0,
            "race_agv_reassign_count": 0,
            "race_agv_reassign_blocked_loaded": 0,
        }

        # L1: 重置 episode 状态与快照
        self._episode_status = "idle"
        self._latest_frame = None
        self._latest_metrics = None
        self._episode_summary = None
        self._heatmaps = None
        self._event_history = []
        self._diff.reset()
        self._last_factory_event_epoch = 0

        max_steps_label = self.max_steps if self.max_steps is not None else "unlimited"
        print(f"[sim_server] 环境创建完成, fjsp={fjsp_algo}, mapf={mapf_algo}, assigner={assigner}, max_steps={max_steps_label}")

    def play(self):
        if self.running and self.paused:
            self.paused = False
            self._pause_event.set()
            print("[sim_server] 仿真继续")
            return

        if self.running:
            return

        self.running = True
        self.paused = False
        self._episode_status = "running"
        self._stop_event.clear()
        self._pause_event.set()
        generation = self._run_generation
        self._thread = threading.Thread(target=self._run_loop, args=(generation,), daemon=True)
        self._thread.start()
        print("[sim_server] 仿真启动")

    def pause(self):
        self.paused = True
        self._pause_event.clear()
        print("[sim_server] 仿真暂停")

    def reset(self):
        self._stop_internal()
        if self.session:
            with self._env_lock:
                self.obs, info = self.session.reset()
                if self._policy_controller is not None and hasattr(self._policy_controller, "reset"):
                    self._policy_controller.reset()
                self.step = 0
                self._episode_status = "idle"
                self._latest_frame = None
                self._latest_metrics = None
                self._episode_summary = None
                self._heatmaps = None
                self._event_history = []
                self._next_insert_id = 1
                self._next_job_id = max((job.job_id for job in self.env.state._all_jobs), default=-1) + 1
                self._recovery_metrics = {
                    "race_residual_replan_count": 0,
                    "race_residual_replan_failed": 0,
                    "race_residual_replan_latency_ms": 0.0,
                    "race_replanned_operation_count": 0,
                    "race_last_replanned_fraction": 0.0,
                    "race_agv_reassign_count": 0,
                    "race_agv_reassign_blocked_loaded": 0,
                }
                self._diff.reset()
                self._last_factory_event_epoch = 0
        print("[sim_server] 环境已重置")

    def stop(self):
        self._stop_internal()
        self._episode_status = "stopped"
        print("[sim_server] 仿真停止")

    def shutdown(self):
        self._stop_internal(wait=False)
        if self.session is not None:
            self.session.close()

    def _stop_internal(self, *, wait=True):
        self._run_generation += 1
        self._stop_event.set()
        self._pause_event.set()
        if wait and self._thread:
            self._thread.join(timeout=10)
        self.running = False
        self._thread = None

    def _build_frame(self) -> dict:
        from sky_executor.runtime_log import build_runtime_frame
        return build_runtime_frame(self.session)

    def _dump_agv_state(self, tag: str = ""):
        """诊断: 打印每个 AGV 的位置 + current_task，定位死锁。"""
        if not self.env:
            return
        try:
            pogema = self.env.pogema_env
            agv_list = pogema.get_agv_info()
            lines = []
            for i, agv in enumerate(agv_list):
                pos = tuple(agv.pos) if hasattr(agv, "pos") else "?"
                tgt = getattr(agv, "target", None)
                tgt = tuple(tgt) if tgt is not None else None
                task = getattr(agv, "current_task", None)
                lines.append(f"AGV{i}@{pos} tgt={tgt} task={task}")
            print(f"[sim_server] [{tag}] " + " | ".join(lines), flush=True)
        except Exception as e:
            print(f"[sim_server] [{tag}] dump 失败: {e}", flush=True)

    def _run_loop(self, generation: int):
        import time
        try:
            while not self._stop_event.is_set():
                self._pause_event.wait()
                if self._stop_event.is_set() or generation != self._run_generation:
                    break

                # ---- 统一会话步进 ----
                self._dump_agv_state("pre-decide")
                t0 = time.time()
                print(f"[sim_server] step={self.step} 开始 step...", flush=True)
                with self._env_lock:
                    if self._stop_event.is_set() or generation != self._run_generation:
                        break
                    session = self.session
                    controller = self._policy_controller
                    observation = self.obs
                    if self._replay_enabled and self.step >= len(self._replay_actions):
                        self._episode_status = "replay_exhausted"
                        with self._subs_lock:
                            self._broadcast(self._state_subs, ("state", {
                                "status": "replay_exhausted", "frame": self._latest_frame,
                            }))
                        break
                    action = self._replay_actions[self.step] if self._replay_enabled else None
                # Inference can block. Keep it outside the manager and core locks,
                # and discard results from a run replaced by reset/create/stop.
                if not self._replay_enabled and controller is not None:
                    action = controller.act(observation, None, deterministic=True)
                if self._stop_event.is_set() or generation != self._run_generation:
                    break
                result = session.step(action)
                with self._env_lock:
                    if self._stop_event.is_set() or generation != self._run_generation:
                        break
                    self.obs, rewards, terminations, truncations, infos = result
                    self.step = session.step_index
                    elapsed = time.time() - t0
                    print(f"[sim_server] step={self.step} 完成 ({elapsed:.2f}s)", flush=True)
                    frame = self._build_frame()
                    self._latest_frame = frame
                print(f"[sim_server] step={self.step} frame 已生成, "
                      f"AGV数={len(frame['grid_state']['positions_xy'])}, "
                      f"机器数={len(frame['machines'])}, "
                      f"transfers={len(frame['active_transfers'])}", flush=True)

                # 异常事件（已提交的故障变化）与状态跃迁事件（DiffEmitter）共用前端 event stream。
                self._emit_exception_events(infos.get("events", []), step=self.step)

                # 派生业务事件（Rule 注册表 + 信封归一化）
                self._diff.diff(frame, step=self.step)

                state_event = ("state", {"status": "running", "frame": frame})
                metrics_payload = dict(infos.get("metrics", {}) or {})
                event_metrics_payload = dict(infos.get("event_metrics", {}) or {})
                metrics_payload.update(event_metrics_payload)
                with self.env.read_state():
                    metrics_payload.update(self.env.job_insertions.metrics)
                metrics_payload.update(self._recovery_metrics)
                get_race_metrics = getattr(self.coordinator, "get_race_metrics", None)
                if callable(get_race_metrics):
                    metrics_payload.update(get_race_metrics())
                metrics_data = {
                    "status": "running",
                    "step": self.step,
                    "metrics": metrics_payload,
                    "event_metrics": event_metrics_payload,
                    "metrics_reward": infos.get("metrics_reward", 0.0),
                }
                self._latest_metrics = metrics_data
                metrics_event = ("metrics", metrics_data)

                # L1: 广播给所有订阅者（线程安全的 threading.Queue）
                with self._subs_lock:
                    num_state_subs = len(self._state_subs)
                    num_metrics_subs = len(self._metrics_subs)
                    self._broadcast(self._state_subs, state_event)
                    self._broadcast(self._metrics_subs, metrics_event)

                print(f"[sim_server] step={self.step} 已广播: "
                      f"state订阅者={num_state_subs}, metrics订阅者={num_metrics_subs}", flush=True)

                hit_step_limit = self.max_steps is not None and self.step >= self.max_steps
                if terminations.get("job_done") or hit_step_limit:
                    # lifecycle 事件：job_done → episode_completed；步数上限 → episode_truncated
                    if terminations.get("job_done"):
                        self._diff.emit_lifecycle("episode_completed", step=self.step)
                    else:
                        self._diff.emit_lifecycle("episode_truncated", step=self.step)
                    # episode 结束时发送汇总 + 热力图
                    summary = self.session.metrics()
                    summary.update(self._recovery_metrics)
                    if callable(get_race_metrics):
                        summary.update(get_race_metrics())
                    heatmaps = self.session.heatmaps()
                    self._episode_summary = summary
                    self._heatmaps = {
                        "transit": heatmaps["transit"].tolist(),
                        "occupancy": heatmaps["occupancy"].tolist(),
                        "obstacles": heatmaps["obstacles"].tolist(),
                    }
                    done_metrics_event = ("metrics", {
                        "status": "stopped",
                        "step": self.step,
                        "episode_summary": summary,
                        "heatmap": self._heatmaps,
                    })
                    done_event = ("state", {"status": "stopped", "frame": frame})

                    self._episode_status = "stopped"
                    with self._subs_lock:
                        self._broadcast(self._metrics_subs, done_metrics_event)
                        self._broadcast(self._state_subs, done_event)
                    self.running = False
                    break

                # 每步间隔，给前端渲染时间 + 避免 decide 过快压垮 fjsp/mapf
                self._stop_event.wait(0.5)
        except RunReplaced:
            return
        except Exception as e:
            if generation != self._run_generation:
                return
            # _run_loop 线程异常退出（如 coordinator.decide 连不上 fjsp/mapf）。
            # 必须重置 running flag，否则后续 play() 会走 if self.running: return
            # 直接返回，仿真永远无法重启。
            import traceback
            print(f"[sim_server] _run_loop 异常崩溃:\n{traceback.format_exc()}")
            self._episode_status = "error"
            err_event = ("state", {"status": "error", "error": str(e), "frame": self._latest_frame})
            with self._subs_lock:
                self._broadcast(self._state_subs, err_event)
        finally:
            if generation == self._run_generation:
                self.running = False
                self._thread = None


manager = SimulationManager()


# ==================== HTTP 接口 ====================

@app.post("/sim/create")
async def create_sim(config: dict):
    try:
        manager.create(config)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "ok"}


@app.post("/sim/play")
async def play():
    manager.play()
    return {"status": "ok"}


@app.post("/sim/pause")
async def pause():
    manager.pause()
    return {"status": "ok"}


@app.post("/sim/reset")
async def reset():
    manager.reset()
    return {"status": "ok"}


@app.post("/sim/stop")
async def stop():
    manager.stop()
    return {"status": "ok"}


@app.post("/sim/exception/inject")
async def inject_exception(body: dict):
    return manager.inject_exception(body)


@app.post("/sim/exception/clear")
async def clear_exceptions(body: dict | None = None):
    return manager.clear_exceptions(body or {})


@app.post("/sim/insert_jobs")
async def insert_jobs(body: dict):
    return manager.enqueue_insert_jobs(body)


@app.get("/sim/state")
async def get_state():
    return {"step": manager.step, "running": manager.running, "paused": manager.paused,
            "max_steps": manager.max_steps, "fjsp_algorithm": manager._fjsp_algorithm,
            "race_fms_enabled": isinstance(manager.coordinator, RaceFMSCoordinator),
            "assigner": manager._assigner_name, "supports_job_insertion": (
                not manager._replay_enabled and manager._policy_controller is None
                and manager._fjsp_algorithm.lower() == "pso" and manager._assigner_name.lower() == "nearest"
            )}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/stream/state")
async def stream_state():
    """L1: 每个连接独立订阅，断开时自动 unsubscribe。"""
    q = manager.subscribe("state")

    async def generate():
        try:
            while True:
                # threading.Queue.get(block=True, timeout=1.0)：
                # 带超时是为了让 executor 线程定期释放，避免客户端断开后
                # q.get() 永久阻塞导致线程泄漏 + event loop 卡死。
                try:
                    event = await asyncio.to_thread(q.get, True, 1.0)
                except thread_queue.Empty:
                    continue
                event_type, data = event
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        finally:
            manager.unsubscribe("state", q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/stream/metrics")
async def stream_metrics():
    """L1: 每个连接独立订阅，断开时自动 unsubscribe。"""
    q = manager.subscribe("metrics")

    async def generate():
        try:
            while True:
                try:
                    event = await asyncio.to_thread(q.get, True, 1.0)
                except thread_queue.Empty:
                    continue
                event_type, data = event
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        finally:
            manager.unsubscribe("metrics", q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/stream/events")
async def stream_events():
    """L1: 每个连接独立订阅 events，断开时自动 unsubscribe。"""
    q = manager.subscribe("events")

    async def generate():
        try:
            while True:
                try:
                    event = await asyncio.to_thread(q.get, True, 1.0)
                except thread_queue.Empty:
                    continue
                event_type, data = event
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        finally:
            manager.unsubscribe("events", q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
