"""Decision policy and notifications, independent of device and simulation time."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from threading import Condition
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from sky_executor.perception.contracts import PerceptionSnapshot


class DecisionChoice(str, Enum):
    SKIP = "skip"
    DECIDE = "decide"
    REPLAN_AND_DECIDE = "replan_and_decide"


@dataclass(frozen=True)
class DecisionChange:
    sequence: int
    kind: str
    subject: object = None


class DecisionPolicy(Protocol):
    def should_snapshot(self, changes: tuple[DecisionChange, ...]) -> bool: ...
    def choose_decision(self, snapshot, changes: tuple[DecisionChange, ...]) -> DecisionChoice: ...


class DefaultDecisionPolicy:
    """Decide initially and after each completed simulation step."""
    def should_snapshot(self, changes):
        return any(change.kind in {"startup", "simulation_step_finished"} for change in changes)

    def choose_decision(self, snapshot, changes):
        return DecisionChoice.DECIDE


@dataclass(frozen=True)
class DecisionSelection:
    """A policy choice made from a snapshot, before any solver is called."""
    snapshot: PerceptionSnapshot
    choice: DecisionChoice


@dataclass(frozen=True)
class DecisionCycleResult:
    """The outcome of one complete decision attempt, including skips."""
    snapshot: PerceptionSnapshot | None = None
    choice: DecisionChoice | None = None
    decision: dict | None = None
    replan_error: str | None = None


class DecisionNotifications:
    """Retain unconsumed changes and wake a caller-owned decision loop."""
    def __init__(self):
        self._condition = Condition()
        self._sequence = 0
        self._changes = []
        self.closed = False
        self.publish((("startup", None),))

    @property
    def sequence(self):
        with self._condition:
            return self._sequence

    def publish(self, changes):
        with self._condition:
            for kind, subject in changes:
                self._sequence += 1
                self._changes.append(DecisionChange(self._sequence, kind, subject))
            self._condition.notify_all()

    def since(self, sequence, *, through=None):
        with self._condition:
            end = self._sequence if through is None else through
            return tuple(change for change in self._changes if sequence < change.sequence <= end)

    def consume(self, through):
        with self._condition:
            self._changes = [change for change in self._changes if change.sequence > through]

    def wait(self, after, stop):
        with self._condition:
            self._condition.wait_for(lambda: self.closed or stop.is_set() or self._sequence > after)

    def wake(self):
        with self._condition:
            self._condition.notify_all()

    def close(self):
        with self._condition:
            self.closed = True
            self._condition.notify_all()
