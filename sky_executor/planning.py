"""Order release and validated changes to unexecuted production arrangements."""
from copy import deepcopy
from dataclasses import dataclass
import math

from sky_executor.events import FactoryEvent
from sky_executor.execution import ExecutionStatus
from sky_executor.perception.contracts import PlanningResult
from sky_executor.grid_factory.factory.material import initialize_job_material


class PlanRejected(ValueError):
    """An expected refusal, before a production arrangement is changed."""


def emit_event(env, kind, payload):
    env.record_factory_event(FactoryEvent(env.env_timeline, kind, payload))
    env.record_business_change(kind, payload)


def release_jobs(env, time):
    """Adopt one explicit release cutoff; reading/solving never advances it."""
    time = float(time)
    if not math.isfinite(time):
        return PlanningResult(False, "release time must be finite")
    with env.state_lock:
        state = env.state
        due = [job for job in state._future_jobs if job.release <= time]
        if not due:
            return PlanningResult(True, "no orders due for release")
        state._future_jobs = [job for job in state._future_jobs if job.release > time]
        state.jobs.extend(due)
        for job in due:
            for operation in job.ops:
                state.hash_operations[(job.job_id, operation.op_id)] = operation
            emit_event(env, "urgent_job_arrival" if job.priority >= 200 else "job_release",
                       {"job_id": job.job_id})
        state.job_epoch += 1
    return PlanningResult(True, "orders released")


def residual_problem(env, time):
    """Only observable processing estimates; repair truth stays in the scene."""
    state = env.state
    now = float(time)
    locked = {(job.job_id, op.op_id) for job in state.jobs for op in job.ops
              if op.status in {"PROCESSING", "SUSPENDED", "FINISHED"}}
    locked.update(record.operation_key for record in env.machine_runtime.execution_records.values()
                  if not record.business_settled)
    for agent_id, task in enumerate(state.agv_current_task):
        if task is None:
            continue
        records = env.agv_runtime.cancellation_records({agent_id})
        busy = any(record.execution_status is not None and (
            env.scene_adapter.agv_binding.cancel_simulation_requests is None
            or record.execution_status is ExecutionStatus.COMPLETED) for record in records)
        if state.agv_loaded[agent_id] or busy:
            locked.add((task.job_id, task.op_id))
    ready = []
    estimates = {}
    for machine in state.machines:
        finish = now
        current = machine.current_op
        if current is not None:
            nominal = current.nominal_proc_time or current.proc_time
            finish += max(0., float(nominal) - current.processed_time)
            estimates[(current.job_id, current.op_id)] = finish
        ready.append(finish)
    jobs = []
    for job in state.jobs:
        pending = [op for op in job.ops if (job.job_id, op.op_id) not in locked]
        if not pending:
            continue
        source = state.hash_machines.get(job.material_location)
        jobs.append({"job_id": job.job_id, "priority": job.priority, "due": job.due,
                     "request_id": job.request_id,
                     "ready_time": estimates.get((job.job_id, pending[0].op_id - 1), now),
                     "from_machine": source.id if source else -1,
                     "material_location": job.material_location, "carrier_id": job.carrier_id,
                     "operations": [{"op_id": op.op_id, "alternatives": [
                         {"machine": mid, "processing": duration} for mid, duration in op.machine_options_with_time
                     ]} for op in pending]})
    return {"current_step": now, "machines": len(state.machines), "machine_ready_times": ready,
            "machine_status": [machine.status for machine in state.machines], "jobs": jobs}


@dataclass(frozen=True)
class PlanChange:
    cancelled: frozenset
    released: frozenset
    queues: dict
    records: tuple
    new_jobs: tuple


