"""
@Project ：SkyEngine
@File    ：grid_factory_env.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2025/1/15 10:00
"""

from contextlib import contextmanager
from collections.abc import Mapping
from threading import RLock
from copy import deepcopy
from typing import List, Tuple, Optional

from pettingzoo import ParallelEnv
from pogema.grid import Grid
from pogema import GridConfig, AnimationMonitor

from sky_executor.utils.registry import register_component
from sky_executor.lifecycle import RunReplaced
from sky_executor.planning import PlanRejected
from sky_executor.grid_factory.factory.Utils.structure import (
    MachineConfig,
    JobConfig,
)

from sky_executor.grid_factory.factory.assign_env import (
    PogemaLifeLongWithAssign,
)
from sky_executor.grid_factory.factory.business import (
    DecisionApplier,
    BusinessSettler,
    BusinessStatistics, routing_task_key,
)
from sky_executor.grid_factory.factory.Utils.machine import (
    generate_machines,
)
from sky_executor.grid_factory.factory.Utils.job import generate_jobs
from sky_executor.grid_factory.factory.Metrics.hub import MetricsHub
from sky_executor.faults import FaultInjector
from sky_executor.events import FactoryEvent, FactoryEventRecorder
from sky_executor.perception import (
    ConfirmationResult,
    ConfirmationStatus,
    ObservationBatch,
    PerceptionReport,
    AgvObservation,
    PerceptionWorker,
    ObservationRejectedError,
    ObservationConfirmationExhaustedError,
    ObservationConfirmationPolicy,
    StateReconciler,
    StrictStateReconciler,
    create_confirmation_policy,
)
from sky_logs.logger import LOGGER


