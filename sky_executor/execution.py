"""A replaceable action boundary; sensing and business settlement stay outside."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable, Literal, Protocol

if TYPE_CHECKING:
    from sky_executor.perception.contracts import AgvAvailabilityObservation, MachineAvailabilityObservation


class ExecutionStatus(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    DEFERRED = "deferred"  # Dropoff attempt ended without unloading; a new request may retry.
    FAILED = "failed"


@dataclass(frozen=True)
class AgvRequest:
    request_id: str
    kind: Literal["move", "pickup", "dropoff"]
    agv_ids: tuple[int, ...]
    actions: tuple[int, ...] = ()


@dataclass(frozen=True)
class AgvExecutionUpdate:
    """Execution payload; its report envelope owns source, sequence and time."""
    request_id: str
    status: ExecutionStatus
    remaining: int | None = None
    positions: tuple[tuple[int, int], ...] | None = None
    reason: str = ""


@dataclass(frozen=True)
class ExecutionUpdateResult:
    """Whether the core applied an execution message and settled its business."""
    applied: bool
    reason: str
    business_settled: bool = False


class AgvExecutionPort(Protocol):
    def submit(self, request: AgvRequest) -> AgvExecutionUpdate: ...
    def reset(self) -> None: ...
    def close(self) -> None: ...


class AgvFaultControl(Protocol):
    """Return the established local state; no recovery clock is implied.

    Asynchronous device coordination belongs to its future scene adapter.
    """
    def inject_fault(self, agv_id, reason) -> AgvAvailabilityObservation: ...
    def clear_fault(self, agv_id) -> AgvAvailabilityObservation: ...


@dataclass(frozen=True)
class ProcessingParameters:
    job_id: int
    op_id: int
    nominal_time: float


@dataclass(frozen=True)
class MachineRequest:
    """Start new work, or control the work named by target_request_id."""
    request_id: str
    kind: Literal["start", "pause", "resume"]
    machine_id: int
    processing: ProcessingParameters | None = None
    target_request_id: str | None = None


@dataclass(frozen=True)
class MachineExecutionUpdate:
    """elapsed is cumulative work across pauses; remaining never grants completion."""
    request_id: str
    status: ExecutionStatus
    elapsed: float | None = None
    remaining: float | None = None
    duration: float | None = None
    reason: str = ""


class MachineExecutionPort(Protocol):
    def submit(self, request: MachineRequest) -> MachineExecutionUpdate: ...
    def reset(self) -> None: ...
    def close(self) -> None: ...


class MachineFaultControl(Protocol):
    def inject_fault(self, machine_id, reason) -> MachineAvailabilityObservation: ...
    def clear_fault(self, machine_id) -> MachineAvailabilityObservation: ...


class SimulationTimeDriver(Protocol):
    """Optional scene capability, independent of the device command port."""
    def advance(self, request_ids: tuple[str, ...]) -> tuple[tuple[AgvExecutionUpdate | MachineExecutionUpdate, ...], frozenset[str]]: ...


@dataclass(frozen=True)
class ExecutionBinding:
    """A command port and the optional scene capabilities supplied alongside it."""
    execution_port: AgvExecutionPort | MachineExecutionPort
    simulation_driver: SimulationTimeDriver | None = None
    fault_control: AgvFaultControl | MachineFaultControl | None = None
    simulation_diagnostics: Callable[[str], dict | None] | None = None
    configure_simulation_operations: Callable[[dict], None] | None = None
    configure_simulation_seed: Callable[[int], None] | None = None
    cancel_simulation_requests: Callable[[tuple[str, ...]], None] | None = None


@dataclass(frozen=True)
class HandlingIntent:
    agv_id: int
    kind: Literal["pickup", "dropoff"]


@dataclass(frozen=True)
class MachineIntent:
    machine_id: int
    operation_key: tuple[int, int]
    kind: Literal["process", "pause"] = "process"
