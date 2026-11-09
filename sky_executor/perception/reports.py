"""Validate and confirm individual reports without changing environment facts."""

from __future__ import annotations

from collections.abc import Set
from sky_executor.perception.validation import is_finite_number, grid_cell_rejection, confidence_rejection

from sky_executor.perception.contracts import (
    AgvAvailabilityObservation,
    AgvObservation,
    MachineAvailabilityObservation,
    PerceptionReport,
    PositionConfirmationState,
    ReportResult,
    ReportStatus,
    ReportStreamKey,
    TemporaryObstacleObservation,
    report_stream_key,
)


class ReportProcessor:
    """Return accepted, rejected or pending input; do not apply it.

    The caller supplies known devices and public grid bounds. Each source,
    fact type and target has its own sequence history. Confirmation counts matching
    valid samples per (source, AGV). It does not prove physical stability,
    collision-free occupancy or completion of a command.
    """

    def __init__(
        self,
        *,
        expected_agv_ids: Set[int],
        expected_machine_ids: Set[int],
        grid_size: tuple[int, int],
        required_position_samples: int | None = None,
        temporary_obstacle_source: str | None = None,
    ) -> None:
        self._expected_agv_ids = frozenset(expected_agv_ids)
        self._expected_machine_ids = frozenset(expected_machine_ids)
        if required_position_samples is not None and (
            type(required_position_samples) is not int
            or required_position_samples < 2
        ):
            raise ValueError("required_position_samples must be an integer >= 2")
        if temporary_obstacle_source is not None and (
            not isinstance(temporary_obstacle_source, str)
            or not temporary_obstacle_source.strip()
        ):
            raise ValueError("temporary_obstacle_source must be a non-empty string")
        self._grid_size = grid_size
        self._required_position_samples = required_position_samples
        self._temporary_obstacle_source = temporary_obstacle_source
        self._last_processed_sequences: dict[ReportStreamKey, int] = {}
        self._position_states: dict[tuple[str, int], PositionConfirmationState] = {}

    def reset(self) -> None:
        """Start a new input session, clearing order and confirmation history."""
        self._last_processed_sequences.clear()
        self._position_states.clear()

    def confirmation_states(self) -> tuple[PositionConfirmationState, ...]:
        """Export immutable confirmation evidence in first-seen stream order."""
        return tuple(self._position_states.values())

    def process(self, report: PerceptionReport) -> ReportResult:
        """Process just this input, without sampling or advancing any clock."""
        reason = self._validate(report)
        if reason is None:
            reason = self._check_sequence(report)
        if reason is not None:
            return ReportResult(report, ReportStatus.REJECTED, reason)

        # A pending valid input also consumes its sequence. Replaying it cannot
        # supply another confirmation sample.
        key = report_stream_key(report)
        self._last_processed_sequences[key] = report.sequence
        if isinstance(report.fact, AgvObservation):
            return self._confirm_position(report, report.fact)
        if isinstance(report.fact, TemporaryObstacleObservation):
            reason = "temporary obstacle accepted immediately"
        else:
            reason = "resource status accepted immediately"
        return ReportResult(
            report, ReportStatus.ACCEPTED, reason
        )

    def _validate(self, report: PerceptionReport) -> str | None:
        if not isinstance(report.source, str) or not report.source.strip():
            return "source must be a non-empty string"
        if type(report.sequence) is not int:
            return "sequence must be an integer"
        if not is_finite_number(report.captured_at):
            return "captured_at must be a finite number"

        if report.movement_request_id is not None and (
            not isinstance(report.movement_request_id, str) or not report.movement_request_id
        ):
            return "movement_request_id must be a non-empty string or None"

        fact = report.fact
        if isinstance(fact, (AgvObservation, AgvAvailabilityObservation)):
            if type(fact.agv_id) is not int:
                return "agv_id must be an integer"
            if fact.agv_id not in self._expected_agv_ids:
                return f"unknown AGV id: {fact.agv_id}"
        elif isinstance(fact, MachineAvailabilityObservation):
            if type(fact.machine_id) is not int:
                return "machine_id must be an integer"
            if fact.machine_id not in self._expected_machine_ids:
                return f"unknown machine id: {fact.machine_id}"
        elif isinstance(fact, TemporaryObstacleObservation):
            if self._temporary_obstacle_source is None:
                return "temporary obstacle reports are disabled"
            if report.source != self._temporary_obstacle_source:
                return (
                    "temporary obstacle source must be "
                    f"{self._temporary_obstacle_source!r}"
                )
        else:
            return (
                "fact must be one AGV position, AGV status, machine status "
                "or temporary obstacle"
            )

        if isinstance(fact, (AgvObservation, TemporaryObstacleObservation)):
            rejection = grid_cell_rejection(fact.grid_cell, self._grid_size)
            if rejection is not None:
                return rejection
            if isinstance(fact, AgvObservation):
                rejection = confidence_rejection(fact.confidence)
                if rejection is not None:
                    return rejection
            elif not isinstance(fact.status, str) or fact.status not in {
                "BLOCKED", "CLEAR"
            }:
                return "temporary obstacle status must be BLOCKED or CLEAR"
        else:
            allowed = {"OK", "DOWN"}
            if isinstance(fact, MachineAvailabilityObservation):
                allowed.add("MAINTENANCE")
            if not isinstance(fact.status, str) or fact.status not in allowed:
                return f"resource status must be one of {sorted(allowed)}"
            if fact.reason is not None and not isinstance(fact.reason, str):
                return "reason must be a string or None"
            if fact.repair_remaining is not None and (
                type(fact.repair_remaining) is not int or fact.repair_remaining < 0
            ):
                return "repair_remaining must be a non-negative integer or None"
        return None

    def _check_sequence(self, report: PerceptionReport) -> str | None:
        key = report_stream_key(report)
        previous = self._last_processed_sequences.get(key)
        if previous is not None and report.sequence <= previous:
            return (
                f"sequence must increase for {key!r}: "
                f"received {report.sequence} after {previous}"
            )
        return None

    def _confirm_position(
        self, report: PerceptionReport, fact: AgvObservation
    ) -> ReportResult:
        required = self._required_position_samples
        key = (report.source, fact.agv_id)
        if required is None:
            self._accept_position(key, report)
            return ReportResult(
                report, ReportStatus.ACCEPTED, "position accepted immediately"
            )

        state = self._position_states.get(key)
        accepted = state.accepted_report if state is not None else None
        if accepted is not None and accepted.fact.grid_cell == fact.grid_cell:
            self._accept_position(key, report)
            return ReportResult(
                report, ReportStatus.ACCEPTED, "position matches last accepted position"
            )

        candidate = state.candidate_report if state is not None else None
        count = 1
        if candidate is not None and candidate.fact.grid_cell == fact.grid_cell:
            count = state.candidate_samples + 1
        if count < required:
            self._position_states[key] = PositionConfirmationState(
                report.source, fact.agv_id, accepted, report, count, required
            )
            return ReportResult(
                report,
                ReportStatus.PENDING,
                f"position needs matching valid samples: {count}/{required}",
            )
        self._accept_position(key, report)
        return ReportResult(
            report,
            ReportStatus.ACCEPTED,
            f"position accepted after {required} matching valid samples",
        )

    def _accept_position(
        self, key: tuple[str, int], report: PerceptionReport
    ) -> None:
        self._position_states[key] = PositionConfirmationState(
            report.source, key[1], report, None, 0, self._required_position_samples
        )
