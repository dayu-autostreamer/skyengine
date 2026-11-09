"""Legacy batch sources and individual sources for offline report validation."""

from __future__ import annotations

from time import time
from typing import Any, Callable, Iterable, Literal

from sky_executor.perception.contracts import (
    AgvAvailabilityObservation,
    AgvObservation,
    MachineAvailabilityObservation,
    ObservationBatch,
    ObservationSource,
    ObservationUnavailableError,
    PerceptionReport,
)


class PogemaObservationSource:
    """Read simulated action candidates, or the grid after environment reset."""

    def __init__(self, environment: Any) -> None:
        self._environment = environment
        self._sequence = 0

    def reset(self) -> None:
        self._sequence = 0

    def observe(self) -> ObservationBatch:
        self._sequence += 1
        observations = tuple(
            AgvObservation(agv_id=agent_id, grid_cell=tuple(position), confidence=1.0)
            for agent_id, position in enumerate(
                self._environment.get_observable_agent_positions()
            )
        )
        return ObservationBatch(
            source="simulation",
            sequence=self._sequence,
            captured_at=time(),
            agvs=observations,
        )

    def close(self) -> None:
        return None


class SequenceObservationSource:
    """Replay an in-memory sequence of batches for tests and offline prototypes."""

    def __init__(self, batches: Iterable[ObservationBatch]) -> None:
        self._batches = tuple(batches)
        self._index = 0

    def reset(self) -> None:
        self._index = 0

    def observe(self) -> ObservationBatch:
        if self._index >= len(self._batches):
            raise ObservationUnavailableError("observation sequence is exhausted")
        batch = self._batches[self._index]
        self._index += 1
        return batch

    def close(self) -> None:
        return None


class SequenceReportSource:
    """Replay reports as supplied, including invalid reports for offline tests."""

    def __init__(self, reports: Iterable[PerceptionReport]) -> None:
        self._reports = tuple(reports)
        self._index = 0

    def reset(self) -> None:
        self._index = 0

    def observe(self) -> PerceptionReport:
        if self._index >= len(self._reports):
            raise ObservationUnavailableError("report sequence is exhausted")
        report = self._reports[self._index]
        self._index += 1
        return report

    def close(self) -> None:
        return None


class PogemaReportSource:
    """Read one selected simulated device fact per call, without stepping it.

    Use a distinct source name for each independent sequence stream. Reset the
    source and processor together when starting a new session. This test adapter
    is not registered in the existing batch runtime configuration.
    """

    def __init__(
        self,
        environment: Any,
        *,
        source: str,
        fact_kind: Literal["agv_position", "agv_availability", "machine_availability"],
        device_id: int,
        clock: Callable[[], float] = time,
    ) -> None:
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source must be a non-empty string")
        if fact_kind not in (
            "agv_position", "agv_availability", "machine_availability"
        ):
            raise ValueError(f"unsupported fact_kind: {fact_kind!r}")
        if type(device_id) is not int or device_id < 0:
            raise ValueError("device_id must be a non-negative integer")
        self._environment = environment
        self._source = source
        self._fact_kind = fact_kind
        self._device_id = device_id
        self._clock = clock
        self._sequence = 0

    def reset(self) -> None:
        self._sequence = 0

    def observe(self) -> PerceptionReport:
        device_id = self._device_id
        if self._fact_kind == "agv_position":
            positions = self._environment.get_observable_agent_positions()
            if device_id >= len(positions):
                raise ObservationUnavailableError(f"unknown simulated AGV: {device_id}")
            fact = AgvObservation(device_id, tuple(positions[device_id]), confidence=1.0)
        elif self._fact_kind == "agv_availability":
            base = self._environment.pogema_env
            while hasattr(base, "env"):
                base = base.env
            if device_id >= len(base.agv_status):
                raise ObservationUnavailableError(f"unknown simulated AGV: {device_id}")
            fact = AgvAvailabilityObservation(device_id, base.agv_status[device_id])
        else:
            machine = next(
                (m for m in self._environment.get_machines() if m.id == device_id), None
            )
            if machine is None:
                raise ObservationUnavailableError(f"unknown simulated machine: {device_id}")
            fact = MachineAvailabilityObservation(device_id, machine.status)
        captured_at = self._clock()
        self._sequence += 1
        return PerceptionReport(self._source, self._sequence, captured_at, fact)

    def close(self) -> None:
        return None


def create_observation_source(
    config: dict | None,
    environment: Any,
) -> ObservationSource:
    """Create the configured source at the single runtime selection point."""

    config = config or {}
    if not isinstance(config, dict):
        raise ValueError("perception must be an object")
    source_name = config.get("source", "simulation")
    if source_name == "simulation":
        return PogemaObservationSource(environment)
    raise ValueError(f"unsupported perception.source: {source_name!r}")
