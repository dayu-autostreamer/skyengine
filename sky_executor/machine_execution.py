"""Machine request identity, occupancy and report correlation."""
from collections import deque
from dataclasses import dataclass
from uuid import uuid4

from sky_executor.execution import (
    ExecutionStatus, ExecutionUpdateResult, MachineRequest,
    ProcessingParameters,
)


@dataclass
class MachineExecutionRecord:
    request: MachineRequest
    operation_key: tuple[int, int]
    execution_status: ExecutionStatus | None = None
    business_settled: bool = False
    last_sequence: int = -1
    reported_work: float = 0
    segment_start: float = 0


class MachineExecutionRuntime:
    """Manage request identity and occupancy; business projection stays outside."""
    def __init__(self, state):
        self.state = state
        self.execution_records = {}
        self.processing_requests = {}
        self._requests_to_dispatch = deque()
        self.closed = False

    def require_running(self):
        if self.closed:
            raise RuntimeError("machine execution is closed; full reset required")

    def request_processing(self, intent):
        machine_id = intent.machine_id
        if intent.kind == "pause":
            request_id = self.processing_requests.get(machine_id)
            if request_id is not None:
                return self._request_control("pause", self.execution_records[request_id])
            return
        if machine_id in self.processing_requests:
            return
        operation = self.state.hash_operations[intent.operation_key]
        suspended_record = next((record for record in self.execution_records.values()
            if record.request.kind == "start" and not record.business_settled
            and record.operation_key == intent.operation_key), None)
        if suspended_record is not None:
            self._request_control("resume", suspended_record)
            self.processing_requests[machine_id] = suspended_record.request.request_id
            return
        nominal = operation.nominal_proc_time or operation.proc_time
        request = MachineRequest(uuid4().hex, "start", machine_id,
            processing=ProcessingParameters(operation.job_id, operation.op_id, nominal))
        self.execution_records[request.request_id] = MachineExecutionRecord(request, intent.operation_key)
        self.processing_requests[machine_id] = request.request_id
        self._requests_to_dispatch.append(request)

    def _request_control(self, kind, processing_record):
        target = processing_record.request.request_id
        existing = next((record.request.request_id for record in self.execution_records.values()
            if record.request.kind == kind and not record.business_settled
            and record.request.target_request_id == target), None)
        if existing is not None:
            return existing
        request = MachineRequest(uuid4().hex, kind, processing_record.request.machine_id, target_request_id=target)
        self.execution_records[request.request_id] = MachineExecutionRecord(request, processing_record.operation_key)
        self._requests_to_dispatch.append(request)
        return request.request_id

    def take_requests(self):
        requests = tuple(self._requests_to_dispatch)
        self._requests_to_dispatch.clear()
        return requests

    def apply_execution_report(self, report):
        update = report.fact
        record = self.execution_records.get(update.request_id)
        if record is None:
            return ExecutionUpdateResult(False, "unknown or obsolete machine request"), None
        if record.business_settled:
            return ExecutionUpdateResult(False, "machine request already settled"), None
        if update.status is ExecutionStatus.DEFERRED:
            return ExecutionUpdateResult(False, "machine execution cannot use dropoff deferral"), None
        if report.sequence <= record.last_sequence:
            return ExecutionUpdateResult(False, "duplicate or late machine update"), None
        if record.request.kind != "start" and self.execution_records[record.request.target_request_id].business_settled:
            record.business_settled = True
            return ExecutionUpdateResult(False, "processing already completed"), None
        machine = next(m for m in self.state.machines if m.id == record.request.machine_id)
        operation = self.state.hash_operations[record.operation_key]
        if machine.current_op is not operation and not (record.request.kind == "start" and operation in machine.suspended_ops):
            return ExecutionUpdateResult(False, "processing operation mismatch"), None
        if update.status is ExecutionStatus.FAILED:
            record.execution_status = update.status
            raise RuntimeError(update.reason or "machine execution failed")
        if record.request.kind == "start":
            if operation.status == "SUSPENDED":
                return ExecutionUpdateResult(False, "processing is suspended"), None
            if update.elapsed is not None and update.elapsed < record.reported_work:
                return ExecutionUpdateResult(False, "processing progress is older than confirmed work"), None
        record.execution_status = update.status
        record.last_sequence = report.sequence
        return ExecutionUpdateResult(True, "machine update adopted"), record

    def mark_settled(self, record):
        record.business_settled = True
        if record.request.kind in ("start", "pause"):
            self.processing_requests.pop(record.request.machine_id, None)

    def diagnostics(self, failure=None):
        return {"failure": str(failure) if failure else None,
            "requests": tuple({"request_id": record.request.request_id, "kind": record.request.kind,
                "machine_id": record.request.machine_id, "operation": record.operation_key,
                "execution_status": record.execution_status.value if record.execution_status else "commanded",
                "settled": record.business_settled} for record in self.execution_records.values())}

    def reset(self):
        self.closed = False
        self.execution_records.clear()
        self.processing_requests.clear()
        self._requests_to_dispatch.clear()

    def close(self):
        self.closed = True
