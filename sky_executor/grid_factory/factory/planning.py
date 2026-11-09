"""JSON planning view containing observations and public distribution priors only."""
from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
from .Utils.processing_time import normalize_processing_config, resolve_processing_distribution


def planning_snapshot(public: dict, task: dict, processing_config: dict, failure_priors: dict, material: dict) -> dict:
    config = normalize_processing_config(processing_config)
    jobs: list[dict] = []
    for job in public["jobs"]:
        value: dict = asdict(job)
        for source, operation in zip(job.ops, value["ops"]):
            operation["transfer_requested"] = source.transfer_requested
            operation["distributions"] = {
                str(mid): deepcopy(resolve_processing_distribution(config, source, mid)) if config["enabled"] else None
                for mid, _ in source.machine_options_with_time
            }
        jobs.append(value)
    machines: list[dict] = [{
        "id": machine.id, "location": list(machine.location), "status": machine.status,
        "down_elapsed": machine.down_elapsed, "buffer_capacity": machine.buffer_capacity,
        "buffer_jobs": sorted(machine.buffer_jobs),
        "current_op": None if machine.current_op is None else [machine.current_op.job_id, machine.current_op.op_id],
        "input_queue": [[op.job_id, op.op_id] for op in machine.input_queue],
        "suspended_ops": [[op.job_id, op.op_id] for op in machine.suspended_ops],
        "urgent_reservations": sorted(machine.urgent_reservations),
    } for machine in public["machines"]]
    priors = deepcopy(failure_priors)
    return {
        "time": task["env_timeline"], "jobs": jobs, "machines": machines,
        "agents": [agent.dict(exclude={"finished_tasks", "repair_remaining"}) for agent in public["agents"]],
        "tasks": [item.dict() for name in ("pending_transfers", "buffered_transfers", "active_transfers") for item in public[name]],
        "ready_task_ids": [item.task_id for item in public["pending_transfers"]],
        "grid": task["obstacle_grid"].tolist(), "moves": task["move_deltas"],
        "events": deepcopy(task.get("events", [])), "failure_priors": priors,
        "pickup_steps": int(material.get("pickup_dwell_steps", 2)),
        "dropoff_steps": int(material.get("dropoff_dwell_steps", 2)),
    }
