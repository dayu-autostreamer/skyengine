"""Callable business boundaries over the existing factory environment state.

Decision preparation, confirmed business settlement and movement/time statistics
share the existing environment objects without owning physical device state.
"""

from __future__ import annotations

from sky_executor.events import FactoryEvent
from sky_executor.execution import HandlingIntent, MachineIntent, ExecutionStatus

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Collection, Sequence

from sky_executor.grid_factory.factory.Utils.structure import Machine, RoutingTask
from sky_executor.perception.contracts import (
    AgvAvailabilityObservation,
    AgvObservation,
    CommitResult,
    FactChangeKind,
    MachineAvailabilityObservation,
)

if TYPE_CHECKING:
    from sky_executor.grid_factory.factory.assign_env import PogemaLifeLongWithAssign

AGV_PHASE_IDLE = "IDLE"
AGV_PHASE_TO_PICKUP = "TO_PICKUP"
AGV_PHASE_PICKING = "PICKING"
AGV_PHASE_TO_DROPOFF = "TO_DROPOFF"
AGV_PHASE_DROPPING = "DROPPING"
HANDLING_PHASES = {AGV_PHASE_PICKING, AGV_PHASE_DROPPING}


class SettlementTrigger(str, Enum):
    """Reason for one non-time-consuming settlement call."""

    FACT = "fact"
    DECISION = "decision"
    EXECUTION = "execution"


@dataclass(frozen=True, slots=True)
class SettlementEntity:
    """Stable reference to one entity affected by settlement."""

    kind: str
    identifier: int | tuple[int, int]


@dataclass(frozen=True, slots=True)
class SettlementResult:
    """Summary of one settlement call, without a persistent event history."""

    trigger: SettlementTrigger
    changed: bool
    affected_entities: tuple[SettlementEntity, ...]
    reason: str
    execution_intents: tuple[HandlingIntent | MachineIntent, ...] = ()


def routing_task_key(task: RoutingTask) -> tuple[int, int, int]:
    """Identify a task without adopting a snapshot's mutable object."""
    return task.job_id, task.op_id, task.task_id


@dataclass(frozen=True, slots=True)
class AgvTimingBasis:
    """Only the task, phase and availability needed to account for one round."""

    task_key: tuple[int, int, int] | None
    phase: str
    status: str


@dataclass(frozen=True, slots=True)
class AgvActionBasis:
    """Task context of a movement command, independent of its timing basis."""

    task_key: tuple[int, int, int] | None
    phase: str
    target: tuple[int, int] | None
    origin: tuple[int, int] | None = None


def agv_action_basis(task: RoutingTask | None, phase: str, origin=None) -> AgvActionBasis:
    target = None
    if task is not None:
        target = task.source if phase in {AGV_PHASE_TO_PICKUP, AGV_PHASE_PICKING} else task.destination
    return AgvActionBasis(
        routing_task_key(task) if task is not None else None,
        phase, tuple(target) if target is not None else None,
        tuple(origin) if origin is not None else None,
    )


def _handling_task(state, agent_id: int, phase_at_step_start: str) -> RoutingTask | None:
    """Return the task eligible for this handling phase and time boundary."""
    if phase_at_step_start not in HANDLING_PHASES or state.agv_status[agent_id] != "OK":
        return None
    transfer = state.agv_current_task[agent_id]
    if transfer is None or state.agv_task_phase[agent_id] != phase_at_step_start:
        return None
    return transfer


def _require_handling_position(
    state, agent_id: int, phase_at_step_start: str
) -> RoutingTask | None:
    """Raise before handling time changes when the committed position is wrong."""
    transfer = _handling_task(state, agent_id, phase_at_step_start)
    if transfer is None:
        return None
    expected = (
        transfer.source
        if phase_at_step_start == AGV_PHASE_PICKING
        else transfer.destination
    )
    actual = tuple(state._to_public_xy(state.grid.positions_xy[agent_id]))
    expected = tuple(expected) if expected is not None else None
    if actual != expected:
        raise RuntimeError(
            f"AGV {agent_id} cannot advance {phase_at_step_start}: "
            f"current position {actual}, expected position {expected}"
        )
    return transfer


def prepare_transfer(state, task: RoutingTask) -> RoutingTask:
    """Normalize the physical pickup source independently of solver conventions."""
    job = next((job for job in state.jobs if job.job_id == task.job_id), None)
    if job is not None and job.material_location is not None:
        task.source = job.material_location
    task.pickup_required = True
    return task


def check_physical_precondition(state, task: RoutingTask) -> bool:
    """Transport is ready once its preceding operation has finished."""
    job = next((job for job in state.jobs if job.job_id == task.job_id), None)
    if (job is None or task.ready_time > state.env_timeline
            or job.carrier_id is not None or job.transport_task_id is not None):
        return False
    if task.op_id > 0 and job.ops[task.op_id - 1].status != "FINISHED":
        return False
    source = state.hash_machines.get(job.material_location)
    at_raw_source = task.op_id == 0 and job.ops[0].arrive_machine_at < 0 and job.material_location == job.raw_material_source
    return at_raw_source or source is None or job.job_id in source.buffer_jobs


