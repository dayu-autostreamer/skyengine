"""Reusable system-injected fault lifecycle; scenes supply clocks and effects."""
from __future__ import annotations
import json
import math
import os
from threading import RLock
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple


class FaultInjector:
    SUPPORTED_TYPES = {"machine_breakdown", "agv_breakdown", "temporary_obstacle"}

    PRESETS = {
        "no_event": {},
        "mild_failure": {
            "machine_failure": {
                "enabled": True,
                "mtbf_steps": 300,
                "busy_only": True,
                "repair_time": {"dist": "fixed", "value": 10},
            },
            "agv_failure": {
                "enabled": True,
                "mtbf_steps": 500,
                "busy_only": False,
                "repair_time": {"dist": "fixed", "value": 8},
            },
        },
        "moderate_failure": {
            "machine_failure": {
                "enabled": True,
                "mtbf_steps": 180,
                "busy_only": False,
                "repair_time": {"dist": "discrete_uniform", "low": 10, "high": 30},
            },
            "agv_failure": {
                "enabled": True,
                "mtbf_steps": 260,
                "busy_only": False,
                "repair_time": {"dist": "discrete_uniform", "low": 5, "high": 20},
            },
            "temporary_obstacle": {
                "enabled": True,
                "mean_interarrival_steps": 140,
                "max_new_per_step": 1,
                "preserve_connectivity": True,
                "duration": {"dist": "discrete_uniform", "low": 8, "high": 24},
            },
        },
        "stress_failure": {
            "machine_failure": {
                "enabled": True,
                "mtbf_steps": 30,
                "busy_only": False,
                "repair_time": {"dist": "discrete_uniform", "low": 20, "high": 60},
            },
            "agv_failure": {
                "enabled": True,
                "mtbf_steps": 50,
                "busy_only": False,
                "repair_time": {"dist": "discrete_uniform", "low": 10, "high": 40},
            },
            "temporary_obstacle": {
                "enabled": True,
                "mean_interarrival_steps": 35,
                "max_new_per_step": 1,
                "preserve_connectivity": True,
                "duration": {"dist": "discrete_uniform", "low": 8, "high": 24},
            },
        },
        "routing_disruption": {
            "temporary_obstacle": {
                "enabled": True,
                "mean_interarrival_steps": 25,
                "max_new_per_step": 1,
                "preserve_connectivity": True,
                "duration": {"dist": "discrete_uniform", "low": 8, "high": 24},
            },
        },
        "combined_moderate": {
            "machine_failure": {
                "enabled": True,
                "mtbf_steps": 80,
                "busy_only": False,
                "repair_time": {"dist": "discrete_uniform", "low": 10, "high": 30},
            },
            "agv_failure": {
                "enabled": True,
                "mtbf_steps": 120,
                "busy_only": False,
                "repair_time": {"dist": "discrete_uniform", "low": 5, "high": 20},
            },
            "temporary_obstacle": {
                "enabled": True,
                "mean_interarrival_steps": 40,
                "max_new_per_step": 1,
                "preserve_connectivity": True,
                "duration": {"dist": "discrete_uniform", "low": 8, "high": 24},
            },
        },
    }

    DEFAULT_CONFIG = {
        "enabled": False,
        "random_seed": None,
        "preset": None,
        "schedule": [],
        "replay_file": None,
        "exception_log_path": None,
        "machine_failure": {
            "enabled": False,
            "prob_per_machine_step": 0.0,
            "mtbf_steps": None,
            "busy_only": False,
            "repair_time": {"dist": "fixed", "value": 10},
        },
        "agv_failure": {
            "enabled": False,
            "prob_per_agv_step": 0.0,
            "mtbf_steps": None,
            "busy_only": False,
            "repair_time": {"dist": "fixed", "value": 10},
        },
        "temporary_obstacle": {
            "enabled": False,
            "prob_per_step": 0.0,
            "mean_interarrival_steps": None,
            "lambda_per_step": None,
            "max_new_per_step": 1,
            "preserve_connectivity": True,
            "duration": {"dist": "fixed", "value": 10},
        },
    }

    def __init__(self, scene, config=None):
        self.scene = scene
        self.input_lock = RLock()
        explicit = config or {}
        preset = self.PRESETS.get(str(explicit.get("preset")), {})
        if explicit.get("preset") and str(explicit["preset"]) not in self.PRESETS:
            raise ValueError("Unknown exception preset: " + str(explicit["preset"]))
        self.config = self._merge_config(self._merge_config(self.DEFAULT_CONFIG, preset), explicit)
        self.enabled = explicit.get("enabled", bool(self.config.get("schedule") or self.config.get("replay_file")
            or any(self.config.get(name, {}).get("enabled") for name in ("machine_failure", "agv_failure", "temporary_obstacle"))))
        self.reset()

    def apply_event(self, event):
        with self.input_lock:
            return self._apply_event(self.scene.env.state, event)

    def reset(self):
        with self.input_lock:
            self._schedule = self._load_schedule()
            self._schedule_idx = 0
            self._active_obstacles = {}
            self._repairs = {}

    def trigger_scheduled(self, schedule_time, *, skip_expired=False):
        """The scene defines schedule coordinates and whether past events expire."""
        with self.input_lock:
            if self.enabled:
                self._apply_scheduled_events(self.scene.env.state, schedule_time, skip_expired=skip_expired)

    def expire_effects(self, now):
        """Only update owned effects; do not generate faults or clear events."""
        with self.input_lock:
            if self.enabled:
                self._tick_repairs(self.scene.env.state, now)
                self._tick_obstacles(self.scene.env.state, now)

    @classmethod
    def configuration_from_env(cls, config: Optional[Dict[str, Any]] = None) -> dict:
        """Parse fault configuration from an explicit config plus environment vars."""
        env_config: Dict[str, Any] = {}
        if os.getenv("EXCEPTIONS_ENABLED") is not None:
            env_config["enabled"] = _truthy(os.getenv("EXCEPTIONS_ENABLED"))
        if os.getenv("EXCEPTION_RANDOM_SEED") is not None:
            env_config["random_seed"] = int(os.getenv("EXCEPTION_RANDOM_SEED"))
        if os.getenv("EXCEPTIONS_PRESET"):
            env_config["preset"] = os.getenv("EXCEPTIONS_PRESET")
        if os.getenv("EXCEPTIONS_SCHEDULE_JSON"):
            env_config["schedule"] = json.loads(os.getenv("EXCEPTIONS_SCHEDULE_JSON", "[]"))
        if os.getenv("EXCEPTIONS_REPLAY_FILE"):
            env_config["replay_file"] = os.getenv("EXCEPTIONS_REPLAY_FILE")
            env_config["enabled"] = True
        if os.getenv("EXCEPTIONS_LOG_PATH"):
            env_config["exception_log_path"] = os.getenv("EXCEPTIONS_LOG_PATH")

        machine_prob = float(os.getenv("MACHINE_FAILURE_PROB", "0") or 0)
        machine_mtbf = float(os.getenv("MACHINE_MTBF_STEPS", "0") or 0)
        agv_prob = float(os.getenv("AGV_FAILURE_PROB", "0") or 0)
        agv_mtbf = float(os.getenv("AGV_MTBF_STEPS", "0") or 0)
        obstacle_prob = float(os.getenv("TEMP_OBSTACLE_PROB", "0") or 0)
        obstacle_mean = float(os.getenv("TEMP_OBSTACLE_MEAN_INTERARRIVAL_STEPS", "0") or 0)

        if machine_prob > 0 or machine_mtbf > 0:
            env_config.setdefault("machine_failure", {})
            env_config["machine_failure"].update({
                "enabled": True,
                "repair_time": {
                    "dist": "fixed",
                    "value": int(os.getenv("MACHINE_REPAIR_TIME_STEPS", "10")),
                },
            })
            if machine_prob > 0:
                env_config["machine_failure"]["prob_per_machine_step"] = machine_prob
            if machine_mtbf > 0:
                env_config["machine_failure"]["mtbf_steps"] = machine_mtbf
            env_config["enabled"] = True
        if agv_prob > 0 or agv_mtbf > 0:
            env_config.setdefault("agv_failure", {})
            env_config["agv_failure"].update({
                "enabled": True,
                "repair_time": {
                    "dist": "fixed",
                    "value": int(os.getenv("AGV_REPAIR_TIME_STEPS", "10")),
                },
            })
            if agv_prob > 0:
                env_config["agv_failure"]["prob_per_agv_step"] = agv_prob
            if agv_mtbf > 0:
                env_config["agv_failure"]["mtbf_steps"] = agv_mtbf
            env_config["enabled"] = True
        if obstacle_prob > 0 or obstacle_mean > 0:
            env_config.setdefault("temporary_obstacle", {})
            env_config["temporary_obstacle"].update({
                "enabled": True,
                "duration": {
                    "dist": "fixed",
                    "value": int(os.getenv("TEMP_OBSTACLE_DURATION_STEPS", "10")),
                },
            })
            if obstacle_prob > 0:
                env_config["temporary_obstacle"]["prob_per_step"] = obstacle_prob
            if obstacle_mean > 0:
                env_config["temporary_obstacle"]["mean_interarrival_steps"] = obstacle_mean
            if os.getenv("TEMP_OBSTACLE_MAX_NEW_PER_STEP"):
                env_config["temporary_obstacle"]["max_new_per_step"] = int(os.getenv("TEMP_OBSTACLE_MAX_NEW_PER_STEP", "1"))
            env_config["enabled"] = True
        merged = cls._merge_config(env_config, config or {})
        return merged


    @staticmethod
    def _merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = deepcopy(base)
        for key, value in (override or {}).items():
            if (
                isinstance(value, dict)
                and isinstance(result.get(key), dict)
            ):
                result[key] = FaultInjector._merge_config(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result


    def _load_schedule(self) -> List[Dict[str, Any]]:
        schedule: List[Dict[str, Any]] = list(self.config.get("schedule") or [])
        replay_file = self.config.get("replay_file")
        if replay_file:
            schedule.extend(self._read_replay_file(str(replay_file)))
        unsupported = sorted({
            str(item.get("type")) for item in schedule
            if item.get("type") not in self.SUPPORTED_TYPES
        })
        if unsupported:
            raise ValueError(f"Unsupported Exception types: {', '.join(unsupported)}")
        return sorted(schedule, key=lambda item: int(item.get("step", 0)))


    def _read_replay_file(self, replay_file: str) -> List[Dict[str, Any]]:
        with open(replay_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return []
        if content[0] == "[":
            data = json.loads(content)
            if not isinstance(data, list):
                raise ValueError(f"Replay file must contain a JSON array or JSONL events: {replay_file}")
            return data
        events: List[Dict[str, Any]] = []
        for line_no, line in enumerate(content.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError(f"Replay JSONL line {line_no} is not an event object: {replay_file}")
            events.append(event)
        return events


    def _apply_scheduled_events(self, penv, step: int, *, skip_expired=False) -> None:
        while self._schedule_idx < len(self._schedule):
            event = self._schedule[self._schedule_idx]
            event_step = int(event.get("step", 0))
            if event_step > step:
                break
            self._schedule_idx += 1
            if skip_expired and event_step < step:
                continue
            self._apply_event(penv, event)


    def _apply_event(self, penv, event: Dict[str, Any]) -> bool:
        etype = event.get("type")
        if etype == "machine_breakdown":
            duration = int(event.get("duration_steps", event.get("duration", 1)))
            return self._machine_breakdown(penv, int(event["machine_id"]), duration, event.get("reason"))
        elif etype == "agv_breakdown":
            duration = int(event.get("duration_steps", event.get("duration", 1)))
            return self._agv_breakdown(penv, int(event["agv_id"]), duration, event.get("reason"))
        elif etype == "temporary_obstacle":
            duration = int(event.get("duration_steps", event.get("duration", 1)))
            cell = tuple(event["cell"])
            return self._temporary_obstacle(penv, cell, duration, event.get("reason"))
        return False


    def _submit(self, fact):
        report_outcomes = self.scene.publish_facts((fact,))
        return report_outcomes[0].committed.applied


    def _machine_breakdown(self, penv, machine_id, duration, reason=None):
        machine = next((m for m in penv.machines if m.id == machine_id), None)
        if machine is None or machine.status != "OK":
            return False
        duration = max(1, int(duration))
        reason = reason or "machine_breakdown"
        now = self.scene.now()
        if self.scene.set_machine_fault(machine_id, active=True, reason=reason, remaining=duration).committed.applied:
            self._repairs[("machine", machine_id)] = (now + duration, reason, now)
            return True


    def _agv_breakdown(self, penv, agv_id, duration, reason=None):
        if not 0 <= agv_id < penv.grid_config.num_agents or penv.agv_status[agv_id] != "OK":
            return False
        duration = max(1, int(duration))
        reason = reason or "agv_breakdown"
        now = self.scene.now()
        if self.scene.set_agv_fault(
                agv_id, active=True, reason=reason, remaining=duration).committed.applied:
            self._repairs[("agv", agv_id)] = (now + duration, reason, now)
            return True


    def _temporary_obstacle(self, penv, cell, duration, reason=None):
        from sky_executor.perception.contracts import TemporaryObstacleObservation
        cell = tuple(cell)
        if not self.scene.can_block_cell(cell) or cell in penv.reported_temporary_obstacles:
            return False
        duration = max(1, int(duration))
        state = {"ends_at": self.scene.now() + duration, "reason": reason or "temporary_obstacle"}
        if self.scene.publish_facts((TemporaryObstacleObservation(cell, "BLOCKED"),))[0].committed.applied:
            self._active_obstacles[cell] = state
            return True


    def _tick_repairs(self, penv, now):
        from sky_executor.perception.contracts import (
            AgvAvailabilityObservation, MachineAvailabilityObservation,
        )
        for kind, device_id in sorted(self._repairs, key=lambda key: (key[0] != "machine", key[1])):
            ends_at, reason, reported_at = self._repairs[(kind, device_id)]
            if now == reported_at:
                continue
            if kind == "machine":
                status = next(m for m in penv.machines if m.id == device_id).status
                observation = MachineAvailabilityObservation
            else:
                status = penv.agv_status[device_id]
                observation = AgvAvailabilityObservation
            if status != "DOWN":
                del self._repairs[(kind, device_id)]
                continue
            with self.scene.env.processing_lock, self.scene.env.state_lock:
                elapsed = min(now, ends_at) - reported_at
                self.scene.env.events.add_downtime(kind, elapsed)
                if kind == "machine":
                    next(m for m in penv.machines if m.id == device_id).down_elapsed += elapsed
                else:
                    penv.agv_down_elapsed[device_id] += elapsed
            remaining = max(0, math.ceil(ends_at - now))
            if remaining == 0:
                if kind == "agv":
                    applied = self.scene.set_agv_fault(device_id, active=False).committed.applied
                else:
                    applied = self.scene.set_machine_fault(device_id, active=False).committed.applied
            else:
                applied = self._submit(observation(device_id, "DOWN", reason, remaining))
            if applied:
                if remaining == 0:
                    del self._repairs[(kind, device_id)]
                else:
                    self._repairs[(kind, device_id)] = (ends_at, reason, now)


    def _tick_obstacles(self, penv, now):
        from sky_executor.perception.contracts import TemporaryObstacleObservation
        for cell, state in list(self._active_obstacles.items()):
            if now >= state["ends_at"]:
                if self._submit(TemporaryObstacleObservation(cell, "CLEAR")):
                    del self._active_obstacles[cell]


    def inject_manual(self, event: Dict[str, Any], *, step: int) -> Dict[str, Any]:
        """Inject one operator-requested Exception now or schedule it for a later step."""
        with self.input_lock:
            penv = self.scene.env.state
            self.enabled = True
            manual_event = deepcopy(event or {})
            event_type = manual_event.get("type")
            if event_type not in self.SUPPORTED_TYPES:
                return {
                    "status": "error",
                    "step": int(step),
                    "type": event_type,
                    "message": f"Unsupported Exception type: {event_type}",
                }
            target_step = int(manual_event.get("start_step", manual_event.get("step", step)))
            manual_event["step"] = target_step

            if target_step > int(step):
                self._schedule.append(manual_event)
                self._schedule = sorted(self._schedule, key=lambda item: int(item.get("step", 0)))
                return {
                    "status": "scheduled",
                    "step": target_step,
                    "type": manual_event.get("type"),
                }

            event_cursor = self.scene.env.events.cursor
            applied = self._apply_event(penv, manual_event)
            if not applied:
                return {
                    "status": "ignored",
                    "step": int(step),
                    "type": manual_event.get("type"),
                    "message": "Exception did not apply, target may be invalid or already affected.",
                }
            return {
                "status": "ok",
                "step": int(step),
                "type": manual_event.get("type"),
                "events": self.scene.env.events.since(event_cursor),
            }


    def clear_manual(self, target: Optional[Dict[str, Any]] = None, *, step: int) -> Dict[str, Any]:
        """Clear active operator-visible Exception effects."""
        with self.input_lock:
            penv = self.scene.env.state
            self.enabled = True
            target = target or {}
            target_type = target.get("type")
            cleared = []
            event_cursor = self.scene.env.events.cursor

            def should_clear_machine(machine_id: int) -> bool:
                return target_type in (None, "machine_breakdown") and (
                    target.get("machine_id") is None or int(target.get("machine_id")) == int(machine_id)
                )

            def should_clear_agv(agv_id: int) -> bool:
                return target_type in (None, "agv_breakdown") and (
                    target.get("agv_id") is None or int(target.get("agv_id")) == int(agv_id)
                )

            def should_clear_cell(cell: Tuple[int, int]) -> bool:
                if target_type not in (None, "temporary_obstacle"):
                    return False
                if target.get("cell") is None:
                    return True
                raw = target.get("cell")
                return tuple(int(v) for v in raw[:2]) == tuple(cell)

            from sky_executor.perception.contracts import (
                TemporaryObstacleObservation,
            )
            for machine in penv.machines:
                if machine.status == "DOWN" and should_clear_machine(machine.id):
                    if self.scene.set_machine_fault(machine.id, active=False).committed.applied:
                        self._repairs.pop(("machine", machine.id), None)
                        cleared.append({"type": "machine_breakdown", "machine_id": machine.id})
            for idx, status in enumerate(penv.agv_status):
                if status == "DOWN" and should_clear_agv(idx):
                    applied = self.scene.set_agv_fault(idx, active=False).committed.applied
                    if applied:
                        self._repairs.pop(("agv", idx), None)
                        cleared.append({"type": "agv_breakdown", "agv_id": idx})
            for cell in list(self._active_obstacles):
                if should_clear_cell(cell) and self._submit(TemporaryObstacleObservation(cell, "CLEAR")):
                    del self._active_obstacles[cell]
                    cleared.append({"type": "temporary_obstacle", "cell": list(cell)})

            return {
                "status": "ok",
                "step": int(step),
                "cleared": cleared,
                "events": self.scene.env.events.since(event_cursor),
            }


def _truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}