@register_component("factory")
class GridFactoryEnv(ParallelEnv):
    """
    基于Pogema的网格工厂环境

    功能特性:
    1. 使用Pogema作为底层网格环境
    2. 支持多智能体路径规划
    3. 集成事件系统和回调机制
    4. 支持工厂任务调度

    注意环境reset之后才能有grid相关结构
    """

    metadata = {"render_modes": ["human"], "name": "grid_factory_env"}

    def __init__(
        self,
        grid_config: Optional[GridConfig] = None,
        machine_config: Optional[MachineConfig] = None,
        job_config: Optional[JobConfig] = None,
        random_target=False,
        metrics_mode: str = 'rl',
        exception_config: Optional[dict] = None,
        processing_time_config: Optional[dict] = None,
        material_handling_config: Optional[dict] = None,
        headless: bool = False,
        public_grid_size: Optional[Tuple[int, int]] = None,
        perception_config: Optional[dict] = None,
        scene_factory=None,
        machine_preparation="before_simulation_step",
    ):
        """
        初始化网格工厂环境
        Args:
            grid_config: Pogema网格配置
            agent: 智能体实例
            env_config: 环境配置
        """
        super().__init__()
        if machine_preparation not in {"before_simulation_step", "after_settlement"}:
            raise ValueError("unknown machine_preparation")
        self.machine_preparation = machine_preparation

        # 环境状态
        self.env_timeline = 0  # 离散化的环境时间

        # Pogema环境
        self.pogema_env: PogemaLifeLongWithAssign | None = None
        self.grid_config = grid_config or self._create_default_grid_config()
        self.grid_config.collision_system = "soft"

        # 机器组件 也就是路由的起始点和终止点
        self.machine_config = machine_config or self._create_default_machine_config()

        # 任务组件
        self.job_config = job_config or self._create_default_job_config()
        self.processing_time_config = processing_time_config
        self.material_handling_config = material_handling_config
        self.headless = bool(headless)

        # 动画保存路径
        self.initialize_pogema_env(random_target)
        self.init_machines = self.initialize_machine_env()
        self.init_jobs = self.initialize_job_env()

        # 统一指标收集器
        self.metrics_hub = MetricsHub(self, mode=metrics_mode)

        # 异常注入器。未提供 exception_config 时默认关闭。
        self.fault_config = FaultInjector.configuration_from_env(exception_config)
        self.events = FactoryEventRecorder(self.state, self.fault_config.get("exception_log_path"))

        # 感知边界使用不含 Pogema padding 的公共网格坐标。
        self.public_grid_size = public_grid_size or self._infer_public_grid_size()
        self.perception_config = perception_config
        self.state_reconciler: StateReconciler = StrictStateReconciler()
        confirmation_policy, confirmation_max_observations = (
            create_confirmation_policy(perception_config)
        )
        self.confirmation_policy: ObservationConfirmationPolicy = (
            confirmation_policy
        )
        self.confirmation_max_observations = confirmation_max_observations
        self.latest_observation_batch: ObservationBatch | None = None
        self.latest_confirmation_result: ConfirmationResult | None = None
        self.latest_confirmed_positions: dict[int, tuple[int, int]] = {}
        self.perception_worker = None
        self._bootstrapping_positions = False
        self._worker_options = None
        self._controller = None
        self.processing_lock = RLock()
        self.simulation_step_lock = RLock()
        self.decision_lock = RLock()
        self._controller_lock = RLock()
        from sky_executor.decision import DecisionNotifications
        self.decision_notifications = DecisionNotifications()
        self._business_chain_depth = 0
        self._business_started = False
        self._business_changes = []
        self._machines_to_prepare = set()
        self.execution_failure = None
        self._order_admission_closed = False
        from sky_executor.job_insertion import JobInsertions
        self.job_insertions = JobInsertions(self)
        state = self.state
        self.decision_applier = DecisionApplier(state)
        self.business_settler = BusinessSettler(state, self.record_factory_event)
        self.business_statistics = BusinessStatistics(state)
        self._assemble_runtimes()
        self._simulation_snapshot = None
        self._movement_since_tick = {}
        self.last_actions = None
        from sky_executor.simulation import SimulationAdapter
        self.scene_adapter = (scene_factory or SimulationAdapter)(self)


    def _create_default_grid_config(self) -> GridConfig:
        """创建默认的网格配置"""
        return GridConfig(
            num_agents=4,
            size=8,
            density=0.1,
            seed=42,
            max_episode_steps=256,
            obs_radius=5,
            on_target="restart",
        )

    def _create_default_machine_config(self):
        """创建默认的机器配置"""
        return MachineConfig(
            num_machines=8,
            strategy="random",
            seed=42,
            zones=4,
            grid_spacing=5,
            noise=1.0,
        )

    def _create_default_job_config(self):
        """创建默认的任务配置"""
        return JobConfig(
            num_jobs=6,
            min_ops_per_job=2,
            max_ops_per_job=3,
            min_proc_time=2,
            max_proc_time=7,
            machine_choices=2,
            total_machines=self.machine_config.num_machines,
            seed=42,
        )

    def _infer_public_grid_size(self) -> Tuple[int, int]:
        """Infer the unpadded coordinate bounds for direct environment users."""
        raw_map = getattr(self.grid_config, "map", None)
        if isinstance(raw_map, str):
            rows = raw_map.splitlines()
            if rows:
                return len(rows), max(len(row) for row in rows)
        if isinstance(raw_map, (list, tuple)) and raw_map:
            return len(raw_map), max(len(row) for row in raw_map)
        size = int(getattr(self.grid_config, "size", 0) or 0)
        return size, size

    @property
    def state(self):
        """The one existing factory state, independent of animation wrappers."""
        return self._state

    @property
    def state_lock(self):
        """Protect complete write/settlement or snapshot operations on this environment.

        Callers must release it before waiting for Worker results or closing
        the Worker. Legacy step/reset and the serial reference controller are
        not concurrent entry points.
        """
        return self.state.state_lock

    def _assemble_runtimes(self):
        from sky_executor.agv_execution import AgvExecutionRuntime
        from sky_executor.machine_execution import MachineExecutionRuntime
        state = self.state
        self.agv_runtime = AgvExecutionRuntime(state)
        self.machine_runtime = MachineExecutionRuntime(state)
        self.report_handler = None

    def register_execution_intents(self, intents):
        from sky_executor.execution import HandlingIntent
        for intent in intents:
            if isinstance(intent, HandlingIntent):
                self.agv_runtime.request_handling(intent)
            else:
                self.machine_runtime.request_processing(intent)

    def ensure_business_started(self, *, run_worker=None):
        """Prepare initial work once per run, independently of decision policy."""
        with self.process_business_chain(run_worker=run_worker):
            if self._business_started:
                return
            if self.machine_preparation == "after_settlement":
                self.prepare_machine_work()
            self._business_started = True

    def prepare_machine_work(self, machine_ids=None):
        """Select and register work; the enclosing business chain dispatches it."""
        with self.state_lock:
            if machine_ids is None:
                machine_ids = tuple(machine.id for machine in self.state.activated_machines)
            machine_ids = tuple(machine_ids)
            blocked = {machine.id for machine in self.state.machines
                       if machine.id in machine_ids and machine.current_op is not None
                       and machine.current_op.status == "FINISHED"}
            for machine_id in blocked:
                if self.business_settler.release_finished_operation(machine_id):
                    self.decision_applier.refresh_buffered_tasks(
                        include_finished_goods=self.scene_adapter.immediate_material_settlement)
                    self.record_business_change("material_released", machine_id)
            if not self.scene_adapter.immediate_material_settlement:
                machine_ids = tuple(machine_id for machine_id in machine_ids if machine_id not in blocked)
            self.register_execution_intents(self.decision_applier.prepare_machine_work(machine_ids))

    def can_complete_dropoff(self, request):
        with self.state_lock:
            if request.kind != "dropoff":
                return True
            return self.business_settler.can_dropoff(self.state.agv_current_task[request.agv_ids[0]])

    def settle_material_changes(self, machine_ids):
        if not machine_ids or not self.scene_adapter.immediate_material_settlement:
            return
        settlement = self.business_settler.settle_material_changes(machine_ids)
        self.register_execution_intents(settlement.execution_intents)
        self.machines_ready_after_settlement(machine_ids)
        if settlement.changed:
            self.record_business_change("material_changed", tuple(machine_ids))

    def machines_ready_after_settlement(self, machine_ids):
        if self.machine_preparation == "after_settlement":
            self._machines_to_prepare.update(machine_ids)

    def record_factory_event(self, event):
        self.events.record(event.step, event.kind, event.payload, event.level)

    def record_fact_commit(self, result):
        """Describe a committed resource change before attempting its business consequences."""
        from sky_executor.perception.contracts import (
            AgvAvailabilityObservation, MachineAvailabilityObservation, TemporaryObstacleObservation,
        )
        base = self.state
        for change in result.events:
            fact = change.report.fact
            if isinstance(fact, AgvAvailabilityObservation):
                down = change.after == "DOWN"
                base.agv_epoch += 1
                kind = "agv_breakdown" if down else "agv_recovery"
                payload = {"agv_id": fact.agv_id}
                if down:
                    task = base.agv_current_task[fact.agv_id]
                    payload.update(reason=fact.reason,
                        position=list(base._to_public_xy(base.grid.positions_xy[fact.agv_id])),
                        current_task_id=task.task_id if task else None)
                metric = "agv_failure_count" if down else "agv_recovery_count"
            elif isinstance(fact, MachineAvailabilityObservation):
                down = change.after != "OK"
                base.machine_epoch += 1
                kind = "machine_breakdown" if down else "machine_recovery"
                payload = {"machine_id": fact.machine_id}
                if down:
                    op = next(m for m in base.machines if m.id == fact.machine_id).current_op
                    payload.update(reason=fact.reason,
                        current_op={"job_id": op.job_id, "op_id": op.op_id} if op else None)
                metric = "machine_failure_count" if down else "machine_recovery_count"
            elif isinstance(fact, TemporaryObstacleObservation):
                down = change.after == "BLOCKED"
                kind = "temporary_obstacle" if down else "obstacle_clear"
                payload = {"cell": list(fact.grid_cell)}
                metric = "temporary_obstacle_count" if down else "obstacle_clear_count"
            else:
                continue
            self.events.increment(metric)
            self.record_factory_event(FactoryEvent(base.env_timeline, kind, payload,
                                                  "warning" if down else "info"))

    def record_business_change(self, kind, subject=None):
        self._business_changes.append((kind, subject))

    def require_execution_running(self):
        if self.execution_failure is not None:
            raise RuntimeError("execution failed; full reset before continuing") from self.execution_failure
        for runtime in (self.machine_runtime, self.agv_runtime):
            runtime.require_running()

    def require_current_run(self, worker):
        """Reject operations bound to a replaced or closed run."""
        with self.processing_lock:
            if worker is None or self.perception_worker is not worker:
                raise RunReplaced("operation belongs to a reset or closed run")

    @contextmanager
    def run_operation(self, worker):
        """Guard a run without holding core locks across the operation."""
        with self.processing_lock:
            self.require_current_run(worker)
            self.require_execution_running()
        try:
            yield
        except (RunReplaced, PlanRejected):
            raise
        except BaseException as error:
            with self.processing_lock:
                if self.perception_worker is not worker:
                    raise RunReplaced("late result from a reset or closed run") from error
                self.fail_execution(error)
            raise
        else:
            self.require_current_run(worker)

    def close_run_worker(self, worker):
        """Close only this run's Worker, outside core locks."""
        with self.processing_lock:
            if worker is None or self.perception_worker is not worker:
                return
        worker.close()

    def fail_execution(self, error):
        with self.processing_lock:
            if self.execution_failure is None:
                self.execution_failure = error
            self.decision_notifications.close()

    def dispatch_pending_requests(self):
        """Dispatch and settle the entire immediate chain in this processing boundary."""
        from sky_executor.execution import AgvRequest
        runtimes = (self.machine_runtime, self.agv_runtime)
        while True:
            with self.state_lock:
                requests = tuple(request for runtime in runtimes for request in runtime.take_requests())
            if not requests:
                return
            if self.report_handler is None:
                self.ensure_perception_worker()
            for request in requests:
                update = (self.scene_adapter.submit_agv_request(request) if isinstance(request, AgvRequest)
                          else self.scene_adapter.submit_machine_request(request))
                if update.request_id != request.request_id:
                    raise RuntimeError("execution returned an update for another request")
                update_result = self.report_handler.apply_execution_report(self.scene_adapter.execution_report(update))
                if not update_result.applied:
                    raise RuntimeError("immediate execution update rejected: " + update_result.reason)


    def apply_decision(self, context, *, run_worker=None):
        self.require_execution_running()
        if context.applied:
            raise RuntimeError("decision already applied")
        with self.process_business_chain(run_worker=run_worker):
            adjustment = self.apply_reschedule(context.decision.get("reschedule") or {})
            if not adjustment.applied:
                raise PlanRejected(adjustment.reason)
            with self.state_lock:
                applier = self.decision_applier
                actions = context.decision
                requests = [applier.resolve_job_request(request)
                            for request in actions.get("job_actions", {}).get("transfer_requests", ())]
                applier.replace_job_requests(requests)
                requests, assignments = applier.receive_task_requests(actions.get("assign_actions", {}))
                intents = applier.prepare_requested_tasks(requests)
                refreshed = applier.refresh_buffered_tasks()
                if requests or refreshed:
                    self.record_business_change("tasks_changed", tuple(routing_task_key(task)
                                                    for task in (*requests, *refreshed)))
                context.assigned_agv_ids = applier.apply_requested_assignments(assignments)
                settlement = self.business_settler.settle_after_assignment(
                    assigned_agv_ids=context.assigned_agv_ids)
                self.register_execution_intents((*intents, *settlement.execution_intents))
                self.machines_ready_after_settlement(
                    machine.id for machine in self.state.activated_machines)
                if context.assigned_agv_ids or settlement.changed:
                    self.record_business_change("decision_applied", context.assigned_agv_ids)
                context.invalidated_agv_ids.update(
                    self.decision_applier.invalidated_actions(context.movement_basis))
                self.last_actions = deepcopy(actions)
        context.applied = True
        return settlement


    def submit_movement(self, context, *, run_worker=None):
        """Register this decision once; simulation consumes accepted moves later."""
        self.require_execution_running()
        if context.dispatched:
            raise RuntimeError("decision movement already dispatched")
        with self.process_business_chain(run_worker=run_worker):
            with self.state_lock:
                context.invalidated_agv_ids.update(
                    self.decision_applier.invalidated_actions(context.movement_basis))
                commands = self.decision_applier.constrain_agent_actions(
                    context.decision["agent_actions"], context.movement_basis,
                    context.assigned_agv_ids, context.invalidated_agv_ids)
            commands = self._register_movement_requests(commands)
        context.dispatched = True
        return commands


    def apply_execution_reports(self, reports, *, run_worker=None):
        """Adopt execution evidence and settle its immediate follow-up chain."""
        with self.process_business_chain(run_worker=run_worker):
            for report in reports:
                update_result = self.report_handler.apply_execution_report(report)
                if not update_result.applied:
                    raise RuntimeError("execution report rejected: " + update_result.reason)
                self.dispatch_pending_requests()

    def _register_movement_requests(self, actions):
        state = self.state
        dispatched = [0] * len(actions)
        with self.state_lock:
            commands = tuple(0 if i in self.agv_runtime.active_handling_requests or state.agv_status[i] != "OK"
                             else action for i, action in enumerate(actions))
            for agv_ids, group_actions in self.scene_adapter.movement_groups(commands):
                if self.agv_runtime.request_movement(agv_ids, group_actions) is not None:
                    for agv_id, action in zip(agv_ids, group_actions):
                        dispatched[agv_id] = action
        return dispatched

    def movement_bindings(self):
        from sky_executor.execution import ExecutionStatus
        with self.state_lock:
            return {agv_id: record.request.request_id for record in self.agv_runtime.execution_records.values()
                    if record.request.kind == "move" and not record.business_settled and not record.cancelled
                    and record.execution_status is ExecutionStatus.COMPLETED for agv_id in record.request.agv_ids}

    def runnable_handling_request_ids(self) -> tuple[str, ...]:
        """Handling execution request IDs whose AGVs currently allow progress."""
        with self.state_lock:
            return tuple(request_id for agv_id, request_id in sorted(self.agv_runtime.active_handling_requests.items())
                         if self.state.agv_status[agv_id] == "OK")

    def runnable_machine_request_ids(self) -> tuple[str, ...]:
        """Processing execution request IDs whose machines currently allow progress."""
        with self.state_lock:
            machines = {machine.id: machine for machine in self.state.machines}
            return tuple(request_id for machine_id, request_id in self.machine_runtime.processing_requests.items()
                if machines[machine_id].status == "OK" and self.state.hash_operations[
                    self.machine_runtime.execution_records[request_id].operation_key].status == "PROCESSING")

    def handling_agv_ids(self, request_ids):
        with self.state_lock:
            return {agv_id for request_id in request_ids
                    for agv_id in self.agv_runtime.execution_records[request_id].request.agv_ids}

    def simulated_movement_participants(self):
        """Check unstarted simulated commands, without constraining autonomous movement."""
        from sky_executor.grid_factory.factory.business import agv_action_basis
        state = self.state
        records = self.agv_runtime.accepted_movement_records()
        for record in records:
            for agv_id, action, basis in zip(record.request.agv_ids, record.request.actions, record.movement_basis):
                current = agv_action_basis(state.agv_current_task[agv_id], state.agv_task_phase[agv_id],
                                          state._to_public_xy(state.grid.positions_xy[agv_id]))
                if action and current != basis:
                    raise RuntimeError("accepted simulation movement origin or task changed")
        return tuple(record.request.request_id for record in records)

    def make_position_report(self, agv_id, position, *, source="scene-positions"):
        with self.processing_lock, self.scene_adapter._input_lock, self.state_lock:
            self.scene_adapter._require_input_open()
            return self.scene_adapter._report(AgvObservation(agv_id, tuple(position)), source,
                                              self.movement_bindings().get(agv_id))

    def submit_scene_positions(self, *, run_worker=None):
        """Sample pull sources; push scenes publish position reports independently."""
        if self.scene_adapter.position_source is not None:
            return self._synchronize_perception_state(run_worker=run_worker)

    def configure_operation_profiles(self, jobs):
        from copy import deepcopy
        self.scene_adapter.configure_operations({(job.job_id, operation.op_id): deepcopy(operation.processing_time_config)
                                                for job in jobs for operation in job.ops})

    @contextmanager
    def process_business_chain(self, *, run_worker=None):
        """Serialize one root input, including its immediate execution results."""
        with self.processing_lock:
            if run_worker is not None:
                self.require_current_run(run_worker)
            self.require_execution_running()
            self._business_chain_depth += 1
            try:
                yield
                if self._business_chain_depth == 1:
                    while True:
                        self.dispatch_pending_requests()
                        if not self._machines_to_prepare:
                            break
                        machine_ids = tuple(sorted(self._machines_to_prepare))
                        self._machines_to_prepare.clear()
                        self.prepare_machine_work(machine_ids)
                    with self.state_lock:
                        self.job_insertions.refresh_execution_phases()
                    self.decision_notifications.publish(self._business_changes)
                    self._business_changes.clear()
            except (RunReplaced, PlanRejected):
                raise
            except BaseException as error:
                self.fail_execution(error)
                raise
            finally:
                self._business_chain_depth -= 1

    @contextmanager
    def read_state(self):
        """Copy a state view after the current immediate business chain."""
        with self.processing_lock, self.state_lock:
            yield

    def configure_scene(self, scene_factory):
        """Replace assembly only before inputs start; use full reset before running."""
        if self.env_timeline != 0 or self._controller is not None or self.perception_worker is not None:
            raise RuntimeError("assemble scenes before starting inputs; use a fresh or reset environment")
        self.scene_adapter.stop_inputs()
        for runtime in (self.machine_runtime, self.agv_runtime):
            runtime.close()
        for binding in (self.scene_adapter.machine_binding, self.scene_adapter.agv_binding):
            binding.execution_port.close()
        self.scene_adapter.close()
        self.scene_adapter = scene_factory(self)
        self._assemble_runtimes()
        self.scene_adapter.validate_initial_layout()
        if self.scene_adapter.position_source is not None:
            self.scene_adapter.position_source.reset()
        self.configure_simulation_seed(self.state.episode_seed)
        self.scene_adapter.reset_state()
        cutoff = self.scene_adapter.planning_time()
        self.state.jobs = [job for job in self.state._all_jobs if job.release <= cutoff]
        self.state._future_jobs = [job for job in self.state._all_jobs if job.release > cutoff]
        self.state.hash_operations = self.state.create_hash_operations()
        self.configure_operation_profiles(self.state._all_jobs)
        self.state_reconciler.reset()
        self.confirmation_policy.reset()
        self.latest_observation_batch = None
        self.latest_confirmation_result = None

    def create_report_handler(self, **options):
        from sky_executor.perception.handling import ReportHandler
        self.report_handler = ReportHandler(
            self, **options,
            on_fact_committed=self.record_fact_commit,
            check_position_reports=self.scene_adapter.check_position_reports,
        )
        return self.report_handler


    def stop_perception_worker(self):
        """Join before touching the source or resetting state; never hold state_lock."""
        with self.processing_lock:
            worker = self.perception_worker
        self.close_run_worker(worker)
        with self.processing_lock:
            if self.perception_worker is worker:
                self.perception_worker = None
                self._worker_options = None

    def start_perception_worker(self, *, required_position_samples=None, temporary_obstacle_source=None):
        options = dict(required_position_samples=required_position_samples,
                       temporary_obstacle_source=temporary_obstacle_source)
        if self.perception_worker is not None and options == self._worker_options:
            return self.perception_worker
        self.stop_perception_worker()
        self.perception_worker = PerceptionWorker(self, **options)
        self._worker_options = options
        return self.perception_worker

    def ensure_perception_worker(self):
        if self.perception_worker is None:
            return self.start_perception_worker(temporary_obstacle_source=self.scene_adapter.source + "-map")
        return self.perception_worker

    def submit_perception_report(self, report):
        return self.ensure_perception_worker().submit_report(report).result()


    def get_confirmed_agent_positions(self) -> List[Tuple[int, int]]:
        """Return the latest applied AGV positions in public coordinates.

        Applied positions passed the configured confirmation policy.  Grid
        stability still does not prove completed movement or arrival.  Raise
        if no complete confirmed position set is available.
        """
        with self.read_state():
            expected_ids = set(range(self.grid_config.num_agents))
            if set(self.latest_confirmed_positions) != expected_ids:
                raise RuntimeError("complete confirmed AGV positions are not available")
            return [
                self.latest_confirmed_positions[agent_id]
                for agent_id in range(self.grid_config.num_agents)
            ]

    def get_observable_agent_positions(self) -> List[Tuple[int, int]]:
        """Read the simulator/sensor-side candidate position layer."""
        candidates = self.scene_adapter.observable_positions()
        if candidates is not None:
            return list(candidates)
        base = self.state
        return [base._to_public_xy(position) for position in base.grid.positions_xy]


    def _capture_observation(self) -> ObservationBatch:
        """Capture one raw batch without validating or applying it."""
        return self.scene_adapter.capture_positions()

    def _reconcile_observation(
        self,
        batch: ObservationBatch,
    ) -> Mapping[int, tuple[int, int]]:
        """Structurally validate a batch without changing environment state."""
        return self.state_reconciler.reconcile(
            batch,
            expected_ids=set(range(self.grid_config.num_agents)),
            grid_size=self.public_grid_size,
        )

    def _confirm_observation(
        self,
        batch: ObservationBatch,
        positions: Mapping[int, tuple[int, int]],
    ) -> ConfirmationResult:
        """Evaluate semantic confirmation without changing environment state."""
        return self.confirmation_policy.evaluate(batch, positions)

    def _apply_confirmation(
        self,
        result: ConfirmationResult,
        *, movement_bindings=None, run_worker=None,
    ) -> None:
        """Atomically apply one semantically confirmed AGV position layer."""
        if result.status is not ConfirmationStatus.CONFIRMED:
            raise ValueError("only confirmed positions may be applied")

        base = self.state
        if self._bootstrapping_positions:
            # Bootstrap only: no report evidence or distance before a session starts.
            new_positions = list(base.grid.positions_xy)
            for agent_id, public_position in result.confirmed_positions.items():
                new_positions[agent_id] = base._to_internal_xy(public_position)
            base.replace_agent_positions(new_positions)
            self.latest_confirmed_positions = dict(result.confirmed_positions)
        else:
            if run_worker is None:
                run_worker = self.ensure_perception_worker()
            with self.processing_lock:
                self.require_current_run(run_worker)
                reports = tuple(PerceptionReport(
                    result.batch.source, result.batch.sequence, result.batch.captured_at, fact,
                    movement_bindings.get(fact.agv_id) if movement_bindings else None,
                ) for fact in result.batch.agvs)
                handle = run_worker.submit_position_frame(reports)
            outcomes = handle.result()
            self.require_current_run(run_worker)
            if len(outcomes) != self.grid_config.num_agents or any(not outcome.committed.applied for outcome in outcomes):
                reasons = "; ".join(outcome.committed.reason for outcome in outcomes if not outcome.committed.applied)
                raise ObservationRejectedError("required position frame failed: " + reasons)
        with self.processing_lock:
            if run_worker is not None:
                self.require_current_run(run_worker)
            self.latest_observation_batch = result.batch
            self.latest_confirmation_result = result

    def _synchronize_perception_state(self, *, run_worker=None) -> ObservationBatch:
        """Sample until confirmed, keeping this input bound to its original run."""
        if not self._bootstrapping_positions and run_worker is None:
            run_worker = self.ensure_perception_worker()
        for _ in range(self.confirmation_max_observations):
            with self.processing_lock:
                if run_worker is not None:
                    self.require_current_run(run_worker)
                movement_bindings = self.movement_bindings()
                batch = self._capture_observation()
                positions = self._reconcile_observation(batch)
                confirmation = self._confirm_observation(batch, positions)
                self.latest_confirmation_result = confirmation
            if confirmation.status is ConfirmationStatus.PENDING:
                continue
            self._apply_confirmation(confirmation, movement_bindings=movement_bindings, run_worker=run_worker)
            return batch

        raise ObservationConfirmationExhaustedError(
            "observation was not confirmed within "
            f"{self.confirmation_max_observations} batches"
        )

    def project_solver_observation(self) -> dict:
        """Build all solver views from one current, applied environment state."""
        with self.read_state():
            from .observation import observable_state
            from .planning import planning_snapshot
            base = self.state
            public = observable_state(base)
            padding = self.grid_config.obs_radius or 0
            grid = base.grid.obstacles
            grid = grid[padding:-padding, padding:-padding] if padding else grid
            task = dict(public, env_timeline=base.env_timeline,
                obstacle_grid=grid.copy(), grid_height=grid.shape[0], grid_width=grid.shape[1],
                move_deltas=[list(move) for move in self.grid_config.MOVES],
                agv_task_phase=list(base.agv_task_phase), agv_loaded=list(base.agv_loaded))
            self.events.enrich_task_observation(task)
            previous = self.metrics_hub.get_latest()
            if previous:
                task["prev_metrics"] = deepcopy(previous)
            priors = self.scene_adapter.failure_priors()
            return {
                "job_observation": {"jobs": public["jobs"], "machines": public["machines"],
                                    "env_timeline": base.env_timeline},
                "task_observation": task,
                "agent_observation": base.build_agent_observation(),
                "planning_observation": planning_snapshot(public, task, self.processing_time_config,
                                                          priors, self.material_handling_config or {}),
            }

    @property
    def machine_possible_positions(self):
        return self.grid_config.possible_targets_xy

    @property
    def current_targets(self):
        return self.pogema_env.grid.finishes_xy

    def initialize_machine_env(self):
        grid: Grid = Grid(grid_config=self.grid_config)
        grid.get_obstacles()
        machines = generate_machines(grid.get_obstacles(), self.machine_config)
        if self.machine_config.strategy != "custom":
            # Generated locations index the padded grid; custom locations are already public.
            for machine in machines:
                machine.location = self.state._to_public_xy(machine.location)
        self.grid_config.possible_targets_xy = [m.location for m in machines]
        return machines

    def initialize_pogema_env(self, random_target=False):
        """初始化Pogema环境"""
        # 创建Pogema环境
        self.pogema_env = PogemaLifeLongWithAssign(
            grid_config=self.grid_config,
            random_target=random_target,
            padding_init_request=False,
            material_handling_config=self.material_handling_config,
        )
        self._state = self.pogema_env
        # Both modes use the scene bridge; only animation/history is optional.
        from sky_executor.simulation import PogemaSimulationStepBridge
        bridge = PogemaSimulationStepBridge(self.pogema_env, lambda: self.scene_adapter)
        self.pogema_env = bridge if self.headless else AnimationMonitor(bridge)
        LOGGER.info(
            f"[GridFactoryEnv] Pogema环境初始化成功，智能体数量: {self.grid_config.num_agents}"
        )

    def initialize_job_env(self):
        """
        初始化 Job 层任务系统：
        1. 创建机器和 Job
        2. 调用调度器生成加工计划
        3. 存储初始调度结果
        """
        LOGGER.info("[GridFactoryEnv] 初始化 Job 层任务...")

        # self.job_config = self._create_default_job_config()
        jobs = generate_jobs(self.job_config)

        return jobs

    def set_env_timeline(self, env_timeline: int):
        """设置环境时间线"""
        self.env_timeline = env_timeline

    def show_actions(self, actions):
        from sky_executor.grid_factory.factory.Utils.pic_drawer import pretty_print_step

        pretty_print_step(self.env_timeline, actions)

    def show_jobs(
        self,
    ):
        from sky_executor.grid_factory.factory.Utils.pic_drawer import pretty_print_jobs

        pretty_print_jobs(self.pogema_env.jobs)

    def ensure_controller(self, coordinator, *, decision_policy=None):
        from sky_executor.control import DecisionController
        # Construction can start a Worker; keep this outside the business locks.
        with self._controller_lock:
            if self._controller is None:
                self._controller = DecisionController(
                    self, coordinator, decision_policy=decision_policy,
                    temporary_obstacle_source=self.scene_adapter.source + "-map")
            elif self._controller._coordinator is not coordinator:
                raise RuntimeError("one controller and Coordinator own each session")
            return self._controller

    def synchronous_step(self, coordinator, provided_decision=None, *, evaluate_decision=True, run_worker=None):
        """Keep vendor history and metrics on the common simulation-step path."""
        if run_worker is None:
            self.ensure_controller(coordinator)
            run_worker = self.perception_worker
        with self.simulation_step_lock, self.run_operation(run_worker):
            request = (run_worker, None if provided_decision is None else deepcopy(provided_decision), evaluate_decision)
            a_obs, a_reward, a_term, a_trunc, a_info = self.pogema_env.step(request)
            with self.read_state():
                self.require_current_run(run_worker)
                projected = self.project_solver_observation()
                result = self.pack_output(
                    [projected["job_observation"], {}, {}, {}, {}],
                    [projected["task_observation"], [], [False] * self.grid_config.num_agents,
                     [False] * self.grid_config.num_agents, []],
                    [a_obs, a_reward, a_term, a_trunc, a_info], projected=projected)
                output = self.metrics_hub.on_step_end(*result)
                if output[2]["job_done"]:
                    self._order_admission_closed = True
                return output


    def residual_problem(self):
        from sky_executor.planning import residual_problem
        with self.read_state():
            return residual_problem(self, self.scene_adapter.planning_time())

    def validate_reschedule(self, action):
        from sky_executor.planning import prepare_change
        with self.read_state():
            prepare_change(self, action)

    def apply_reschedule(self, action, new_jobs=()):
        from sky_executor.planning import apply_change
        with self.process_business_chain():
            return apply_change(self, action, new_jobs)

    def release_due_jobs(self, time, *, run_worker=None):
        from sky_executor.planning import release_jobs
        with self.process_business_chain(run_worker=run_worker):
            return release_jobs(self, time)

    def step(self, actions=None):
        """Compatibility entry: external decisions use the same synchronous rounds."""
        coordinator = self._controller._coordinator if self._controller is not None else None
        return self.synchronous_step(coordinator, actions or {}, evaluate_decision=False)

    def reset(self, seed=None):
        LOGGER.info("[GridFactoryEnv] 重置环境")
        self.scene_adapter.stop_inputs()
        self.decision_notifications.close()
        self.stop_perception_worker()
        with self.scene_adapter.fault_injector.input_lock:
            # Port cleanup can join producers; inputs and Worker are already stopped.
            for binding in (self.scene_adapter.machine_binding, self.scene_adapter.agv_binding):
                binding.execution_port.reset()
            episode_seed = int(self.grid_config.seed or 0) if seed is None else int(seed)
            self.configure_simulation_seed(episode_seed)
            if self.scene_adapter.position_source is not None:
                self.scene_adapter.position_source.reset()
            with self.processing_lock:
                return self._reset_after_inputs_stopped(seed)

    def configure_simulation_seed(self, seed):
        """Configure simulated random streams outside the core locks."""
        for binding in (self.scene_adapter.machine_binding, self.scene_adapter.agv_binding):
            if binding.configure_simulation_seed is not None:
                binding.configure_simulation_seed(seed)

    def _reset_after_inputs_stopped(self, seed):
        from sky_executor.decision import DecisionNotifications
        self.decision_notifications = DecisionNotifications()
        self._business_changes.clear()
        self._business_started = False
        self._machines_to_prepare.clear()
        self.execution_failure = None
        self._order_admission_closed = False
        self.job_insertions.reset()
        for runtime in (self.machine_runtime, self.agv_runtime):
            runtime.reset()
        self._controller = None
        self._simulation_snapshot = None
        self._movement_since_tick = {}
        self.last_actions = None

        self.set_env_timeline(0)
        self.metrics_hub.on_episode_start()
        self.state_reconciler.reset()
        self.confirmation_policy.reset()
        self.latest_observation_batch = None
        self.latest_confirmation_result = None
        self.latest_confirmed_positions = {}
        # --- 重置 Pogema 相关 ---
        a_observations, a_infos = self.pogema_env.reset(seed=seed)

        # --- 重置任务相关，使用可能位置 ---
        t_observations, t_infos = self.pogema_env.machine_reset(deepcopy(self.init_machines))

        # --- 重置任务相关，使用任务列表 ---
        j_observations, j_infos = self.pogema_env.job_reset(deepcopy(self.init_jobs))

        reachable = self.scene_adapter.validate_initial_layout()
        from sky_executor.grid_factory.factory.material import initialize_material_stations
        initialize_material_stations(self.state, reachable)
        self.scene_adapter.reset_state()
        cutoff = self.scene_adapter.planning_time()
        self.state.jobs = [job for job in self.state._all_jobs if job.release <= cutoff]
        self.state._future_jobs = [job for job in self.state._all_jobs if job.release > cutoff]
        self.state.hash_operations = self.state.create_hash_operations()
        self.configure_operation_profiles(self.state._all_jobs)
        self.events.reset()

        self._bootstrapping_positions = True
        try:
            self._synchronize_perception_state()
        finally:
            self._bootstrapping_positions = False
        projected = deepcopy(self.project_solver_observation())
        j_observations = projected["job_observation"]
        t_observations = projected["task_observation"]
        a_observations = projected["agent_observation"]

        # --- 打包输出 ---
        obs, rwd, term, trunc, info = self.pack_output(
            [j_observations, j_infos],
            [t_observations, t_infos],
            [a_observations, a_infos],
        )

        return obs, info

    def render(self):
        """渲染环境"""
        self.pogema_env.render()

    def close(self):
        self.decision_notifications.close()
        self.scene_adapter.stop_inputs()
        self.stop_perception_worker()
        with self.scene_adapter.fault_injector.input_lock:
            for runtime in (self.machine_runtime, self.agv_runtime):
                runtime.close()
            for binding in (self.scene_adapter.machine_binding, self.scene_adapter.agv_binding):
                binding.execution_port.close()
        self.scene_adapter.close()
        self.pogema_env.close()

    # ---------- 获取器方法 ----------
    def get_jobs(self) -> List:
        """获取作业列表"""
        return self.pogema_env.jobs

    def job_all_done(self):
        return self.state.job_all_done() and not any(
            record["phase"] in {"queued", "replanning"} for record in self.job_insertions.records.values())

    def get_machines(self) -> List:
        """获取机器列表"""
        return self.pogema_env.machines

    def get_agents(self) -> List:
        """获取AGV列表"""
        with self.read_state():
            return self.agents

    def get_agent_positions(self) -> List[Tuple[int, int]]:
        """获取智能体位置"""
        with self.read_state():
            return self.pogema_env.grid.get_agents_xy()

    def get_agent_targets(self) -> List[Tuple[int, int]]:
        """获取智能体目标"""
        return self.pogema_env.grid.finishes_xy

    def unpack_input(self, actions):
        """将输入的 actions 拆分为机器与智能体两部分"""
        # 假设 self.input_actions 是外部传入的总动作字典
        job_actions = actions.get("job_actions", {})
        task_actions = actions.get("assign_actions", {})
        agent_actions = actions.get("agent_actions", {})
        return (
            job_actions,
            task_actions,
            agent_actions,
        )

    def pack_output(self, job_info, task_info, agent_info, *, projected=None):
        """动态合并 job 和 agent 输出"""

        def unpack(info):
            """支持 (obs, reward, term, trunc, info) 或 (obs, info)"""
            if len(info) == 5:
                obs, reward, term, trunc, inf = info
            elif len(info) == 2:
                obs, inf = info
                reward, term, trunc = {}, {}, {}
            else:
                raise ValueError(f"Unexpected tuple length: {len(info)}")
            return obs, reward, term, trunc, inf

        j_obs, j_reward, _j_term, j_trunc, j_info = unpack(job_info)
        t_obs, t_reward, t_term, t_trunc, t_info = unpack(task_info)
        a_obs, a_reward, a_term, a_trunc, a_info = unpack(agent_info)

        # job_step runs before machine processing. Completion must be read
        # from the same final state as the returned observations.
        job_done = self.job_all_done()

        observations = deepcopy(projected) if projected is not None else self.project_solver_observation()
        t_obs = observations["task_observation"]

        # 将上一步 Metrics 注入 task_observation，供 FeatureExtractor 使用
        prev_metrics = self.metrics_hub.get_latest()
        if prev_metrics and isinstance(t_obs, dict):
            t_obs["prev_metrics"] = deepcopy(prev_metrics)


        rewards = {
            "job_reward": j_reward,
            "task_reward": t_reward,
            "agent_reward": a_reward,
        }
        terminations = {
            "job_done": job_done,
            "task_done": t_term,
            "agent_done": a_term,
        }
        truncations = {
            "job_truncated": j_trunc,
            "task_truncated": t_trunc,
            "agent_truncated": a_trunc,
        }
        infos = {
            "job_info": j_info,
            "task_info": t_info,
            "agent_info": a_info,
        }
        infos["events"] = self.events.current_events()
        infos["event_metrics"] = self.events.get_metrics()
        infos.update(self.events.get_epochs())
        if self.latest_observation_batch is not None:
            infos["perception"] = {
                "source": self.latest_observation_batch.source,
                "sequence": self.latest_observation_batch.sequence,
                "captured_at": self.latest_observation_batch.captured_at,
                "validation_level": "structural",
                "confirmation_policy": self.confirmation_policy.name,
                "confirmation_status": (
                    self.latest_confirmation_result.status.value
                    if self.latest_confirmation_result is not None
                    else None
                ),
                "consecutive_samples": (
                    self.latest_confirmation_result.consecutive_samples
                    if self.latest_confirmation_result is not None
                    else None
                ),
                "applied": True,
            }

        return observations, rewards, terminations, truncations, infos