def enqueue_operation(state, transfer: RoutingTask, target_machine: Machine) -> None:
    """Place an arrived operation on its machine, with or without an AGV."""
    hash_op = (transfer.job_id, transfer.op_id)
    real_op = state.hash_operations[hash_op]
    real_op.arrive_machine_at = state.env_timeline
    real_op.assigned_machine = target_machine.id
    target_machine.buffer_jobs.add(transfer.job_id)

    # 解析 machine_options_with_time 获取机器实际加工时间
    if real_op.machine_options_with_time:
        for mid, pt in real_op.machine_options_with_time:
            if mid == target_machine.id:
                real_op.nominal_proc_time = pt
                real_op.proc_time = pt
                real_op.sampled_proc_time = None
                real_op.processing_time_distribution = None
                break
    # 如果 machine_options_with_time 为空，保持原 proc_time 不变

    # 放入机器的 input_queue
    target_machine.input_queue.append(real_op)
    target_machine.urgent_reservations.discard((transfer.job_id, transfer.op_id))

    # 激活休眠机器
    if target_machine.id not in [m.id for m in state.activated_machines]:
        state.activated_machines.append(target_machine)


def refresh_ready_tasks(
    state, tasks: Sequence[RoutingTask]
) -> tuple[RoutingTask, ...]:
    """Refresh only the selected buffered task objects."""
    selected = {id(task) for task in tasks}
    still_buffered = []
    changed = []
    for task in state.buffered_tasks:
        if id(task) not in selected:
            still_buffered.append(task)
            continue
        prepare_transfer(state, task)
        if not check_physical_precondition(state, task):
            still_buffered.append(task)
        elif task.kind == "operation" and task.source == task.destination and task.destination in state.hash_machines:
            machine = state.hash_machines[task.destination]
            if task.job_id not in machine.buffer_jobs and len(machine.buffer_jobs) >= machine.buffer_capacity:
                still_buffered.append(task)
                continue
            enqueue_operation(state, task, machine)
            changed.append(task)
        else:
            state.transfers_to_assign.append(task)
            changed.append(task)
    state.buffered_tasks = still_buffered
    return tuple(changed)