def prepare_change(env, action, new_jobs=()):
    """Validate the whole edit against current facts, without mutating them."""
    if not isinstance(action, dict):
        raise PlanRejected("reschedule must be an object")
    state = env.state
    try:
        cancelled = frozenset(tuple(map(int, key)) for key in action.get("cancel_operations", ()))
        released = {int(agent) for agent in action.get("release_agvs", ())}
        queues = {int(mid): [tuple(map(int, key)) for key in keys]
                  for mid, keys in action.get("machine_queues", {}).items()}
    except (TypeError, ValueError, OverflowError, AttributeError) as error:
        raise PlanRejected("invalid reschedule fields") from error
    for key in cancelled:
        operation = state.hash_operations.get(key)
        if operation is None or operation.status != "PENDING":
            raise PlanRejected("only known unstarted operations may be cancelled")
        if any(record.operation_key == key and not record.business_settled
               for record in env.machine_runtime.execution_records.values()):
            raise PlanRejected("operation has an unfinished machine request")
    for agent_id, task in enumerate(state.agv_current_task):
        if task is not None and (task.job_id, task.op_id) in cancelled:
            released.add(agent_id)
    for agent_id in released:
        if not 0 <= agent_id < len(state.agv_current_task) or state.agv_current_task[agent_id] is None:
            raise PlanRejected("release_agvs requires a vehicle with a current task")
        if state.agv_loaded[agent_id]:
            raise PlanRejected("a loaded workpiece must remain on its current vehicle")
    machines = {machine.id: machine for machine in state.machines}
    for mid, keys in queues.items():
        if mid not in machines:
            raise PlanRejected("unknown machine queue")
        current = {(op.job_id, op.op_id) for op in machines[mid].input_queue} - cancelled
        if len(keys) != len(set(keys)) or set(keys) != current:
            raise PlanRejected("machine_queues must permute the remaining input queue")
    records = env.agv_runtime.cancellation_records(released)
    for record in records:
        if record.execution_status is ExecutionStatus.COMPLETED:
            raise PlanRejected("completed movement still requires position confirmation")
        if record.execution_status is not None and env.scene_adapter.agv_binding.cancel_simulation_requests is None:
            raise PlanRejected("independent device has an unfinished action")
    owned = deepcopy(tuple(new_jobs))
    ids = [job.job_id for job in owned]
    if len(ids) != len(set(ids)) or set(ids).intersection(job.job_id for job in state._all_jobs):
        raise PlanRejected("new job identifiers must be unique")
    try:
        for job in owned:
            if not math.isfinite(float(job.release)):
                raise ValueError("job release must be finite")
            initialize_job_material(state, job)
    except (TypeError, ValueError) as error:
        raise PlanRejected(str(error)) from error
    return PlanChange(cancelled, frozenset(released), queues, records, owned)


def apply_change(env, action, new_jobs=()):
    """Serialize preflight, simulated cancellation and core commit in one chain."""
    if not action and not new_jobs:
        return PlanningResult(True, "no plan adjustment")
    with env.state_lock:
        try:
            change = prepare_change(env, action, new_jobs)
        except PlanRejected as error:
            return PlanningResult(False, str(error))
    sent = tuple(record.request.request_id for record in change.records if record.execution_status is not None)
    if sent:
        # The caller holds processing_lock, but no state lock across device calls.
        env.scene_adapter.cancel_simulation_requests(sent)
    with env.state_lock:
        state = env.state
        env.agv_runtime.cancel_records(change.records)
        for agent_id in change.released:
            task = state.agv_current_task[agent_id]
            job = next(job for job in state.jobs if job.job_id == task.job_id)
            job.transport_task_id = None
            task.assigned_agent_id = None
            task.assign_time = task.pickup_start_time = -1
            state.agv_current_task[agent_id] = None
            state._set_agv_phase(agent_id, "IDLE")
            state.grid.finishes_xy[agent_id] = state.grid.positions_xy[agent_id]
            state.active_transfers.remove(task)
            if (task.job_id, task.op_id) not in change.cancelled:
                state.transfers_to_assign.append(task)
        for name in ("pending_transfers", "buffered_tasks", "transfers_to_assign"):
            setattr(state, name, [task for task in getattr(state, name)
                                 if (task.job_id, task.op_id) not in change.cancelled])
        for machine in state.machines:
            machine.input_queue = [op for op in machine.input_queue
                                   if (op.job_id, op.op_id) not in change.cancelled]
            machine.urgent_reservations.difference_update(change.cancelled)
        for key in change.cancelled:
            op = state.hash_operations[key]
            op.assigned_machine = op.assigned_robot = op.assigned_node = None
            op.arrive_machine_at = -1
        machines = {machine.id: machine for machine in state.machines}
        for mid, keys in change.queues.items():
            machines[mid].input_queue = [state.hash_operations[key] for key in keys]
        state._all_jobs.extend(change.new_jobs)
        state._future_jobs.extend(change.new_jobs)
        # A fleet request may include unaffected vehicles: preserve their moves.
        for record in change.records:
            request = record.request
            if request.kind == "move":
                actions = tuple(0 if agent in change.released else value
                                for agent, value in zip(request.agv_ids, request.actions))
                if any(actions):
                    env.agv_runtime.request_movement(request.agv_ids, actions)
        if action:
            state.reschedule_count += 1
            state.reassigned_operation_count += len(change.cancelled)
            state.reassigned_transport_count += len(change.released)
            emit_event(env, "reschedule_applied", {"cancel_operations": sorted(change.cancelled),
                "release_agvs": sorted(change.released), "machine_queues": change.queues})
        if change.new_jobs:
            state.job_epoch += 1
    if change.new_jobs:
        env.configure_operation_profiles(change.new_jobs)
        release_jobs(env, env.scene_adapter.planning_time())
    return PlanningResult(True, "production arrangement updated")
