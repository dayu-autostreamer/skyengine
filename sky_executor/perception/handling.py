"""Apply queued reports to core state, independently of queue scheduling."""
from __future__ import annotations

from sky_executor.execution import ExecutionStatus

from collections.abc import Iterable, Set
from copy import deepcopy
from typing import TYPE_CHECKING

from sky_executor.execution import AgvExecutionUpdate, MachineExecutionUpdate, ExecutionUpdateResult
from sky_executor.perception.commits import FactCommitter
from sky_executor.perception.contracts import (
    AgvAvailabilityObservation, AgvObservation, MachineAvailabilityObservation,
    JobInsertionRequest, JobPlanningUpdate, RescheduleRequest, JobReleaseCheck,
    FactChangeKind, PerceptionReport, PerceptionSnapshot, ReportOutcome, ReportStreamKey,
    TemporaryObstacleObservation, report_stream_key,
)
from sky_executor.perception.reports import ReportProcessor

if TYPE_CHECKING:
    from sky_executor.grid_factory.factory.grid_factory_env import GridFactoryEnv


def report_diagnostic_key(
    report: PerceptionReport,
    agv_ids: Set[int],
    machine_ids: Set[int],
    grid_size: tuple[int, int],
) -> ReportStreamKey | None:
    """Identify a known fact stream, including rejected but identifiable input."""
    key = report_stream_key(report)
    if key is None:
        return None
    fact = report.fact
    if isinstance(fact, (AgvObservation, AgvAvailabilityObservation)):
        device_id, known_ids = fact.agv_id, agv_ids
    elif isinstance(fact, MachineAvailabilityObservation):
        device_id, known_ids = fact.machine_id, machine_ids
    elif isinstance(fact, TemporaryObstacleObservation):
        cell = fact.grid_cell
        width, height = grid_size
        if not (0 <= cell[0] < width and 0 <= cell[1] < height):
            return None
        return key
    else:
        return None
    if device_id not in known_ids:
        return None
    return key


def build_perception_snapshot(
    env: GridFactoryEnv,
    processor: ReportProcessor,
    committer: FactCommitter,
    recent_outcomes: Iterable[ReportOutcome],
) -> PerceptionSnapshot:
    """Copy views and evidence; the owner serializes access to report records."""
    with env.read_state():
        return deepcopy(PerceptionSnapshot(
            observation=env.project_solver_observation(),
            committed_reports=committer.committed_reports(),
            confirmation_states=processor.confirmation_states(),
            recent_outcomes=tuple(recent_outcomes),
            execution=env.agv_runtime.diagnostics(env.execution_failure),
            machine_execution=env.machine_runtime.diagnostics(env.execution_failure),
            job_insertions=env.job_insertions.snapshot(),
            insertion_metrics=dict(env.job_insertions.metrics),
            decision_sequence=env.decision_notifications.sequence,
        ))


