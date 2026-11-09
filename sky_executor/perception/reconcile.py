"""Minimal structural reconciliation for canonical AGV observations."""

from __future__ import annotations

from collections.abc import Mapping
from sky_executor.perception.validation import is_finite_number, grid_cell_rejection, confidence_rejection

from sky_executor.perception.contracts import (
    GridCell,
    ObservationBatch,
    ObservationRejectedError,
)


class StrictStateReconciler:
    """Accept only complete, ordered and internally consistent batches.

    Acceptance here is structural only.  It does not mean that a physical AGV
    is stable or has completed a commanded movement.  Smoothing, time windows,
    confidence thresholds, occlusion handling and recovery remain outside this
    stage.
    """

    def __init__(self) -> None:
        self._last_sequence: int | None = None

    def reset(self) -> None:
        self._last_sequence = None

    def reconcile(
        self,
        batch: ObservationBatch,
        *,
        expected_ids: set[int],
        grid_size: tuple[int, int],
    ) -> Mapping[int, GridCell]:
        if not isinstance(batch.source, str) or not batch.source.strip():
            self._reject("source must be a non-empty string")
        if type(batch.sequence) is not int:
            self._reject("sequence must be an integer")
        if self._last_sequence is not None and batch.sequence <= self._last_sequence:
            self._reject(
                f"sequence must increase: received {batch.sequence} after {self._last_sequence}"
            )
        if not is_finite_number(batch.captured_at):
            self._reject("captured_at must be a finite number")

        positions: dict[int, GridCell] = {}
        occupied: set[GridCell] = set()
        for observation in batch.agvs:
            agent_id = observation.agv_id
            if type(agent_id) is not int:
                self._reject("agv_id must be an integer")
            if agent_id in positions:
                self._reject(f"duplicate AGV id: {agent_id}")

            cell = observation.grid_cell
            rejection = grid_cell_rejection(cell, grid_size)
            if rejection is not None:
                self._reject(f"AGV {agent_id} {rejection}")
            if cell in occupied:
                self._reject(f"multiple AGVs occupy grid_cell {cell}")
            rejection = confidence_rejection(observation.confidence)
            if rejection is not None:
                self._reject(f"AGV {agent_id} {rejection}")

            positions[agent_id] = cell
            occupied.add(cell)

        observed_ids = set(positions)
        if observed_ids != expected_ids:
            missing = sorted(expected_ids - observed_ids)
            unexpected = sorted(observed_ids - expected_ids)
            self._reject(
                f"AGV id set mismatch: missing={missing}, unexpected={unexpected}"
            )

        self._last_sequence = batch.sequence
        return positions

    @staticmethod
    def _reject(reason: str) -> None:
        raise ObservationRejectedError(reason)
