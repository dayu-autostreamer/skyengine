"""Observable snapshots: simulator outcomes stay behind the environment boundary."""
from __future__ import annotations

from copy import copy, deepcopy


def observable_state(env) -> dict:
    requests = {(task.job_id, task.op_id): task
                for name in ("pending_transfers", "buffered_tasks", "transfers_to_assign", "active_transfers")
                for task in getattr(env, name) if task.kind == "operation"}
    jobs: list = []
    operations: dict = {}
    for source in env.jobs:
        job = copy(source)
        job.ops = []
        for original in source.ops:
            operation = deepcopy(original)
            task = requests.get((source.job_id, original.op_id))
            operation.transfer_requested = task is not None or original.assigned_machine is not None
            if task is not None and operation.assigned_machine is None:
                destination = env.hash_machines.get(task.destination)
                if destination is not None:
                    operation.assigned_machine = destination.id
            nominal = float(original.nominal_proc_time if original.nominal_proc_time is not None else original.proc_time)
            operation.remaining_proc_time = max(0.0, nominal - original.processed_time)
            if original.status != "FINISHED":
                operation.proc_time = nominal
                operation.sampled_proc_time = None
            else:
                operation.remaining_proc_time = 0.0
            job.ops.append(operation)
            operations[(job.job_id, operation.op_id)] = operation
        jobs.append(job)
    machines: list = []
    for source in env.machines:
        machine = copy(source)
        machine.repair_remaining = None
        machine.current_op = None if source.current_op is None else operations[(source.current_op.job_id, source.current_op.op_id)]
        machine.input_queue = [operations[(op.job_id, op.op_id)] for op in source.input_queue]
        machine.suspended_ops = [operations[(op.job_id, op.op_id)] for op in source.suspended_ops]
        machine.buffer_jobs = set(source.buffer_jobs)
        machine.history_ops = list(source.history_ops)
        machine.urgent_reservations = set(source.urgent_reservations)
        machines.append(machine)
    agents: list = env.get_agv_info()
    for agent in agents:
        agent.repair_remaining = None
        agent.current_task = deepcopy(agent.current_task)
        agent.finished_tasks = []
    return {"jobs": jobs, "machines": machines, "agents": agents,
            "pending_transfers": deepcopy(env.transfers_to_assign),
            "buffered_transfers": deepcopy(env.buffered_tasks),
            "active_transfers": deepcopy(env.active_transfers)}
