"""Semantic confirmation policies for structurally valid observations."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from sky_executor.perception.contracts import (
    ConfirmationResult,
    ConfirmationStatus,
    GridCell,
    ObservationBatch,
)


def _position_snapshot(
    positions: Mapping[int, GridCell],
) -> Mapping[int, GridCell]:
    """Copy positions so a confirmation result cannot change with its caller."""
    return MappingProxyType(dict(positions))


class ImmediateConfirmationPolicy:
    """Immediately confirm every structurally valid complete batch."""

    name = "immediate"

    def reset(self) -> None:
        return None

    def evaluate(
        self,
        batch: ObservationBatch,
        positions: Mapping[int, GridCell],
    ) -> ConfirmationResult:
        return ConfirmationResult(
            status=ConfirmationStatus.CONFIRMED,
            batch=batch,
            confirmed_positions=_position_snapshot(positions),
            consecutive_samples=1,
        )


class ConsecutiveGridConfirmationPolicy:
    """Confirm an atomic grid snapshot after N identical observations."""

    name = "consecutive_grid"

    def __init__(self, required_samples: int) -> None:
        if type(required_samples) is not int or required_samples < 2:
            raise ValueError(
                "required_samples must be an integer greater than or equal to 2"
            )
        self.required_samples = required_samples
        self._candidate_signature: tuple[
            str,
            tuple[tuple[int, GridCell], ...],
        ] | None = None
        self._consecutive_samples = 0

    def reset(self) -> None:
        self._candidate_signature = None
        self._consecutive_samples = 0

    def evaluate(
        self,
        batch: ObservationBatch,
        positions: Mapping[int, GridCell],
    ) -> ConfirmationResult:
        normalized_positions = dict(positions)
        signature = (
            batch.source,
            tuple(sorted(normalized_positions.items())),
        )

        if signature == self._candidate_signature:
            self._consecutive_samples = min(
                self.required_samples,
                self._consecutive_samples + 1,
            )
        else:
            self._candidate_signature = signature
            self._consecutive_samples = 1

        if self._consecutive_samples < self.required_samples:
            return ConfirmationResult(
                status=ConfirmationStatus.PENDING,
                batch=batch,
                confirmed_positions=None,
                consecutive_samples=self._consecutive_samples,
            )

        return ConfirmationResult(
            status=ConfirmationStatus.CONFIRMED,
            batch=batch,
            confirmed_positions=_position_snapshot(normalized_positions),
            consecutive_samples=self._consecutive_samples,
        )


def create_confirmation_policy(
    config: dict | None,
) -> tuple[ImmediateConfirmationPolicy | ConsecutiveGridConfirmationPolicy, int]:
    """Create one confirmation policy and its per-boundary sample limit."""
    config = config or {}
    if not isinstance(config, dict):
        raise ValueError("perception must be an object")

    confirmation = config.get("confirmation")
    if confirmation is None:
        return ImmediateConfirmationPolicy(), 1
    if not isinstance(confirmation, dict):
        raise ValueError("perception.confirmation must be an object")

    policy_name = confirmation.get("policy", "immediate")
    if policy_name == "immediate":
        stability_fields = {"required_samples", "max_observations"}
        supplied_fields = stability_fields.intersection(confirmation)
        if supplied_fields:
            fields = ", ".join(sorted(supplied_fields))
            raise ValueError(
                f"perception.confirmation fields {fields} require "
                "policy='consecutive_grid'"
            )
        return ImmediateConfirmationPolicy(), 1

    if policy_name == "consecutive_grid":
        if "required_samples" not in confirmation:
            raise ValueError(
                "perception.confirmation.required_samples is required for "
                "policy='consecutive_grid'"
            )
        if "max_observations" not in confirmation:
            raise ValueError(
                "perception.confirmation.max_observations is required for "
                "policy='consecutive_grid'"
            )

        policy = ConsecutiveGridConfirmationPolicy(
            confirmation["required_samples"]
        )
        max_observations = confirmation["max_observations"]
        if type(max_observations) is not int:
            raise ValueError(
                "perception.confirmation.max_observations must be an integer"
            )
        if max_observations < policy.required_samples:
            raise ValueError(
                "perception.confirmation.max_observations must be greater than "
                "or equal to required_samples"
            )
        return policy, max_observations

    raise ValueError(
        f"unsupported perception.confirmation.policy: {policy_name!r}"
    )