class DecisionApplier:
    """Validate and apply requests, assignments and core preparation policy."""

    def __init__(self, state: PogemaLifeLongWithAssign) -> None:
        self._state = state

    def resolve_transfer(self, t: dict) -> RoutingTask:
        """Resolve explicit machine references; coordinates always remain coordinates."""
        state = self._state
        fields = deepcopy(t)
        machines = {machine.id: machine for machine in state.machines}
        for field in ("source", "destination"):
            machine_id = fields.pop(field + "_machine_id", None)
            if machine_id is not None:
                machine_id = int(machine_id)
                if machine_id not in machines:
                    raise ValueError(f"unknown {field} machine id: {machine_id}")
                fields[field] = machines[machine_id].location
        return RoutingTask(**fields)

    def resolve_job_request(self, request: object) -> object:
        """Parse one JobSolver request without receiving or assigning it."""
        if isinstance(request, dict):
            return self.resolve_transfer(request)
        if isinstance(request, RoutingTask):
            return deepcopy(request)
        return request

    def replace_job_requests(self, requests: list[RoutingTask]) -> None:
        """Stage parsed requests; receiving and settlement are separate calls."""
        self._state.pending_transfers = requests

    def receive_task_requests(
        self, action: dict
    ) -> tuple[tuple[RoutingTask, ...], dict[int, RoutingTask | None]]:
        """Receive parsed requests and match Assigner references to owned tasks.

        Only pending_transfers can introduce tasks. Assigner values already
        use business coordinates and must never pass through job parsing.
        """
        state = self._state
        tasks_by_key = {}
        tasks_by_id = {}
        for task in (
            *state.buffered_tasks, *state.transfers_to_assign,
            *state.active_transfers, *state.agv_current_task,
        ):
            if task is not None:
                key = routing_task_key(task)
                if key in tasks_by_key and tasks_by_key[key] is not task:
                    raise RuntimeError(f"ambiguous environment task key: {key}")
                if task.task_id in tasks_by_id and tasks_by_id[task.task_id] is not task:
                    raise RuntimeError(f"ambiguous environment task id: {task.task_id}")
                tasks_by_key[key] = task
                tasks_by_id[task.task_id] = task
        finished = {routing_task_key(task) for tasks in state.agv_finished_tasks for task in tasks}
        new_requests = []
        destination_updates = []
        requested_operations = {(task.job_id, task.op_id) for task in tasks_by_key.values()}
        for task in state.pending_transfers:
            key = routing_task_key(task)
            if key in finished:
                raise ValueError(f"request references a completed task: {key}")
            operation_key = (task.job_id, task.op_id)
            if task.kind != "operation" or task.task_id < 0 or task.task_id in tasks_by_id or operation_key in requested_operations:
                raise ValueError("duplicate or invalid production transfer")
            operation = state.hash_operations.get(operation_key)
            if operation is None:
                raise ValueError(f"unknown operation: {operation_key}")
            if operation.status != "PENDING" or operation.assigned_machine is not None:
                raise ValueError("operation already started or has a committed transfer")
            if task.destination is not None:
                machine = state.hash_machines.get(tuple(task.destination))
                eligible = operation.machine_options or [mid for mid, _ in operation.machine_options_with_time or ()]
                if machine is None or machine.id not in eligible:
                    raise ValueError("transfer destination is not an eligible machine")
            tasks_by_key[key] = task
            tasks_by_id[task.task_id] = task
            requested_operations.add(operation_key)
            new_requests.append(task)

        def match_reference(request, field):
            if isinstance(request, RoutingTask):
                fields = request.dict()
                destination = request.destination
            elif isinstance(request, dict):
                fields = request
                destination = request.get("destination")
            elif type(request) is int:
                fields = {"task_id": request}
                destination = None
            else:
                raise TypeError(f"{field} must reference task ids, RoutingTask values or dictionaries")
            task_id = fields.get("task_id")
            if type(task_id) is not int:
                raise ValueError(f"invalid task reference in {field}: {fields}")
            key = tuple(fields.get(name) for name in ("job_id", "op_id", "task_id"))
            if key in finished:
                raise ValueError(f"completed task reference in {field}: {key}")
            if task_id not in tasks_by_id:
                if any(key[2] == task_id for key in finished):
                    raise ValueError(f"completed task reference in {field}: {task_id}")
                raise ValueError(f"unknown task reference in {field}: {task_id}")
            task = tasks_by_id[task_id]
            if any(name in fields and (type(fields[name]) is not int or fields[name] != getattr(task, name))
                   for name in ("job_id", "op_id")):
                raise ValueError(f"invalid task reference in {field}: {key}")
            if task.destination is None and destination is not None:
                destination_updates.append((task, tuple(destination)))
            return task

        assignments = {}
        for agent_id, request in action.get("assignments", {}).items():
            if type(agent_id) is not int or not 0 <= agent_id < len(state.agv_status):
                raise ValueError(f"unknown AGV id: {agent_id}")
            assignments[agent_id] = (
                None if request is None else match_reference(request, f"assignments[{agent_id}]")
            )
        remaining = [match_reference(task, "pending_transfers") for task in action.get("pending_transfers", ())]

        # Reorder ready tasks only. Selection is not successful assignment.
        ready_keys = {routing_task_key(task) for task in state.transfers_to_assign}
        waiting = []
        for task in (*remaining, *state.transfers_to_assign):
            key = routing_task_key(task)
            if key in ready_keys:
                waiting.append(task)
                ready_keys.remove(key)
        for task, destination in destination_updates:
            if task.destination is None:
                task.destination = destination
        for task in new_requests:
            if task.create_time < 0:
                task.create_time = state.env_timeline
        state.buffered_tasks.extend(new_requests)
        state.transfers_to_assign = waiting
        state.pending_transfers = []
        state._assigned_this_step.clear()
        return tuple(new_requests), assignments

    def assign_transfer(self, agent_id: int, transfer: RoutingTask) -> int:
        """Write an assignment; the caller separately settles arrival."""
        state = self._state
        transfer = prepare_transfer(state, transfer)
        job = next(job for job in state.jobs if job.job_id == transfer.job_id)
        job.transport_task_id = transfer.task_id
        transfer.assign_time = state.env_timeline
        transfer.assigned_agent_id = agent_id
        state.agv_current_task[agent_id] = transfer
        state._assigned_this_step.add(agent_id)
        if transfer not in state.active_transfers:
            state.active_transfers.append(transfer)
        if transfer.pickup_required:
            state.agv_loaded[agent_id] = False
            state._set_agv_phase(agent_id, AGV_PHASE_TO_PICKUP)
            state._set_agv_target(agent_id, transfer.source)
        else:
            state.agv_loaded[agent_id] = True
            state._set_agv_phase(agent_id, AGV_PHASE_TO_DROPOFF)
            state._set_agv_target(agent_id, transfer.destination)
        return agent_id

    def apply_assignment(self, agent_id: int, transfer: RoutingTask | None) -> int | None:
        """Apply only to an available, idle AGV; retain the random-target option."""
        state = self._state
        if state.agv_status[agent_id] != "OK" or state.agv_current_task[agent_id] is not None:
            return None
        if state.random_target:
            if state.grid_config.possible_targets_xy:
                state.grid.finishes_xy[agent_id] = state._to_internal_xy(
                    state._rng.choice(state.grid_config.possible_targets_xy)
                )
            return None
        if transfer is None:
            return None
        return self.assign_transfer(agent_id, transfer)

    def apply_requested_assignments(
        self, assignments: dict[int, RoutingTask | None]
    ) -> tuple[int, ...]:
        """Assign ready tasks once; unavailable AGVs leave their tasks waiting."""
        state = self._state
        selected = set()
        jobs = set()
        for agent_id, task in assignments.items():
            if task is None:
                continue
            if not any(item is task for item in state.transfers_to_assign):
                raise ValueError("assignment references a non-ready task")
            if (task.task_id in selected or task.job_id in jobs
                    or state.agv_current_task[agent_id] is not None
                    or any(current is not None and current.job_id == task.job_id
                           for current in state.agv_current_task)):
                raise ValueError("transport tasks, workpieces and AGVs must have a single owner")
            selected.add(task.task_id)
            jobs.add(task.job_id)
        assigned = []
        for agent_id in sorted(assignments):
            task = assignments[agent_id]
            if task is None:
                continue
            if self.apply_assignment(agent_id, task) is not None:
                state.transfers_to_assign = [item for item in state.transfers_to_assign if item is not task]
                assigned.append(agent_id)
        return tuple(assigned)

    def constrain_agent_actions(
        self, actions: Sequence[int], observed: Sequence[AgvActionBasis],
        assigned_agv_ids: Sequence[int], invalid_agv_ids: Collection[int] = (),
    ) -> list[int]:
        """Restrict existing commands; never generate movement from a new target."""
        state = self._state
        return [
            0 if (
                observed[agent_id].phase in HANDLING_PHASES
                or state.agv_task_phase[agent_id] in HANDLING_PHASES
                or state.agv_status[agent_id] != "OK"
                or agent_id in assigned_agv_ids
                or agent_id in invalid_agv_ids
            ) else action
            for agent_id, action in enumerate(actions)
        ]

    def invalidated_actions(self, observed: Sequence[AgvActionBasis]) -> tuple[int, ...]:
        """Check only the task context of each original movement command."""
        state = self._state
        return tuple(
            agent_id for agent_id, basis in enumerate(observed)
            if agv_action_basis(state.agv_current_task[agent_id], state.agv_task_phase[agent_id],
                                state._to_public_xy(state.grid.positions_xy[agent_id])) != basis
        )

    def prepare_requested_tasks(self, tasks):
        """Apply input policy and readiness; this is not completion settlement."""
        intents = []
        for task in tasks:
            intent = self.reserve_for_urgent_transfer(task)
            if intent is not None:
                intents.append(intent)
            refresh_ready_tasks(self._state, (task,))
        return tuple(intents)

    def refresh_buffered_tasks(self, *, include_finished_goods=True):
        return refresh_ready_tasks(self._state, tuple(task for task in self._state.buffered_tasks
            if include_finished_goods or task.kind != "finished_goods"))

    def reserve_for_urgent_transfer(self, task):
        state = self._state
        if task.priority < 200:
            return
        machine = state.hash_machines.get(task.destination)
        if machine is None:
            return
        machine.urgent_reservations.add((task.job_id, task.op_id))
        operation = machine.current_op
        intent = None
        if operation is not None and operation.priority < 200 and operation.status == "PROCESSING":
            intent = MachineIntent(machine.id, (operation.job_id, operation.op_id), "pause")
        if machine not in state.activated_machines:
            state.activated_machines.append(machine)
        return intent

    def select_machine_operation(self, machine_id):
        """Reserve the next operation using core priority and preemption policy."""
        state = self._state
        machine = next(m for m in state.machines if m.id == machine_id)
        if machine.status != "OK":
            return None
        if machine.current_op is not None:
            return None
        if machine.urgent_reservations and not any(op.priority >= 200 for op in machine.input_queue):
            return None
        if machine.input_queue:
            index = max(range(len(machine.input_queue)), key=lambda i: machine.input_queue[i].priority)
            operation = machine.input_queue.pop(index)
        elif machine.suspended_ops:
            operation = machine.suspended_ops[0]
        else:
            if machine in state.activated_machines:
                state.activated_machines.remove(machine)
            return None
        machine.current_op = operation
        operation.assigned_machine = machine.id
        state.machine_process_time[machine_id] = 0
        return operation

    def prepare_machine_work(self, machine_ids):
        """Select new work without dispatching devices or advancing time."""
        intents = []
        for machine_id in dict.fromkeys(machine_ids):
            operation = self.select_machine_operation(machine_id)
            if operation is not None:
                intents.append(MachineIntent(machine_id, (operation.job_id, operation.op_id)))
        return tuple(intents)


