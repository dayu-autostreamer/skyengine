"""Canonical contracts for environment perception.

Observation sources report positions in SkyEngine's public, unpadded grid
coordinates.  Sensor-specific coordinates and calibration stay inside the
source implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Mapping, Protocol, runtime_checkable

from sky_executor.execution import AgvExecutionUpdate, MachineExecutionUpdate, ExecutionUpdateResult

if TYPE_CHECKING:
    from sky_executor.grid_factory.factory.business import SettlementResult
    from sky_executor.grid_factory.factory.Utils.structure import Job


GridCell = tuple[int, int]


@dataclass(frozen=True, slots=True)
class AgvObservation:
    """One observed AGV position in the canonical business grid."""

    agv_id: int
    grid_cell: GridCell
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class AgvAvailabilityObservation:
    """One observed AGV resource status, separate from its task phase."""

    agv_id: int
    status: str
    reason: str | None = None
    repair_remaining: int | None = None


@dataclass(frozen=True, slots=True)
class MachineAvailabilityObservation:
    """One observed machine resource status, separate from processing progress."""

    machine_id: int
    status: str
    reason: str | None = None
    repair_remaining: int | None = None


@dataclass(frozen=True, slots=True)
class TemporaryObstacleObservation:
    """One temporary obstacle fact in the canonical business grid."""

    grid_cell: GridCell
    status: str


PerceptionFact = (
    AgvObservation
    | AgvAvailabilityObservation
    | MachineAvailabilityObservation
    | TemporaryObstacleObservation
)


@dataclass(frozen=True, slots=True)
class JobInsertionRequest:
    """Normalized order definitions, staged until a production replan succeeds."""
    request_id: str
    jobs: tuple[dict, ...]
    accepted_step: int
    inserted: tuple[dict, ...] = ()
    rejected: tuple[dict, ...] = ()


@dataclass(frozen=True, slots=True)
class JobPlanningUpdate:
    """Planning outcome; a missing request id applies an existing recovery plan."""
    request_id: str | None
    phase: str
    new_jobs: tuple[Job, ...] = ()
    replanned_keys: frozenset[tuple[int, int]] = frozenset()
    latency_ms: float = 0
    reason: str = ""


@dataclass(frozen=True, slots=True)
class JobInsertionResult:
    applied: bool
    reason: str
    request_id: str | None
    phase: str | None = None


@dataclass(frozen=True, slots=True)
class RescheduleRequest:
    action: dict


@dataclass(frozen=True, slots=True)
class JobReleaseCheck:
    time: float


@dataclass(frozen=True, slots=True)
class PlanningResult:
    applied: bool
    reason: str


@dataclass(frozen=True, slots=True)
class PerceptionReport:
    """One state fact or execution update from a logical source stream.

    Sequence numbers order a source/device/fact or request stream, not time.
    Hardware adapters convert their inputs to these canonical fields.
    """

    source: str
    sequence: int
    captured_at: float
    fact: PerceptionFact | AgvExecutionUpdate | MachineExecutionUpdate | JobInsertionRequest | JobPlanningUpdate | RescheduleRequest | JobReleaseCheck
    movement_request_id: str | None = None


ReportStreamKey = tuple[str, type, int | GridCell | str]


def report_stream_key(report: PerceptionReport) -> ReportStreamKey | None:
    """Identify a fact stream, without validating its fact value or device registry.

    Invalid but identifiable facts can still have diagnostics. In particular,
    position coordinates do not affect the identity of an AGV position stream.
    """
    if not isinstance(report.source, str) or not report.source.strip():
        return None
    fact = report.fact
    if isinstance(fact, (AgvExecutionUpdate, MachineExecutionUpdate)):
        return report.source, type(fact), fact.request_id
    if isinstance(fact, (AgvObservation, AgvAvailabilityObservation)):
        target = fact.agv_id
    elif isinstance(fact, MachineAvailabilityObservation):
        target = fact.machine_id
    elif isinstance(fact, TemporaryObstacleObservation):
        target = fact.grid_cell
        if (
            not isinstance(target, tuple) or len(target) != 2
            or any(type(value) is not int for value in target)
        ):
            return None
        return report.source, type(fact), target
    else:
        return None
    if type(target) is not int:
        return None
    return report.source, type(fact), target


class ReportStatus(str, Enum):
    """Outcome of validating and confirming one report, before state commit."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"


