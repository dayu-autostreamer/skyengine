"""Record committed factory changes independently of injected-fault generation."""
from copy import deepcopy
from dataclasses import dataclass
import json
import os
from threading import RLock
from typing import Any, Dict


@dataclass(frozen=True, slots=True)
class FactoryEvent:
    step: int
    kind: str
    payload: dict
    level: str = "info"


class FactoryEventRecorder:
    def __init__(self, state, log_path=None):
        self.state = state
        self._lock = RLock()
        self._exception_log_path = log_path
        self.reset()

    def reset(self):
        with self._lock:
            self._frame_events = []
            self._all_events = []
            self._pending_events = []
            self._in_frame = False
            self._metrics = self._new_metrics()
            self._prepare_event_log()
            self.publish()

    @property
    def cursor(self):
        with self._lock:
            return len(self._all_events)

    def begin_frame(self):
        with self._lock:
            self._frame_events = self._pending_events
            self._pending_events = []
            self._in_frame = True
            self.publish()

    def finish_frame(self):
        with self._lock:
            self._in_frame = False

    def current_events(self):
        with self._lock:
            return deepcopy(self._frame_events)

    def since(self, cursor):
        with self._lock:
            return deepcopy(self._all_events[cursor:])

    def get_metrics(self):
        with self._lock:
            return dict(self._metrics)

    def increment(self, metric, amount=1):
        with self._lock:
            self._metrics[metric] += amount

    def add_downtime(self, kind, duration):
        with self._lock:
            self.increment(kind + "_down_steps_total", duration)
            self.publish()

    def record(self, step, kind, payload, level="info"):
        with self._lock:
            self.state.event_epoch += 1
            event = dict(step=int(step), type=kind, level=level, payload=deepcopy(payload),
                         event_epoch=self.state.event_epoch)
            self._frame_events.append(event)
            self._all_events.append(event)
            if kind in {"machine_breakdown", "machine_recovery", "agv_breakdown",
                        "agv_recovery", "temporary_obstacle", "obstacle_clear"}:
                self._metrics["event_count_total"] += 1
            if not self._in_frame:
                self._pending_events.append(event)
            self.publish()
            self._write_event_log(event)

    def publish(self):
        self.state.last_events = self.current_events()
        self.state.event_metrics = self.get_metrics()

    def get_epochs(self):
        return {name: int(getattr(self.state, name)) for name in
                ("event_epoch", "map_epoch", "machine_epoch", "agv_epoch", "job_epoch")}

    def enrich_task_observation(self, observation):
        observation.update(self.get_epochs())
        observation.update(events=self.current_events(), event_metrics=self.get_metrics(),
            agv_status=list(self.state.agv_status), agv_down_elapsed=list(self.state.agv_down_elapsed),
            blocked_cells=[list(cell) for cell in sorted(self.state.reported_temporary_obstacles)])

    @staticmethod
    def _new_metrics() -> Dict[str, int]:
        return {
            "event_count_total": 0,
            "machine_failure_count": 0,
            "machine_recovery_count": 0,
            "machine_down_steps_total": 0,
            "agv_failure_count": 0,
            "agv_recovery_count": 0,
            "agv_down_steps_total": 0,
            "temporary_obstacle_count": 0,
            "obstacle_clear_count": 0,
        }


    def _prepare_event_log(self) -> None:
        if not self._exception_log_path:
            return
        log_dir = os.path.dirname(os.path.abspath(str(self._exception_log_path)))
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(self._exception_log_path, "w", encoding="utf-8"):
            pass


    def _write_event_log(self, event: Dict[str, Any]) -> None:
        if not self._exception_log_path:
            return
        with open(self._exception_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