class BusinessSettler:
    """Apply business consequences of confirmed facts and execution results."""

    def __init__(self, state: PogemaLifeLongWithAssign, record_event=None) -> None:
        self._state = state
        self._record_event = record_event or (lambda event: None)

    def _event(self, kind, payload):
        self._record_event(FactoryEvent(self._state.env_timeline, kind, payload))

    def _machine(self, machine_id: int) -> Machine:
        return next(machine for machine in self._state.machines if machine.id == machine_id)

    @staticmethod
    def _result(
        trigger: SettlementTrigger,
        changed: bool,
        entities: Sequence[SettlementEntity],
        reason: str,
        execution_intents=(),
    ) -> SettlementResult:
        return SettlementResult(
            trigger,
            changed,
            tuple(dict.fromkeys(entities)),
            reason,
            tuple(execution_intents),
        )

    @staticmethod
    def _task_entities(task: RoutingTask) -> tuple[SettlementEntity, ...]:
        if task.kind == "finished_goods":
            return (SettlementEntity("task", task.task_id), SettlementEntity("job", task.job_id))
        return (
            SettlementEntity("task", task.task_id),
            SettlementEntity("operation", (task.job_id, task.op_id)),
        )

    def _settle_agv(self, agent_id: int):
        """Settle arrival and all eligible zero-time transitions for one AGV."""
        state = self._state
        if state.agv_status[agent_id] != "OK":
            return (), ()
        task = state.agv_current_task[agent_id]

        def business_signature():
            return (
                state.agv_current_task[agent_id], state.agv_task_phase[agent_id],
                state.agv_handling_remaining[agent_id], state.agv_loaded[agent_id],
                None if task is None else (
                    task.pickup_start_time, task.pickup_finish_time,
                    task.dropoff_start_time, task.finish_time,
                ),
            )

        before = business_signature()
        intents = self.settle_arrival(agent_id)
        if business_signature() == before:
            return (), intents
        affected = [SettlementEntity("agv", agent_id)]
        if task is not None:
            affected.extend(self._task_entities(task))
            if state.agv_current_task[agent_id] is None:
                machine = state.hash_machines.get(task.destination)
                if machine is not None:
                    affected.append(SettlementEntity("machine", machine.id))
        return tuple(affected), intents

    def settle_after_fact_commit(self, commit_result: CommitResult) -> SettlementResult:
        """Apply direct business consequences of one successful fact commit."""
        if not commit_result.applied:
            return self._result(
                SettlementTrigger.FACT,
                False,
                (),
                f"fact was not committed: {commit_result.reason}",
            )

        state = self._state
        fact = commit_result.report.fact
        changed = False
        affected: list[SettlementEntity] = []
        intents = []
        if isinstance(fact, AgvObservation):
            position_event = next(
                (
                    event
                    for event in commit_result.events
                    if event.kind is FactChangeKind.POSITION
                ),
                None,
            )
            if position_event is not None:
                changed = True
                affected.append(SettlementEntity("agv", fact.agv_id))

            settled, new_intents = self._settle_agv(fact.agv_id)
            intents.extend(new_intents)
            if settled:
                changed = True
                affected.extend(settled)

        elif isinstance(fact, AgvAvailabilityObservation):
            if fact.status == "OK":
                reason_before = state.agv_down_reason[fact.agv_id]
                repair_before = state.agv_repair_remaining[fact.agv_id]
                state.agv_down_reason[fact.agv_id] = None
                state.agv_repair_remaining[fact.agv_id] = 0
                settled, new_intents = self._settle_agv(fact.agv_id)
                intents.extend(new_intents)
                changed = reason_before is not None or repair_before != 0 or bool(settled)
                if changed:
                    affected.append(SettlementEntity("agv", fact.agv_id))
                    affected.extend(settled)

        elif isinstance(fact, MachineAvailabilityObservation):
            if fact.status == "OK":
                machine = self._machine(fact.machine_id)
                changed = (
                    getattr(machine, "down_reason", None) is not None
                    or getattr(machine, "repair_remaining", 0) != 0
                )
                machine.down_reason = None
                machine.repair_remaining = 0
                if changed:
                    affected.append(SettlementEntity("machine", fact.machine_id))

        reason = (
            "fact settlement changed derived state"
            if changed
            else "fact has no direct business settlement"
        )
        return self._result(SettlementTrigger.FACT, changed, affected, reason, intents)

    def settle_after_assignment(self, *, assigned_agv_ids=()) -> SettlementResult:
        """Apply only the arrival consequences of successful assignments."""
        affected = []
        intents = []
        for agent_id in assigned_agv_ids:
            changed, new_intents = self._settle_agv(agent_id)
            affected.extend(changed)
            intents.extend(new_intents)
        return self._result(SettlementTrigger.DECISION, bool(affected), affected,
                            "assignment arrival settled" if affected else "no assignment arrival", intents)

    def confirm_machine_started(self, operation):
        changed = operation.status != "PROCESSING"
        if operation.start_process_at < 0:
            operation.start_process_at = self._state.env_timeline
        operation.status = "PROCESSING"
        machine = self._machine(operation.assigned_machine)
        machine.buffer_jobs.discard(operation.job_id)
        if changed:
            self._event("operation_started", {"job_id": operation.job_id, "op_id": operation.op_id,
                                               "machine_id": machine.id})

    def confirm_machine_paused(self, machine_id, operation, remaining):
        state = self._state
        machine = self._machine(machine_id)
        operation.accumulated_process_time = operation.processed_time
        operation.remaining_proc_time = remaining
        operation.preemption_count += 1
        operation.status = "SUSPENDED"
        machine.suspended_ops.append(operation)
        machine.current_op = None
        state.machine_process_time[machine_id] = 0

    def confirm_machine_resumed(self, machine_id, operation, remaining):
        machine = self._machine(machine_id)
        machine.suspended_ops.remove(operation)
        if remaining is not None:
            operation.proc_time = float(remaining)
        operation.remaining_proc_time = None
        self._state.machine_process_time[machine_id] = 0
        self.confirm_machine_started(operation)

    def _finish_machine_business(self, machine_id):
        state = self._state
        machine = self._machine(machine_id)
        current_op = machine.current_op
        operation = state.hash_operations[(current_op.job_id, current_op.op_id)]
        operation.finish_process_at = state.env_timeline
        operation.status = "FINISHED"
        operation.accumulated_process_time = operation.processed_time
        machine.processed_ops_count += 1
        machine.history_ops.append((
            operation.job_id, operation.op_id,
            operation.start_process_at, operation.finish_process_at,
        ))
        self._event("operation_completed", {"job_id": operation.job_id, "op_id": operation.op_id,
                                              "machine_id": machine.id})
        self.release_finished_operation(machine_id)
        return operation

    def release_finished_operation(self, machine_id):
        """Move an already completed workpiece out of the processing slot, without time."""
        state = self._state
        machine = self._machine(machine_id)
        operation = machine.current_op
        if machine.status != "OK" or operation is None or operation.status != "FINISHED":
            return False
        if len(machine.buffer_jobs) >= machine.buffer_capacity:
            machine.buffer_blocked_steps += 1
            return False
        machine.buffer_jobs.add(operation.job_id)
        machine.current_op = None
        state.machine_process_time[machine.id] = 0
        job = next(job for job in state.jobs if job.job_id == operation.job_id)
        if operation.op_id == len(job.ops) - 1:
            task = RoutingTask(task_id=state._shipping_sequence, job_id=job.job_id,
                op_id=len(job.ops), kind="finished_goods", source=job.material_location,
                destination=job.finished_goods_destination, ready_time=operation.finish_process_at,
                priority=job.priority, create_time=operation.finish_process_at)
            state._shipping_sequence -= 1
            state.buffered_tasks.append(task)
        return True

    def settle_material_changes(self, machine_ids):
        """Reconsider only affected machine ports; no device work or clock advancement."""
        affected = []
        intents = []
        locations = set()
        for machine_id in dict.fromkeys(machine_ids):
            machine = self._machine(machine_id)
            locations.add(machine.location)
            if self.release_finished_operation(machine_id):
                affected.append(SettlementEntity("machine", machine_id))
        for task in refresh_ready_tasks(self._state, tuple(self._state.buffered_tasks)):
            affected.extend(self._task_entities(task))
        for agent_id, task in enumerate(self._state.agv_current_task):
            if task is not None and task.destination in locations and self._state.agv_task_phase[agent_id] == AGV_PHASE_TO_DROPOFF:
                changed, new_intents = self._settle_agv(agent_id)
                affected.extend(changed)
                intents.extend(new_intents)
        return self._result(SettlementTrigger.EXECUTION, bool(affected), affected, "material availability checked", intents)

    def settle_machine_completion(self, machine_id, *, refresh_finished_goods=True):
        operation = self._finish_machine_business(machine_id)
        affected = [SettlementEntity("machine", machine_id),
                    SettlementEntity("operation", (operation.job_id, operation.op_id)),
                    SettlementEntity("job", operation.job_id)]
        tasks = tuple(task for task in self._state.buffered_tasks if task.job_id == operation.job_id
                      and (refresh_finished_goods or task.kind != "finished_goods"))
        for task in refresh_ready_tasks(self._state, tasks):
            affected.extend(self._task_entities(task))
            machine = self._state.hash_machines.get(task.destination)
            if machine is not None and task.source == task.destination:
                affected.append(SettlementEntity("machine", machine.id))
        return self._result(SettlementTrigger.EXECUTION, True, affected, "machine completion settled")

    def finish_pickup(self, agent_idx: int, transfer: RoutingTask) -> None:
        state = self._state
        job = next(job for job in state.jobs if job.job_id == transfer.job_id)
        source = state.hash_machines.get(job.material_location)
        if source is not None:
            source.buffer_jobs.discard(job.job_id)
        job.material_location = None
        job.carrier_id = agent_idx
        transfer.pickup_finish_time = state.env_timeline
        state.agv_loaded[agent_idx] = True
        state._set_agv_phase(agent_idx, AGV_PHASE_TO_DROPOFF)
        state._set_agv_target(agent_idx, transfer.destination)
        self._event("transport_picked_up", {"job_id": job.job_id, "task_id": transfer.task_id, "agv_id": agent_idx})

    def finish_dropoff(self, agent_idx: int, transfer: RoutingTask) -> bool:
        state = self._state
        if not self.deliver(agent_idx, transfer):
            return False
        state.agv_loaded[agent_idx] = False
        state._set_agv_phase(agent_idx, AGV_PHASE_IDLE)
        state.grid.finishes_xy[agent_idx] = state.grid.positions_xy[agent_idx]
        return True

    def settle_arrival(self, agent_idx):
        """Enter handling from committed position and return the required action."""
        state = self._state
        task = state.agv_current_task[agent_idx]
        if task is None or state.agv_status[agent_idx] != "OK":
            return ()
        phase = state.agv_task_phase[agent_idx]
        if phase in HANDLING_PHASES:
            return (HandlingIntent(agent_idx, "pickup" if phase == AGV_PHASE_PICKING else "dropoff"),)
        position = tuple(state.grid.positions_xy[agent_idx])
        if phase == AGV_PHASE_TO_PICKUP and position == state._to_internal_xy(task.source):
            task.pickup_start_time = state.env_timeline
            state._set_agv_phase(agent_idx, AGV_PHASE_PICKING)
            state._set_agv_target(agent_idx, task.source)
            return (HandlingIntent(agent_idx, "pickup"),)
        if phase == AGV_PHASE_TO_DROPOFF and position == state._to_internal_xy(task.destination):
            if task.kind == "operation" and task.destination not in state.hash_machines:
                raise RuntimeError("dropoff completion has no target machine")
            if not self.can_dropoff(task):
                state.hash_machines[task.destination].buffer_blocked_steps += 1
                return ()
            task.dropoff_start_time = state.env_timeline
            state._set_agv_phase(agent_idx, AGV_PHASE_DROPPING)
            state._set_agv_target(agent_idx, task.destination)
            return (HandlingIntent(agent_idx, "dropoff"),)
        return ()

    def apply_agv_execution(self, record, update):
        if record.request.kind == "move":
            return False, ()
        agent_id = record.request.agv_ids[0]
        task = _require_handling_position(self._state, agent_id, record.handling_phase)
        if update.status is ExecutionStatus.DEFERRED:
            if task.kind == "operation":
                self._state.hash_machines[task.destination].buffer_blocked_steps += 1
            self._state.agv_handling_remaining[agent_id] = 0
            self._state._set_agv_phase(agent_id, AGV_PHASE_TO_DROPOFF)
            return False, ()
        if update.status is not ExecutionStatus.COMPLETED:
            if update.remaining is not None:
                self._state.agv_handling_remaining[agent_id] = update.remaining
            return False, ()
        if record.request.kind == "pickup":
            self.finish_pickup(agent_id, task)
        elif not self.finish_dropoff(agent_id, task):
            raise RuntimeError("dropoff completion could not be settled")
        return True, self.settle_arrival(agent_id)

    def _project_machine_work(self, record, update, operation, machine, distribution):
        if update.elapsed is not None:
            machine.total_work_time += update.elapsed - record.reported_work
            record.reported_work = update.elapsed
        operation.processed_time = record.reported_work
        self._state.machine_process_time[machine.id] = record.reported_work - record.segment_start
        if update.duration is not None:
            operation.proc_time = update.duration - record.segment_start
            operation.sampled_proc_time = update.duration
            operation.processing_time_distribution = distribution
        nominal = operation.nominal_proc_time or 0
        if (update.status is ExecutionStatus.RUNNING and operation.status == "PROCESSING"
                and operation.processed_time >= nominal and not operation.deviation_reported):
            operation.deviation_reported = True
            self._event("processing_time_deviation", {"job_id": operation.job_id, "op_id": operation.op_id,
                                                      "elapsed_processing": operation.processed_time})

    def apply_machine_execution(self, record, update, processing_record, distribution, *, refresh_finished_goods=True):
        state = self._state
        machine = self._machine(record.request.machine_id)
        operation = state.hash_operations[record.operation_key]
        if record.request.kind == "start":
            if update.status is ExecutionStatus.ACCEPTED:
                return False, ()
            self._project_machine_work(record, update, operation, machine, distribution)
            freed_buffer = operation.job_id in machine.buffer_jobs
            self.confirm_machine_started(operation)
            if update.status is ExecutionStatus.COMPLETED:
                settlement = self.settle_machine_completion(machine.id, refresh_finished_goods=refresh_finished_goods)
                return True, tuple(entity.identifier for entity in settlement.affected_entities
                                   if entity.kind == "machine")
            return False, (machine.id,) if freed_buffer else ()
        if update.status is not ExecutionStatus.COMPLETED:
            return False, ()
        if record.request.kind == "pause":
            self._project_machine_work(processing_record, update, operation, machine, distribution)
            remaining = update.remaining if update.remaining is not None else max(0, operation.proc_time - state.machine_process_time[machine.id])
            self.confirm_machine_paused(machine.id, operation, remaining)
        else:
            remaining = update.remaining if update.remaining is not None else operation.remaining_proc_time
            processing_record.segment_start = update.elapsed if update.elapsed is not None else processing_record.reported_work
            self._project_machine_work(processing_record, update, operation, machine, distribution)
            self.confirm_machine_resumed(machine.id, operation, remaining)
        return True, (machine.id,) if record.request.kind == "pause" else ()

    def deliver(self, agent_idx: int, transfer) -> bool:
        """AGV 卸货: 将物料放入目标机器的 input_queue"""
        state = self._state
        # 用 transfer.destination 查找机器，不用 finishes_xy
        # 因为 pogema on_target="restart" 会自动将 finishes_xy 改为随机目标
        target_machine = state.hash_machines.get(transfer.destination, None)

        if transfer.kind == "finished_goods":
            job = next(job for job in state.jobs if job.job_id == transfer.job_id)
            job.delivered = True
            job.completion_time = state.env_timeline
            self._event("job_completed", {"job_id": job.job_id})
        elif target_machine is None:
            if state.debug_mode:
                print(
                    f"[WARNING] Agent {agent_idx} arrived at "
                    f"{transfer.destination} but no machine found."
                )
            return False

        else:
            if not self.can_dropoff(transfer):
                return False
            enqueue_operation(state, transfer, target_machine)
        job = next(job for job in state.jobs if job.job_id == transfer.job_id)
        job.material_location = transfer.destination
        job.carrier_id = job.transport_task_id = None
        transfer.finish_time = state.env_timeline

        # 记录任务完成
        state.agv_finished_tasks[agent_idx].append(transfer)
        if transfer in state.active_transfers:
            state.active_transfers.remove(transfer)
        state.agv_current_task[agent_idx] = None
        self._event("transport_completed", {"job_id": job.job_id, "task_id": transfer.task_id, "agv_id": agent_idx})
        return True

    def can_dropoff(self, task):
        if task.kind == "finished_goods":
            return True
        machine = self._state.hash_machines.get(task.destination)
        return machine is not None and len(machine.buffer_jobs) < machine.buffer_capacity


