"""Commit accepted facts against current occupancy and report their changes."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sky_executor.perception.contracts import (
    AgvAvailabilityObservation, AgvObservation, CommitResult, FactChangeEvent,
    FactChangeKind, GridCell, MachineAvailabilityObservation, PerceptionFact,
    PerceptionReport, ReportResult, ReportStreamKey, TemporaryObstacleObservation,
    report_stream_key,
)

if TYPE_CHECKING:
    from sky_executor.grid_factory.factory.grid_factory_env import GridFactoryEnv


class FactCommitter:
    """Trust report validation; check live constraints and record successful writes.

    The caller holds state_lock through commit and business settlement. The
    committed sequence is independent of the processor's consumed sequence:
    acceptance and confirmation can succeed while current occupancy rejects it.
    """
    def __init__(self, env: GridFactoryEnv) -> None:
        self._env = env
        self._last_committed_sequences: dict[ReportStreamKey, int] = {}
        self._latest_reports: dict[tuple[type, int | GridCell], PerceptionReport] = {}

    def reset(self) -> None:
        self._last_committed_sequences.clear()
        self._latest_reports.clear()

    def latest_report(self, fact_type: type[PerceptionFact], target: int | GridCell) -> PerceptionReport | None:
        return self._latest_reports.get((fact_type, target))

    def committed_reports(self) -> tuple[PerceptionReport, ...]:
        return tuple(self._latest_reports.values())

    def commit(self, report_result: ReportResult) -> CommitResult:
        report = report_result.report
        fact = report_result.accepted_fact
        if fact is None:
            return CommitResult(report, False, f"report is {report_result.status.value}: {report_result.reason}")
        previous = self._last_committed_sequences.get(report_stream_key(report))
        if previous is not None and report.sequence <= previous:
            return CommitResult(report, False, "sequence already committed")

        base = self._env.state
        if isinstance(fact, AgvObservation):
            rejection = self._position_rejection(base, fact)
            if rejection is not None:
                return CommitResult(report, False, rejection)
            before = tuple(base._to_public_xy(base.grid.positions_xy[fact.agv_id]))
            self._apply_position(base, fact)
            return self._record_commit(report, fact.agv_id, FactChangeKind.POSITION, before, fact.grid_cell)
        if isinstance(fact, AgvAvailabilityObservation):
            before = base.agv_status[fact.agv_id]
            if before != "DOWN" and fact.status == "DOWN":
                base.agv_down_elapsed[fact.agv_id] = 0
            base.agv_status[fact.agv_id] = fact.status
            if fact.reason is not None:
                base.agv_down_reason[fact.agv_id] = fact.reason
            if fact.repair_remaining is not None:
                base.agv_repair_remaining[fact.agv_id] = fact.repair_remaining
            return self._record_commit(report, fact.agv_id, FactChangeKind.AVAILABILITY, before, fact.status)
        if isinstance(fact, MachineAvailabilityObservation):
            machine = next(machine for machine in base.machines if machine.id == fact.machine_id)
            before = machine.status
            if before != "DOWN" and fact.status == "DOWN":
                machine.down_elapsed = 0
            machine.status = fact.status
            if fact.reason is not None:
                machine.down_reason = fact.reason
            if fact.repair_remaining is not None:
                machine.repair_remaining = fact.repair_remaining
            return self._record_commit(report, fact.machine_id, FactChangeKind.AVAILABILITY, before, fact.status)

        rejection = self._temporary_obstacle_rejection(base, fact)
        if rejection is not None:
            return CommitResult(report, False, rejection)
        before, after = self._apply_temporary_obstacle(base, fact)
        return self._record_commit(report, fact.grid_cell, FactChangeKind.TEMPORARY_OBSTACLE, before, after)

    def _record_commit(self, report, target, change_kind, before, after):
        events = () if before == after else (FactChangeEvent(change_kind, report, before, after),)
        self._latest_reports[(type(report.fact), target)] = report
        self._last_committed_sequences[report_stream_key(report)] = report.sequence
        return CommitResult(report, True, "fact applied", events)

    def commit_position_frame(self, report_results) -> tuple[CommitResult, ...]:
        """Validate final batch occupancy, commit all positions, then save receipts."""
        report_results = tuple(report_results)
        base = self._env.state
        rejection = self._position_frame_rejection(base, report_results)
        if rejection is not None:
            return tuple(CommitResult(item.report, False, rejection) for item in report_results)

        old_positions = list(base.grid.positions_xy)
        old_occupancy = base.grid.positions.copy()
        new_positions = list(old_positions)
        for report_result in report_results:
            fact = report_result.accepted_fact
            new_positions[fact.agv_id] = base._to_internal_xy(fact.grid_cell)
        try:
            base.replace_agent_positions(new_positions)
        except BaseException:
            base.grid.positions_xy[:] = old_positions
            base.grid.positions[:] = old_occupancy
            raise

        commit_results = []
        for report_result in report_results:
            fact = report_result.accepted_fact
            before = tuple(base._to_public_xy(old_positions[fact.agv_id]))
            self._env.latest_confirmed_positions[fact.agv_id] = fact.grid_cell
            commit_results.append(self._record_commit(
                report_result.report, fact.agv_id, FactChangeKind.POSITION, before, fact.grid_cell))
        return tuple(commit_results)

    def _position_frame_rejection(self, base, report_results):
        positions = {}
        for report_result in report_results:
            fact = report_result.accepted_fact
            if not isinstance(fact, AgvObservation):
                return "position frame contains unaccepted or non-position input"
            if fact.agv_id in positions:
                return "position frame must contain every known AGV exactly once"
            positions[fact.agv_id] = fact.grid_cell
            previous = self._last_committed_sequences.get(report_stream_key(report_result.report))
            if previous is not None and report_result.report.sequence <= previous:
                return "position frame contains an already committed sequence"
            rejection = self._position_rejection(base, fact, check_occupancy=False)
            if rejection is not None:
                return rejection
        if set(positions) != set(range(base.grid_config.num_agents)):
            return "position frame must contain every known AGV exactly once"
        if len(set(positions.values())) != len(positions):
            return "position frame has duplicate final positions"
        return None

    def _position_rejection(self, base, fact: AgvObservation, *, check_occupancy=True):
        internal = base._to_internal_xy(fact.grid_cell)
        if base.grid.obstacles[internal] != base.grid.config.FREE:
            return f"grid_cell {fact.grid_cell} is an obstacle"
        if check_occupancy:
            for agent_id, position in enumerate(base.grid.positions_xy):
                if agent_id != fact.agv_id and base.grid.is_active[agent_id] and tuple(position) == internal:
                    return f"grid_cell {fact.grid_cell} is occupied by AGV {agent_id}"
        return None

    def _apply_position(self, base, fact: AgvObservation) -> None:
        grid = base.grid
        old_positions = list(grid.positions_xy)
        old_occupancy = grid.positions.copy()
        new_positions = list(old_positions)
        new_positions[fact.agv_id] = base._to_internal_xy(fact.grid_cell)
        try:
            base.replace_agent_positions(new_positions)
        except Exception:
            grid.positions_xy[:] = old_positions
            grid.positions[:] = old_occupancy
            raise
        self._env.latest_confirmed_positions[fact.agv_id] = fact.grid_cell

    def _temporary_obstacle_rejection(self, base, fact: TemporaryObstacleObservation):
        cell = fact.grid_cell
        managed = base.reported_temporary_obstacles
        internal = base._to_internal_xy(cell)
        blocked = base.grid.obstacles[internal] != base.grid.config.FREE
        if fact.status == "CLEAR":
            if cell not in managed and blocked:
                return f"grid_cell {cell} is not a report-managed temporary obstacle"
            return None
        if cell in managed:
            return None
        if blocked:
            return f"grid_cell {cell} is already an obstacle"
        for agent_id, position in enumerate(base.grid.positions_xy):
            if base.grid.is_active[agent_id] and tuple(base._to_public_xy(position)) == cell:
                return f"grid_cell {cell} is occupied by AGV {agent_id}"
        machine = next((item for item in base.machines if tuple(item.location) == cell), None)
        if machine is not None:
            return f"grid_cell {cell} is occupied by machine {machine.id}"
        return None

    @staticmethod
    def _apply_temporary_obstacle(base, fact: TemporaryObstacleObservation) -> tuple[str, str]:
        cell = fact.grid_cell
        managed = base.reported_temporary_obstacles
        before = "BLOCKED" if cell in managed else "CLEAR"
        after = fact.status
        if before != after:
            internal = base._to_internal_xy(cell)
            if after == "BLOCKED":
                base.grid.obstacles[internal] = base.grid.config.OBSTACLE
                managed.add(cell)
            else:
                base.grid.obstacles[internal] = base.grid.config.FREE
                managed.remove(cell)
            base.map_epoch += 1
        return before, after