class ReportHandler:
    """Own fact processing in the consumer; execution uses request correlation."""
    def __init__(self, env, *, required_position_samples=None,
                 temporary_obstacle_source=None, on_fact_committed, check_position_reports):
        base = env.state
        expected_agv_ids = frozenset(range(base.grid_config.num_agents))
        if base.grid is None or set(env.latest_confirmed_positions) != expected_agv_ids:
            raise ValueError("environment must complete reset before creating a worker")
        self._env = env
        self._agv_ids = expected_agv_ids
        self._machine_ids = frozenset(machine.id for machine in base.machines)
        self.processor = ReportProcessor(
            expected_agv_ids=self._agv_ids,
            expected_machine_ids=self._machine_ids,
            grid_size=env.public_grid_size,
            required_position_samples=required_position_samples,
            temporary_obstacle_source=temporary_obstacle_source,
        )
        self.committer = FactCommitter(env)
        self.recent_outcomes: dict[ReportStreamKey, ReportOutcome] = {}
        self._on_fact_committed = on_fact_committed
        self._check_position_reports = check_position_reports

    def handle_report(self, report: PerceptionReport) -> ReportOutcome | ExecutionUpdateResult:
        # This consumer owns confirmation records and processes queued snapshots
        # only after this report's commit and settlement have completed.
        if isinstance(report.fact, AgvExecutionUpdate):
            return self.apply_execution_report(report)
        if isinstance(report.fact, MachineExecutionUpdate):
            return self.apply_execution_report(report)
        if isinstance(report.fact, RescheduleRequest):
            return self._env.apply_reschedule(report.fact.action)
        if isinstance(report.fact, JobReleaseCheck):
            from sky_executor.planning import release_jobs
            return release_jobs(self._env, report.fact.time)
        if isinstance(report.fact, JobInsertionRequest):
            result = self._env.job_insertions.receive(report)
            if result.applied:
                self._env.record_business_change("job_insertion", report.fact.request_id)
            return result
        if isinstance(report.fact, JobPlanningUpdate):
            result = self._env.job_insertions.apply(report)
            if result.applied:
                self._env.record_business_change("job_planning", report.fact.request_id)
            return result
        report_result = self.processor.process(report)
        with self._env.state_lock:
            if isinstance(report_result.accepted_fact, AgvObservation):
                self._check_position_reports((report,))
            loaded_before = tuple(self._env.state.agv_loaded)
            commit_result = self.committer.commit(report_result)
            self._record_position_commits((commit_result,), loaded_before)
            key = self._diagnostic_key(report)
            if key is not None:
                # If settlement raises, retain the accepted/applied evidence
                # without claiming that settlement completed.
                self.recent_outcomes[key] = ReportOutcome(report_result, commit_result)
            self._on_fact_committed(commit_result)
            settlement_result = self._env.business_settler.settle_after_fact_commit(commit_result)
            self._env.register_execution_intents(settlement_result.execution_intents)
            self._record_fact_changes(commit_result)
            report_outcome = ReportOutcome(report_result, commit_result, settlement_result)
            if key is not None:
                self.recent_outcomes[key] = report_outcome
            return report_outcome

    def apply_execution_report(self, report):
        """Adopt request evidence, settle its business, then register follow-up actions."""
        env = self._env
        execution_update = report.fact
        is_agv = isinstance(execution_update, AgvExecutionUpdate)
        runtime = env.agv_runtime if is_agv else env.machine_runtime
        with env.state_lock:
            update_result, execution_record = runtime.apply_execution_report(report)
            if not update_result.applied:
                return update_result
            if is_agv:
                task = env.state.agv_current_task[execution_record.request.agv_ids[0]]
                source_machine = (env.state.hash_machines.get(task.source)
                                  if task is not None and execution_record.request.kind == "pickup" else None)
                if execution_record.request.kind == "move" and execution_update.status is ExecutionStatus.COMPLETED:
                    env.scene_adapter.record_movement_result(execution_record.request, execution_update)
                business_settled, execution_intents = env.business_settler.apply_agv_execution(execution_record, execution_update)
                machine_ids = ()
                if business_settled and execution_record.request.kind == "dropoff" and task.kind == "operation":
                    machine_ids = (env.state.hash_machines[task.destination].id,)
                elif business_settled and source_machine is not None:
                    machine_ids = (source_machine.id,)
                freed_buffer_ids = (source_machine.id,) if business_settled and source_machine is not None else ()
            else:
                processing_record = (execution_record if execution_record.request.kind == "start" else
                            runtime.execution_records[execution_record.request.target_request_id])
                business_settled, machine_ids = env.business_settler.apply_machine_execution(
                    execution_record, execution_update, processing_record,
                    env.scene_adapter.machine_diagnostics(execution_update.request_id),
                    refresh_finished_goods=env.scene_adapter.immediate_material_settlement)
                execution_intents = ()
                freed_buffer_ids = (machine_ids if execution_record.request.kind == "start"
                                    and execution_update.status is ExecutionStatus.RUNNING else ())
            if business_settled:
                runtime.mark_settled(execution_record)
            elif is_agv and execution_update.status is ExecutionStatus.DEFERRED:
                runtime.release_deferred_handling(execution_record)
            env.machines_ready_after_settlement(machine_ids)
            env.settle_material_changes(freed_buffer_ids)
            env.register_execution_intents(execution_intents)
            env.record_business_change("execution", (execution_update.request_id, execution_update.status.value))
            return ExecutionUpdateResult(True, "execution completed and business settled" if business_settled else update_result.reason, business_settled)

    def _record_fact_changes(self, commit_result):
        for event in commit_result.events:
            self._env.record_business_change(event.kind.value, event.report.fact)
            if isinstance(event.report.fact, MachineAvailabilityObservation) and event.after == "OK":
                self._env.machines_ready_after_settlement((event.report.fact.machine_id,))
                self._env.settle_material_changes((event.report.fact.machine_id,))

    def handle_position_frame(self, reports):
        report_results = tuple(self.processor.process(report) for report in reports)
        with self._env.state_lock:
            if all(isinstance(result.accepted_fact, AgvObservation) for result in report_results):
                self._check_position_reports(reports)
            loaded_before = tuple(self._env.state.agv_loaded)
            commit_results = self.committer.commit_position_frame(report_results)
            self._record_position_commits(commit_results, loaded_before)
            report_outcomes = [ReportOutcome(report_result, commit_result)
                               for report_result, commit_result in zip(report_results, commit_results)]
            for report_outcome in report_outcomes:
                key = self._diagnostic_key(report_outcome.processed.report)
                if key is not None:
                    self.recent_outcomes[key] = report_outcome
            # Rejected frames have no business changes to order. Valid frames
            # settle in AGV order after all positions have been committed.
            settlement_order = range(len(report_outcomes))
            if all(commit_result.applied for commit_result in commit_results):
                settlement_order = sorted(settlement_order, key=lambda i: reports[i].fact.agv_id)

            for index in settlement_order:
                self._on_fact_committed(commit_results[index])
                settlement_result = self._env.business_settler.settle_after_fact_commit(commit_results[index])
                self._env.register_execution_intents(settlement_result.execution_intents)
                self._record_fact_changes(commit_results[index])
                report_outcome = ReportOutcome(report_results[index], commit_results[index], settlement_result)
                report_outcomes[index] = report_outcome
                key = self._diagnostic_key(reports[index])
                if key is not None:
                    self.recent_outcomes[key] = report_outcome
            return tuple(report_outcomes)

    def _record_position_commits(self, commit_results, loaded_before):
        position_reports = []
        for commit_result in commit_results:
            if not commit_result.applied or not isinstance(commit_result.report.fact, AgvObservation):
                continue
            position_reports.append(commit_result.report)
            for event in commit_result.events:
                if event.kind is FactChangeKind.POSITION:
                    agv_id = event.report.fact.agv_id
                    self._env.business_statistics.record_position_changes(
                        (event.before,), (event.after,), agent_ids=(agv_id,))
                    self._env._movement_since_tick.setdefault(agv_id, loaded_before[agv_id])
        settled_ids = self._env.agv_runtime.settle_confirmed_movements(position_reports)
        self._env.scene_adapter.release_movement_positions(settled_ids)

    def _diagnostic_key(
        self, report: PerceptionReport
    ) -> ReportStreamKey | None:
        return report_diagnostic_key(
            report, self._agv_ids, self._machine_ids, self._env.public_grid_size
        )

    def snapshot(self) -> PerceptionSnapshot:
        return build_perception_snapshot(
            self._env, self.processor, self.committer,
            self.recent_outcomes.values(),
        )
