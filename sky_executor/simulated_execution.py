"""Reusable simulated device implementations; no core business settlement."""
from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace
from sky_executor.execution import AgvRequest, AgvExecutionUpdate, ExecutionStatus, MachineRequest, MachineExecutionUpdate
from sky_executor.grid_factory.factory.Utils.processing_time import ProcessingTimeSampler


class SimulatedAgvExecutor:
    """Own dwell progress and fault effects; the driver explicitly advances each tick.

    predict computes a detached Pogema movement batch. No business objects are
    passed to this executor, and a completed movement does not commit positions.
    """
    def __init__(self, predict, *, pickup_dwell_steps=2, dropoff_dwell_steps=2, dropoff_admission=None):
        self._predict = predict
        self._durations = {"pickup": pickup_dwell_steps, "dropoff": dropoff_dwell_steps}
        self._handling = {}
        self._movements = {}
        self._faults = set()
        self._dropoff_admission = dropoff_admission

    def _completion(self, request):
        if request.kind == "dropoff" and self._dropoff_admission is not None and not self._dropoff_admission(request):
            return ExecutionStatus.DEFERRED
        return ExecutionStatus.COMPLETED

    def submit(self, request: AgvRequest) -> AgvExecutionUpdate:
        if request.kind == "move":
            self._movements[request.request_id] = request
            return AgvExecutionUpdate(request.request_id, ExecutionStatus.ACCEPTED)
        if request.kind not in ("pickup", "dropoff"):
            return AgvExecutionUpdate(request.request_id, ExecutionStatus.FAILED,
                                      reason="unsupported action")
        if request.agv_ids[0] in self._faults:
            return AgvExecutionUpdate(request.request_id, ExecutionStatus.FAILED,
                                      reason="AGV is unavailable")
        duration = self._durations[request.kind]
        if duration == 0:
            return AgvExecutionUpdate(request.request_id, self._completion(request))
        self._handling[request.request_id] = (request, duration)
        return AgvExecutionUpdate(request.request_id, ExecutionStatus.ACCEPTED, remaining=duration)

    def advance(self, request_ids):
        execution_updates = []
        for request_id in request_ids:
            if request_id in self._movements:
                request = self._movements[request_id]
                actions = tuple(0 if agv_id in self._faults else action
                                for agv_id, action in zip(request.agv_ids, request.actions))
                positions = tuple(self._predict(actions))
                del self._movements[request_id]
                execution_updates.append(AgvExecutionUpdate(
                    request_id, ExecutionStatus.COMPLETED, positions=positions))
                continue
            request, remaining = self._handling[request_id]
            if request.agv_ids[0] in self._faults:
                continue
            remaining -= 1
            status = ExecutionStatus.RUNNING if remaining else self._completion(request)
            execution_updates.append(AgvExecutionUpdate(
                request_id, status, remaining=remaining))
            if remaining:
                self._handling[request_id] = (request, remaining)
            else:
                del self._handling[request_id]
        return tuple(execution_updates), frozenset(update.request_id for update in execution_updates)

    def cancel_requests(self, request_ids):
        """Discard unconsumed moves/dwell work; never undo completed positions."""
        for request_id in request_ids:
            if request_id in self._movements:
                del self._movements[request_id]
            else:
                del self._handling[request_id]

    def inject_fault(self, agv_id, reason):
        from sky_executor.perception.contracts import AgvAvailabilityObservation
        self._faults.add(agv_id)
        return AgvAvailabilityObservation(agv_id, "DOWN", reason)

    def clear_fault(self, agv_id):
        from sky_executor.perception.contracts import AgvAvailabilityObservation
        self._faults.discard(agv_id)
        return AgvAvailabilityObservation(agv_id, "OK")

    def reset(self):
        self._handling.clear()
        self._movements.clear()
        self._faults.clear()

    def close(self):
        self.reset()


@dataclass
class SimulatedWork:
    request: MachineRequest
    duration: float
    distribution: dict | None
    elapsed: float = 0
    paused: bool = False
    finished: bool = False


class SimulatedMachineExecutor:
    """Own sampled durations and progress; the scene owns virtual time and faults."""
    def __init__(self, processing_time_config=None):
        self.sampler = ProcessingTimeSampler.from_config(processing_time_config)
        self._operation_profiles = {}
        self._diagnostics = {}
        self._work = {}
        self._faults = set()

    def _update(self, request_id, status, work):
        return MachineExecutionUpdate(
            request_id, status, elapsed=work.elapsed,
            remaining=max(0, work.duration - work.elapsed),
            duration=work.duration,
        )

    def submit(self, request):
        if request.kind == 'start':
            if request.machine_id in self._faults:
                return MachineExecutionUpdate(request.request_id, ExecutionStatus.FAILED,
                                              reason='machine is unavailable')
            parameters = request.processing
            duration, distribution = self.sampler.sample_for_operation(
                SimpleNamespace(job_id=parameters.job_id, op_id=parameters.op_id,
                    processing_time_config=self._operation_profiles.get((parameters.job_id, parameters.op_id))),
                request.machine_id, parameters.nominal_time)
            work = SimulatedWork(request, duration, distribution)
            self._work[request.request_id] = work
            self._diagnostics[request.request_id] = deepcopy(distribution)
            return self._update(request.request_id, ExecutionStatus.RUNNING, work)
        work = self._work[request.target_request_id]
        self._diagnostics[request.request_id] = deepcopy(work.distribution)
        if not work.finished:
            if request.kind == 'pause':
                work.paused = True
            elif request.kind == 'resume':
                work.paused = False
        return self._update(request.request_id, ExecutionStatus.COMPLETED, work)

    def advance(self, request_ids):
        updates = []
        for request_id in request_ids:
            work = self._work[request_id]
            if work.paused or work.finished or work.request.machine_id in self._faults:
                continue
            work.elapsed += min(1.0, max(0.0, work.duration - work.elapsed))
            if work.elapsed >= work.duration:
                work.finished = True
            status = ExecutionStatus.COMPLETED if work.finished else ExecutionStatus.RUNNING
            updates.append(self._update(request_id, status, work))
        return tuple(updates), frozenset(update.request_id for update in updates)

    def configure_operations(self, profiles):
        self._operation_profiles.update(deepcopy(profiles))

    def configure_seed(self, seed):
        self.sampler.reset(seed)

    def diagnostics(self, request_id):
        return deepcopy(self._diagnostics.get(request_id))

    def inject_fault(self, machine_id, reason):
        from sky_executor.perception.contracts import MachineAvailabilityObservation
        self._faults.add(machine_id)
        return MachineAvailabilityObservation(machine_id, 'DOWN', reason)

    def clear_fault(self, machine_id):
        from sky_executor.perception.contracts import MachineAvailabilityObservation
        self._faults.discard(machine_id)
        return MachineAvailabilityObservation(machine_id, 'OK')

    def reset(self):
        self.sampler.reset()
        self._work.clear()
        self._operation_profiles.clear()
        self._diagnostics.clear()
        self._faults.clear()

    def close(self):
        self.reset()
