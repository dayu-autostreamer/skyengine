"""Canonical, JSON-safe runtime snapshots shared by training and the GUI."""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from typing import Any


def _json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, set):
        return [_json(item) for item in sorted(value)]
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    if hasattr(value, "model_dump"):
        return _json(value.model_dump())
    if hasattr(value, "dict"):
        return _json(value.dict())
    if hasattr(value, "item"):
        return _json(value.item())
    return str(value)


def _build_runtime_frame(session, insertion_requests: list[dict] | None = None) -> dict[str, Any]:
    """Build the one frame format used by SSE, training traces and replay.

    This reads the live formal ``SimulationSession`` state.  It does not run
    another simulator and it is independent from AnimationMonitor/rendering.
    """
    env = session.env
    pogema = env.state
    observation = env.project_solver_observation()
    public = observation["task_observation"]
    agents, jobs, machines = public["agents"], public["jobs"], public["machines"]
    machine_rows = []
    for machine in machines:
        op = getattr(machine, "current_op", None)
        machine_rows.append({
            "id": machine.id,
            "location": list(machine.location),
            "status": getattr(machine, "status", "OK"),
            "repair_remaining": None,
            "down_elapsed": machine.down_elapsed,
            "buffer_capacity": machine.buffer_capacity,
            "buffer_occupancy": len(machine.buffer_jobs),
            "current_op": None if op is None else {
                "job_id": op.job_id, "op_id": op.op_id,
                "status": getattr(op, "status", None),
                "proc_time": getattr(op, "proc_time", None),
                "sampled_proc_time": getattr(op, "sampled_proc_time", None),
                "start_process_at": getattr(op, "start_process_at", None),
                "finish_process_at": getattr(op, "finish_process_at", None),
                "accumulated_process_time": getattr(op, "accumulated_process_time", 0.0),
                "remaining_proc_time": getattr(op, "remaining_proc_time", None),
            },
            "queue_length": len(getattr(machine, "input_queue", [])),
            "suspended_count": len(getattr(machine, "suspended_ops", [])),
        })
    job_rows = []
    for job in jobs:
        job_rows.append({
            "job_id": job.job_id, "release": job.release, "due": job.due,
            "priority": getattr(job, "priority", 0),
            "request_id": getattr(job, "request_id", None),
            "completion_time": job.completion_time,
            "is_completed": job.is_completed,
            "material_location": job.material_location, "carrier_id": job.carrier_id,
            "raw_material_source": job.raw_material_source,
            "finished_goods_destination": job.finished_goods_destination,
            "delivered": job.delivered,
            "ops": [{
                "op_id": op.op_id, "status": op.status,
                "assigned_machine": op.assigned_machine,
                "proc_time": op.proc_time,
                "nominal_proc_time": getattr(op, "nominal_proc_time", None),
                "sampled_proc_time": getattr(op, "sampled_proc_time", None),
                "start_process_at": getattr(op, "start_process_at", None),
                "finish_process_at": getattr(op, "finish_process_at", None),
                "remaining_proc_time": getattr(op, "remaining_proc_time", None),
                "preemption_count": getattr(op, "preemption_count", 0),
                "processed_time": op.processed_time,
            } for op in job.ops],
        })
    obstacles = public["blocked_cells"]
    events = public["events"]
    frame = {
        "schema_version": 2,
        "step": int(env.env_timeline),
        "timestamp": f"T+{env.env_timeline}s",
        "env_timeline": int(getattr(pogema, "env_timeline", session.step_index)),
        "grid_state": {
            "positions_xy": [list(agent.pos) for agent in agents],
            "finishes_xy": [list(pogema._to_public_xy(item)) for item in pogema.grid.finishes_xy],
            "is_active": [getattr(agent, "current_task", None) is not None for agent in agents],
            "agv_status": list(getattr(pogema, "agv_status", [])),
            "agv_repair_remaining": [None] * len(agents),
            "agv_down_elapsed": list(pogema.agv_down_elapsed),
            "agv_task_phase": list(getattr(pogema, "agv_task_phase", [])),
            "agv_handling_remaining": list(getattr(pogema, "agv_handling_remaining", [])),
            "agv_loaded": list(getattr(pogema, "agv_loaded", [])),
        },
        "event_epoch": int(getattr(pogema, "event_epoch", 0)),
        "map_epoch": int(getattr(pogema, "map_epoch", 0)),
        "machine_epoch": int(getattr(pogema, "machine_epoch", 0)),
        "agv_epoch": int(getattr(pogema, "agv_epoch", 0)),
        "job_epoch": int(getattr(pogema, "job_epoch", 0)),
        "events": _json(events),
        "event_metrics": _json(getattr(pogema, "event_metrics", {}) or {}),
        "blocked_cells": [list(cell) for cell in obstacles],
        "machines": machine_rows,
        "jobs": job_rows,
        "active_transfers": [_json(task) for task in getattr(pogema, "active_transfers", [])],
        "pending_transfers": [_json(task) for task in getattr(pogema, "transfers_to_assign", [])],
        "insertion_requests": deepcopy(list(env.job_insertions.snapshot()) if insertion_requests is None else insertion_requests),
    }
    frame["agvs"] = [{
        "id": int(agent.id), "pos": list(agent.pos),
        "status": getattr(agent, "status", "OK"),
        "task_phase": getattr(agent, "task_phase", "IDLE"),
        "handling_remaining": int(getattr(agent, "handling_remaining", 0) or 0),
        "loaded": bool(getattr(agent, "loaded", False)),
        "current_task": _json(getattr(agent, "current_task", None)),
    } for agent in agents]
    return _json(frame)


def serialize_action(action: dict[str, Any] | None) -> dict[str, Any]:
    """Serialize a native action without embedding mutable Pydantic objects."""
    return _json(action or {})


def build_runtime_frame(session, insertion_requests=None):
    """Read once after an immediate chain; every field uses that same committed state."""
    with session.env.read_state():
        return _build_runtime_frame(session, insertion_requests)