class BusinessStatistics:
    """Record committed distance and classify time for explicit simulation ticks."""

    def __init__(self, state: PogemaLifeLongWithAssign) -> None:
        self._state = state

    def record_position_changes(
        self,
        previous_positions: Sequence[tuple[int, int]],
        current_positions: Sequence[tuple[int, int]],
        *,
        agent_ids: Sequence[int] | None = None,
    ) -> tuple[int, ...]:
        """Record actual Manhattan movement without advancing business time."""
        state = self._state
        if not hasattr(state, "agv_stats"):
            state.agv_stats = {
                i: {
                    "dist": 0,
                    "loaded": 0,
                    "empty": 0,
                    "idle": 0,
                    "handling": 0,
                    "task_waiting": 0,
                }
                for i in range(state.grid_config.num_agents)
            }
        if len(previous_positions) != len(current_positions):
            raise ValueError("position lists must have the same length")
        ids = tuple(range(len(previous_positions))) if agent_ids is None else tuple(agent_ids)
        if len(ids) != len(previous_positions):
            raise ValueError("agent_ids must match the supplied position lists")
        changed: list[int] = []
        for agent_id, previous, current in zip(ids, previous_positions, current_positions):
            distance = abs(current[0] - previous[0]) + abs(current[1] - previous[1])
            if distance <= 0:
                continue
            state.agv_stats[agent_id]["dist"] += distance
            changed.append(agent_id)
        return tuple(changed)

    def timing_basis(self) -> tuple[AgvTimingBasis, ...]:
        """Freeze the current business state at the advancement boundary."""
        env = self._state
        return tuple(
            AgvTimingBasis(
                routing_task_key(task) if task is not None else None,
                env.agv_task_phase[agent_id], env.agv_status[agent_id],
            )
            for agent_id, task in enumerate(env.agv_current_task)
        )

    def record_agv_time(
        self, agent_id: int, basis: AgvTimingBasis, *, moved: bool,
        handling_advanced: bool | None = None, movement_loaded: bool | None = None,
    ) -> None:
        """Account for one authorized tick, using its basis rather than final state."""
        env = self._state
        if not hasattr(env, "agv_stats"):
            env.agv_stats = {
                i: {"dist": 0, "loaded": 0, "empty": 0, "idle": 0, "handling": 0, "task_waiting": 0}
                for i in range(env.grid_config.num_agents)
            }
        has_task = basis.task_key is not None
        handling = (
            basis.phase in HANDLING_PHASES and basis.status == "OK"
            if handling_advanced is None else handling_advanced
        )
        loaded = (
            has_task and basis.phase == AGV_PHASE_TO_DROPOFF
            if movement_loaded is None else movement_loaded
        )
        if handling:
            category = "handling"
        elif moved and loaded:
            category = "loaded"
        elif moved:
            category = "empty"
        elif has_task:
            category = "task_waiting"
        else:
            category = "idle"
        stats = env.agv_stats[agent_id]
        stats[category] = stats.get(category, 0) + 1
