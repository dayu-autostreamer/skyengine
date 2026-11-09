"""Core order admission and production-plan application, independent of scene I/O."""
from collections import deque
from copy import deepcopy

from sky_executor.grid_factory.factory.Utils.structure import Job, Operation
from sky_executor.perception.contracts import JobInsertionResult


class JobInsertions:
    """One owner for pending requests, frontend phases and insertion statistics."""
    def __init__(self, env):
        self.env = env
        self.on_phase_change = None
        self.reset()

    def reset(self):
        self.records = {}
        self.pending_requests = deque()
        self.processed_sequences = {}
        self.plan_revision = 0
        self.metrics = dict(inserted_jobs_completed=0, job_replan_count=0,
                            job_replan_failed=0, job_replan_latency_ms=0., urgent_response_time=0.)

    def _public_record(self, record):
        return {key: deepcopy(value) for key, value in record.items() if not key.startswith("_")}

    def snapshot(self):
        return tuple(self._public_record(record) for record in self.records.values())

    def _phase(self, record, phase, **fields):
        record.update(fields)
        record["phase"] = phase
        record["timeline"].append({"phase": phase, "step": self.env.env_timeline})
        if self.on_phase_change is not None:
            self.on_phase_change(self._public_record(record))

    def _late(self, report):
        return report.sequence <= self.processed_sequences.get((report.source, report.fact.request_id), -1)

    def receive(self, report):
        request = report.fact
        with self.env.state_lock:
            if request.request_id in self.records or self._late(report):
                return JobInsertionResult(False, "duplicate insertion request", request.request_id)
            if self.env._order_admission_closed:
                return JobInsertionResult(False, "order admission is closed after completion", request.request_id)
            base = self.env.state
            proposed = [job["job_id"] for job in request.jobs]
            owned = {job.job_id for job in base._all_jobs}
            owned.update(job_id for record in self.records.values()
                         if record["phase"] in {"queued", "replanning"} for job_id in record["job_ids"])
            if not proposed or len(set(proposed)) != len(proposed) or owned.intersection(proposed):
                return JobInsertionResult(False, "empty or conflicting job identifiers", request.request_id)
            record = dict(request_id=request.request_id, accepted_step=request.accepted_step,
                          inserted=deepcopy(list(request.inserted)), rejected=deepcopy(list(request.rejected)),
                          job_ids=proposed, timeline=[], revision=None, latency_ms=None, error=None,
                          _jobs=deepcopy(request.jobs))
            self.records[request.request_id] = record
            self.pending_requests.append(request.request_id)
            self.processed_sequences[(report.source, request.request_id)] = report.sequence
            self._phase(record, "queued")
            return JobInsertionResult(True, "insertion queued for the next decision", request.request_id, "queued")

    def next_request(self):
        while self.pending_requests and self.records[self.pending_requests[0]]["phase"] != "queued":
            self.pending_requests.popleft()
        if not self.pending_requests:
            return None
        return deepcopy(self.records[self.pending_requests[0]])

    def apply(self, report):
        update = report.fact
        with self.env.state_lock:
            if self._late(report):
                return JobInsertionResult(False, "duplicate or late planning update", update.request_id)
            record = self.records.get(update.request_id) if update.request_id is not None else None
            if update.request_id is not None:
                if record is None:
                    return JobInsertionResult(False, "unknown or obsolete insertion", update.request_id)
                expected = "queued" if update.phase == "replanning" else "replanning"
                if record["phase"] != expected:
                    return JobInsertionResult(False, "insertion is not in the required phase", update.request_id, record["phase"])
            elif update.phase != "scheduled" or update.new_jobs:
                return JobInsertionResult(False, "recovery reports can only apply a residual plan", None)
            if update.phase == "scheduled" and record is not None and [job.job_id for job in update.new_jobs] != record["job_ids"]:
                return JobInsertionResult(False, "planned jobs do not match the insertion request", update.request_id, record["phase"])
            if update.phase not in {"scheduled", "replanning", "failed"}:
                return JobInsertionResult(False, "unknown planning phase", update.request_id)
        if update.phase == "scheduled":
            applied = self._install(update.new_jobs, update.replanned_keys)
            if not applied.applied:
                return JobInsertionResult(False, applied.reason, update.request_id,
                                          record["phase"] if record else None)
        with self.env.state_lock:
            if update.phase == "scheduled":
                self.plan_revision += 1
                if not update.new_jobs:
                    self.env.state.job_epoch += 1
                if record is not None:
                    self.metrics["job_replan_count"] += 1
                    self.metrics["job_replan_latency_ms"] += update.latency_ms
                    self._phase(record, "scheduled", revision=self.plan_revision, latency_ms=update.latency_ms)
            elif update.phase == "replanning":
                self._phase(record, "replanning")
                record.pop("_jobs")
            else:
                self.metrics["job_replan_failed"] += 1
                self._phase(record, "failed", error=update.reason, latency_ms=update.latency_ms)
            self.processed_sequences[(report.source, update.request_id)] = report.sequence
            return JobInsertionResult(True, "planning update applied", update.request_id, update.phase)

    def _install(self, new_jobs, replanned_keys):
        existing = [key for key in replanned_keys if key in self.env.state.hash_operations]
        return self.env.apply_reschedule({"cancel_operations": existing}, new_jobs)

    def refresh_execution_phases(self):
        base = self.env.state
        active = {(task.job_id, task.op_id) for task in base.active_transfers}
        jobs = {job.job_id: job for job in base._all_jobs}
        order = {"scheduled": 0, "transporting": 1, "processing": 2, "completed": 3}
        for record in self.records.values():
            if record["phase"] not in order or record["phase"] == "completed":
                continue
            tracked = [jobs[job_id] for job_id in record["job_ids"]]
            if all(job.is_completed for job in tracked):
                target = "completed"
            elif any(operation.start_process_at >= 0 for job in tracked for operation in job.ops):
                target = "processing"
            elif any((job.job_id, operation.op_id) in active for job in tracked for operation in job.ops):
                target = "transporting"
            else:
                continue
            if order[target] <= order[record["phase"]]:
                continue
            for phase in ("transporting", "processing", "completed"):
                if order[record["phase"]] < order[phase] <= order[target]:
                    self._phase(record, phase)
            if target == "completed":
                self.metrics["inserted_jobs_completed"] += len(tracked)
                self.metrics["urgent_response_time"] += max(0, self.env.env_timeline - record["accepted_step"])


