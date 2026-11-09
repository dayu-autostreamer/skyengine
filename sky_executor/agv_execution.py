"""AGV request identity, occupancy and report correlation."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from uuid import uuid4

from sky_executor.execution import (
    AgvRequest, ExecutionStatus, ExecutionUpdateResult,
)


@dataclass
class ExecutionRecord:
    request: AgvRequest
    task_key: tuple | None = None
    handling_phase: str | None = None
    execution_status: ExecutionStatus | None = None
    business_settled: bool = False
    cancelled: bool = False
    last_sequence: int = -1
    movement_basis: tuple = ()


class AgvExecutionRuntime:
    """Register commands and correlate reports; no device or scene operations."""
    def __init__(self, state):
        self.state = state
        self.execution_records = {}
        self.active_handling_requests = {}
        self._requests_to_dispatch = deque()
        self.closed = False

    def require_running(self):
        if self.closed:
            raise RuntimeError("AGV execution is closed; full reset required")

    def request_handling(self, intent):
        from sky_executor.grid_factory.factory.business import _require_handling_position, routing_task_key
        agent_id = intent.agv_id
        phase = "PICKING" if intent.kind == "pickup" else "DROPPING"
        task = _require_handling_position(self.state, agent_id, phase)
        if (task is None or agent_id in self.active_handling_requests
                or self.movement_for(agent_id) is not None):
            return
        request = AgvRequest(uuid4().hex, intent.kind, (agent_id,))
        self.execution_records[request.request_id] = ExecutionRecord(request, routing_task_key(task), phase)
        self.active_handling_requests[agent_id] = request.request_id
        self._requests_to_dispatch.append(request)

    def take_requests(self):
        requests = tuple(self._requests_to_dispatch)
        self._requests_to_dispatch.clear()
        return requests

    def movement_for(self, agv_id):
        return next((record for record in self.execution_records.values()
                     if record.request.kind == "move" and not record.business_settled and not record.cancelled
                     and any(device_id == agv_id and action != 0
                             for device_id, action in zip(record.request.agv_ids, record.request.actions))), None)

    def request_movement(self, agv_ids, actions):
        if any(record.request.kind == "move" and not record.business_settled and not record.cancelled
               and set(record.request.agv_ids).intersection(agv_ids)
               for record in self.execution_records.values()):
            return None
        if any(agv_id in self.active_handling_requests and action != 0
               for agv_id, action in zip(agv_ids, actions)):
            return None
        request = AgvRequest(uuid4().hex, "move", tuple(agv_ids), tuple(actions))
        from sky_executor.grid_factory.factory.business import agv_action_basis
        basis = tuple(agv_action_basis(self.state.agv_current_task[i], self.state.agv_task_phase[i],
                      self.state._to_public_xy(self.state.grid.positions_xy[i])) for i in agv_ids)
        self.execution_records[request.request_id] = ExecutionRecord(request, movement_basis=basis)
        self._requests_to_dispatch.append(request)
        return request.request_id

    def accepted_movement_records(self):
        return tuple(record for record in self.execution_records.values()
                     if record.request.kind == "move" and record.execution_status is ExecutionStatus.ACCEPTED
                     and not record.business_settled and not record.cancelled)

    def apply_execution_report(self, report):
        from sky_executor.grid_factory.factory.business import _require_handling_position, routing_task_key
        update = report.fact
        record = self.execution_records.get(update.request_id)
        if record is None:
            return ExecutionUpdateResult(False, "unknown or obsolete request"), None
        if record.cancelled:
            return ExecutionUpdateResult(False, "execution request was cancelled"), None
        if record.business_settled or record.execution_status in (ExecutionStatus.COMPLETED, ExecutionStatus.DEFERRED):
            return ExecutionUpdateResult(False, "execution already completed"), None
        if report.sequence <= record.last_sequence:
            return ExecutionUpdateResult(False, "duplicate or late execution update"), None
        if update.status is ExecutionStatus.DEFERRED and record.request.kind != "dropoff":
            return ExecutionUpdateResult(False, "only dropoff may be deferred"), None
        if record.request.kind != "move":
            agent_id = record.request.agv_ids[0]
            task = self.state.agv_current_task[agent_id]
            if task is None or routing_task_key(task) != record.task_key:
                return ExecutionUpdateResult(False, "task mismatch"), None
        if update.status is ExecutionStatus.FAILED:
            record.execution_status = update.status
            raise RuntimeError(update.reason or "execution failed")
        if record.request.kind != "move" and _require_handling_position(
                self.state, record.request.agv_ids[0], record.handling_phase) is None:
            return ExecutionUpdateResult(False, "handling is not currently eligible"), None
        record.execution_status = update.status
        record.last_sequence = report.sequence
        return ExecutionUpdateResult(True, "execution update adopted"), record

    def mark_settled(self, record):
        record.business_settled = True
        if record.request.kind != "move":
            self.active_handling_requests.pop(record.request.agv_ids[0])

    def release_deferred_handling(self, record):
        self.active_handling_requests.pop(record.request.agv_ids[0])

    def settle_confirmed_movements(self, reports):
        confirmed = {}
        for report in reports:
            if report.movement_request_id is not None:
                confirmed.setdefault(report.movement_request_id, set()).add(report.fact.agv_id)
        settled_ids = []
        for request_id, agv_ids in confirmed.items():
            record = self.execution_records.get(request_id)
            if (record is not None and record.request.kind == "move" and not record.business_settled and not record.cancelled
                    and record.execution_status is ExecutionStatus.COMPLETED
                    and set(record.request.agv_ids) <= agv_ids):
                self.mark_settled(record)
                settled_ids.append(request_id)
        return tuple(settled_ids)

    def diagnostics(self, failure=None):
        return {"failure": str(failure) if failure else None,
            "requests": tuple({"request_id": record.request.request_id,
                "kind": record.request.kind, "agv_ids": record.request.agv_ids,
                "execution_status": record.execution_status.value if record.execution_status else "commanded",
                "settled": record.business_settled, "cancelled": record.cancelled, "task_key": record.task_key}
                for record in self.execution_records.values())}

    def cancellation_records(self, agv_ids):
        """Find owned requests affected by releasing these vehicles."""
        return tuple(record for record in self.execution_records.values()
            if not record.cancelled and not record.business_settled
            and record.execution_status is not ExecutionStatus.DEFERRED
            and (any(i in agv_ids and action != 0 for i, action in
                     zip(record.request.agv_ids, record.request.actions))
                 if record.request.kind == "move" else record.request.agv_ids[0] in agv_ids))

    def cancel_records(self, records):
        ids = {record.request.request_id for record in records}
        for record in records:
            record.cancelled = True
            if record.request.kind != "move":
                self.active_handling_requests.pop(record.request.agv_ids[0], None)
        self._requests_to_dispatch = deque(request for request in self._requests_to_dispatch
                                           if request.request_id not in ids)

    def close(self):
        self.closed = True

    def reset(self):
        self.closed = False
        self.execution_records.clear()
        self.active_handling_requests.clear()
        self._requests_to_dispatch.clear()