@dataclass(frozen=True, slots=True)
class ReportResult:
    """Keep the input for explanation; expose a fact only after acceptance."""

    report: PerceptionReport
    status: ReportStatus
    reason: str

    @property
    def accepted_fact(self) -> PerceptionFact | None:
        if self.status is ReportStatus.ACCEPTED:
            return self.report.fact
        return None


class FactChangeKind(str, Enum):
    """Changes to committed facts, separate from task completion."""

    POSITION = "position"
    AVAILABILITY = "availability"
    TEMPORARY_OBSTACLE = "temporary_obstacle"


@dataclass(frozen=True, slots=True)
class FactChangeEvent:
    """One committed change; the report identifies the device and evidence."""

    kind: FactChangeKind
    report: PerceptionReport
    before: GridCell | str
    after: GridCell | str


@dataclass(frozen=True, slots=True)
class CommitResult:
    """Result of applying an accepted fact, including any resulting change."""

    report: PerceptionReport
    applied: bool
    reason: str
    events: tuple[FactChangeEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class ReportOutcome:
    """Separate acceptance, fact application and direct business settlement.

    None means settlement has not completed, not a successful no-op.
    """

    processed: ReportResult
    committed: CommitResult
    settlement: SettlementResult | None = None


ReportApplicationResult = ReportOutcome | ExecutionUpdateResult | JobInsertionResult | PlanningResult


@dataclass(frozen=True, slots=True)
class PositionConfirmationState:
    """Evidence for one source/AGV, not a copy of the environment position."""

    source: str
    agv_id: int
    accepted_report: PerceptionReport | None
    candidate_report: PerceptionReport | None
    candidate_samples: int
    required_samples: int | None


@dataclass(frozen=True, slots=True)
class PerceptionSnapshot:
    """Independent data at a queue boundary; observation remains mutable."""

    observation: dict[str, object]
    committed_reports: tuple[PerceptionReport, ...]
    confirmation_states: tuple[PositionConfirmationState, ...]
    recent_outcomes: tuple[ReportOutcome, ...]
    execution: dict | None = None
    machine_execution: dict | None = None
    job_insertions: tuple[dict, ...] = ()
    insertion_metrics: dict | None = None
    decision_sequence: int = 0


@dataclass(frozen=True, slots=True)
class ObservationBatch:
    """An atomic set of AGV observations captured by one source."""

    source: str
    sequence: int
    captured_at: float
    agvs: tuple[AgvObservation, ...]


class ConfirmationStatus(str, Enum):
    """Semantic confirmation outcome for one structurally valid batch."""

    PENDING = "pending"
    CONFIRMED = "confirmed"


@dataclass(frozen=True, slots=True)
class ConfirmationResult:
    """Result of applying a semantic confirmation policy to one batch."""

    status: ConfirmationStatus
    batch: ObservationBatch
    confirmed_positions: Mapping[int, GridCell] | None
    consecutive_samples: int


class PerceptionError(RuntimeError):
    """Base error for unavailable or rejected perception input."""


class ObservationUnavailableError(PerceptionError):
    """Raised when a source cannot provide its next batch or report."""


class ObservationRejectedError(PerceptionError):
    """Raised when a batch cannot be structurally accepted for application."""


class ObservationConfirmationExhaustedError(PerceptionError):
    """Raised when bounded sampling ends without a confirmed observation."""


@runtime_checkable
class ObservationSource(Protocol):
    """Provides one canonical observation batch per environment boundary."""

    def reset(self) -> None:
        ...

    def observe(self) -> ObservationBatch:
        ...

    def close(self) -> None:
        ...


@runtime_checkable
class ReportSource(Protocol):
    """Provide one report per read, without committing state or waiting for confirmation."""

    def reset(self) -> None:
        ...

    def observe(self) -> PerceptionReport:
        ...

    def close(self) -> None:
        ...


@runtime_checkable
class StateReconciler(Protocol):
    """Structurally validates a batch before it may be applied.

    Implementations at this stage do not establish physical stability or
    completion of an AGV movement.
    """

    def reset(self) -> None:
        ...

    def reconcile(
        self,
        batch: ObservationBatch,
        *,
        expected_ids: set[int],
        grid_size: tuple[int, int],
    ) -> Mapping[int, GridCell]:
        ...


@runtime_checkable
class ObservationConfirmationPolicy(Protocol):
    """Evaluates semantic stability after structural reconciliation."""

    name: str

    def reset(self) -> None:
        ...

    def evaluate(
        self,
        batch: ObservationBatch,
        positions: Mapping[int, GridCell],
    ) -> ConfirmationResult:
        ...