def build_replan_problem(env, now, new_jobs):
    """Build one observable residual problem and proposed, uninstalled orders."""
    from sky_executor.planning import residual_problem
    now = float(now)
    problem = residual_problem(env, now)
    problem_jobs = problem["jobs"]
    materialized = []
    for item in new_jobs:
        ops = []
        for op_id, alternatives in enumerate(item["operations"]):
            pairs = [(int(alt["machine"]), float(alt["processing"])) for alt in alternatives]
            ops.append(Operation(
                job_id=item["job_id"], op_id=op_id,
                machine_options=[mid for mid, _ in pairs], machine_options_with_time=pairs,
                proc_time=min(pt for _, pt in pairs), nominal_proc_time=min(pt for _, pt in pairs),
                release=now, due=item["due"], priority=item["priority"],
                request_id=item["request_id"],
            ))
        job = Job(job_id=item["job_id"], ops=ops, release=now, due=item["due"],
                  priority=item["priority"], name=item["name"], request_id=item["request_id"],
                  raw_material_source=item.get("raw_material_source"),
                  finished_goods_destination=item.get("finished_goods_destination"))
        materialized.append(job)
        problem_jobs.append(problem_job(job, ops, now, -1))
    return problem, materialized


def problem_job(job, operations, ready_time, from_machine):
    serialized_operations = []
    for operation in operations:
        options = operation.machine_options_with_time
        if not options:
            options = [(operation.assigned_machine, operation.proc_time)]
        serialized_operations.append({
            "op_id": operation.op_id,
            "alternatives": [{"machine": int(machine_id), "processing": float(duration)}
                             for machine_id, duration in options],
        })
    return {
        "job_id": job.job_id, "ready_time": ready_time, "from_machine": from_machine,
        "priority": job.priority, "due": job.due, "request_id": job.request_id,
        "operations": serialized_operations,
    }
