"""Formal DFJSP-T domain adapter backed by SkyEngine's live simulator."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import unquote, urlparse

from dataset.dfjsp_t.validate_schema import validate_instance
from experiment.algorithm_platform.events import hash_state
from experiment.algorithm_platform.models import (
    ArtifactKind,
    DomainEvent,
    DomainRef,
    RunContext,
    RunPurpose,
    ScenarioRef,
    StateSnapshot,
    StepResult,
    ValidationResult,
)
from experiment.algorithm_platform.serialization import to_jsonable
from sky_executor.runtime_log import build_runtime_frame, serialize_action
from sky_executor.session import SimulationSession
from sky_executor.grid_factory.factory.Component.RaceFMS.state import (
    RaceState,
    RaceStateEncoder,
)


DFJSPT_URGENT_PRIORITY = 200


@dataclass(frozen=True, slots=True)
class DFJSPTProblem:
    """An immutable source identity plus a private instance copy."""

    scenario_id: str
    scenario_digest: str
    _instance: Mapping[str, object] | None
    metadata: Mapping[str, object]
    corpus_instances: tuple[Mapping[str, object], ...] = ()

    @property
    def is_corpus(self) -> bool:
        return self._instance is None

    @property
    def instance(self) -> Mapping[str, object]:
        if self._instance is None:
            raise ValueError(
                "a corpus scenario cannot be executed as one online or batch instance"
            )
        return self._instance


@dataclass(frozen=True, slots=True)
class DFJSPTDataSplit:
    """Verified formal instances handed to a trainable algorithm."""

    name: str
    problems: tuple[DFJSPTProblem, ...]


class DFJSPTDomainAdapter:
    """Load versioned scenarios and create authoritative online sessions."""

    def __init__(self, reference: DomainRef):
        parameters = reference.parameters
        self._scenario_root = Path(
            str(parameters.get("scenario_root", Path.cwd()))
        ).resolve()
        self._route_solver = str(parameters.get("route_solver", "astar"))
        self._assigner = str(parameters.get("assigner", "nearest"))
        self._agent_observation_type = str(parameters.get("agent_observation_type", "default"))
        self._validation_scenarios = tuple(
            _scenario_ref(value)
            for value in parameters.get("validation_scenarios", ())
        )

    def load_problem(self, scenario: ScenarioRef) -> DFJSPTProblem:
        path, fragment = _scenario_path(self._scenario_root, scenario.uri)
        if bool(scenario.metadata.get("corpus", False)):
            if path.suffix.lower() != ".jsonl":
                raise ValueError("a DFJSP-T corpus scenario must reference JSONL")
            actual_digest = _file_sha256(path)
            expected_digest = scenario.digest.removeprefix("sha256:")
            if actual_digest != expected_digest:
                raise ValueError(
                    f"corpus digest mismatch for {scenario.scenario_id!r}: "
                    f"expected {expected_digest}, found {actual_digest}"
                )
            instances = _read_jsonl_corpus(
                path,
                tuple(
                    str(value)
                    for value in scenario.metadata.get("instance_ids", ())
                ),
            )
            return DFJSPTProblem(
                scenario_id=scenario.scenario_id,
                scenario_digest=f"sha256:{actual_digest}",
                _instance=None,
                metadata=copy.deepcopy(dict(scenario.metadata)),
                corpus_instances=tuple(
                    copy.deepcopy(instance) for instance in instances
                ),
            )
        if path.suffix.lower() == ".jsonl":
            instance_id = str(
                scenario.metadata.get(
                    "instance_id",
                    fragment or scenario.scenario_id,
                )
            )
            instance = _read_jsonl_instance(path, instance_id)
        else:
            instance = json.loads(path.read_text(encoding="utf-8"))

        validate_instance(instance)
        actual_digest = str(instance["canonical_hash"])
        expected_digest = scenario.digest.removeprefix("sha256:")
        if actual_digest != expected_digest:
            raise ValueError(
                f"scenario digest mismatch for {scenario.scenario_id!r}: "
                f"expected {expected_digest}, found {actual_digest}"
            )
        return DFJSPTProblem(
            scenario_id=scenario.scenario_id,
            scenario_digest=f"sha256:{actual_digest}",
            _instance=copy.deepcopy(instance),
            metadata=copy.deepcopy(dict(scenario.metadata)),
        )

    def create_session(
        self,
        problem: DFJSPTProblem,
        context: RunContext,
    ) -> "DFJSPTOnlineSession":
        if context.run.purpose is RunPurpose.VALIDATE and (
            str(problem.metadata.get("split", "")).lower() == "benchmark"
            or _contains_instance_split(problem, "benchmark")
        ):
            raise ValueError(
                "sealed benchmark instances cannot be used for parameter selection"
            )
        config = copy.deepcopy(dict(problem.instance))
        config["seed"] = context.run.seeds.environment
        if context.run.budget.max_steps is not None:
            # The explicit execution limit must also reach the inner simulator;
            # otherwise an evaluation can stop at the corpus's shorter limit.
            config["simulation_control"]["max_steps"] = context.run.budget.max_steps
        session = SimulationSession.from_config(
            config,
            native_actions=True,
            agent_observation_type=self._agent_observation_type,
            headless=True,
        )
        return DFJSPTOnlineSession(session, context, route_solver=self._route_solver, assigner=self._assigner)

    def validate_solution(
        self,
        problem: DFJSPTProblem,
        solution: object,
    ) -> ValidationResult:
        from .batch import validate_batch_solution

        return validate_batch_solution(problem.instance, solution)

    def evaluate_solution(
        self,
        problem: DFJSPTProblem,
        solution: Mapping[str, object],
    ) -> dict[str, float]:
        from .batch import evaluate_batch_solution

        return evaluate_batch_solution(problem.instance, solution)

    def load_training_data(
        self,
        problem: DFJSPTProblem,
        context: RunContext,
    ) -> DFJSPTDataSplit:
        if context.run.purpose is not RunPurpose.TRAIN:
            raise ValueError("training data may only be loaded by a train run")
        if str(problem.metadata.get("split", "")).lower() == "benchmark":
            raise ValueError("sealed benchmark instances cannot be used for training")
        if _contains_instance_split(problem, "benchmark"):
            raise ValueError("benchmark corpus content cannot be used for training")
        if problem.is_corpus and str(
            problem.metadata.get("split", "")
        ).lower() != "training":
            raise ValueError("a training corpus must declare split='training'")
        return DFJSPTDataSplit(
            name="training",
            problems=_expand_problem(problem),
        )

    def load_validation_data(
        self,
        problem: DFJSPTProblem,
        context: RunContext,
    ) -> DFJSPTDataSplit | None:
        del context
        if not self._validation_scenarios:
            return None
        validation_sources = tuple(
            self.load_problem(scenario)
            for scenario in self._validation_scenarios
        )
        if any(
            source.is_corpus
            and str(source.metadata.get("split", "")).lower()
            != "validation"
            for source in validation_sources
        ):
            raise ValueError(
                "a validation corpus must declare split='validation'"
            )
        validation = tuple(
            item
            for source in validation_sources
            for item in _expand_problem(source)
        )
        if any(
            str(item.metadata.get("split", "")).lower() == "benchmark"
            for item in validation
        ):
            raise ValueError(
                "sealed benchmark instances cannot be used for model selection"
            )
        if any(
            _contains_instance_split(item, "benchmark")
            for item in validation
        ):
            raise ValueError(
                "benchmark corpus content cannot be used for model selection"
            )
        training_digests = {
            item.scenario_digest for item in _expand_problem(problem)
        }
        if training_digests.intersection({
            item.scenario_digest for item in validation
        }):
            raise ValueError(
                "validation instances must be disjoint from training instances"
            )
        return DFJSPTDataSplit(name="validation", problems=validation)

    def load_evaluation_data(
        self,
        problem: DFJSPTProblem,
        context: RunContext,
    ) -> DFJSPTDataSplit:
        if context.run.purpose is RunPurpose.TRAIN:
            validation = self.load_validation_data(problem, context)
            if validation is not None:
                return validation
        if context.run.purpose is RunPurpose.VALIDATE and (
            str(problem.metadata.get("split", "")).lower() == "benchmark"
            or _contains_instance_split(problem, "benchmark")
        ):
            raise ValueError(
                "sealed benchmark instances cannot be used for model selection"
            )
        return DFJSPTDataSplit(
            name="evaluation",
            problems=_expand_problem(problem),
        )


class DFJSPTOnlineSession:
    """JSON-facing scheduling session over one formal SimulationSession."""

    def __init__(self, session: SimulationSession, context: RunContext, *, route_solver: str = "astar", assigner: str = "nearest"):
        self._session = session
        self._context = context
        self._route_solver = route_solver
        self._assigner = assigner
        self._environment_seed = context.run.seeds.environment
        self._task_sequence = 0
        self._action_history: list[dict[str, object]] = []
        self._state_encoder = RaceStateEncoder()

    @property
    def simulation_time(self) -> float:
        return float(self._session.env.pogema_env.env_timeline)

    @property
    def state_version(self) -> int:
        return int(self._session.step_index)

    @property
    def terminated(self) -> bool:
        return bool(self._session.done)

    def reset(self) -> dict[str, object]:
        self._session.reset(seed=self._environment_seed)
        self._task_sequence = 0
        self._action_history.clear()
        return self.observe()

    def observe(self) -> dict[str, object]:
        frame = build_runtime_frame(self._session)
        pogema = self._session.env.pogema_env
        jobs = []
        for job in self._session.obs["job_observation"]["jobs"]:
            jobs.append(
                {
                    "job_id": int(job.job_id),
                    "release": float(job.release),
                    "due": None if job.due is None else float(job.due),
                    "priority": int(job.priority),
                    "request_id": job.request_id,
                    "completion_time": float(job.completion_time),
                    "is_completed": bool(job.is_completed),
                    "operations": [
                        {
                            "op_id": int(operation.op_id),
                            "status": str(operation.status),
                            "assigned_machine": operation.assigned_machine,
                            "nominal_processing_time": float(
                                operation.nominal_proc_time
                                if operation.nominal_proc_time is not None
                                else operation.proc_time
                            ),
                            "remaining_processing_time": (
                                None
                                if operation.remaining_proc_time is None
                                else float(operation.remaining_proc_time)
                            ),
                            "machine_options": [
                                {
                                    "machine_id": int(machine_id),
                                    "processing_time": float(processing_time),
                                }
                                for machine_id, processing_time in (
                                    operation.machine_options_with_time or ()
                                )
                            ],
                            "preemption_count": int(operation.preemption_count),
                        }
                        for operation in job.ops
                    ],
                }
            )

        machines = []
        for machine in self._session.obs["job_observation"]["machines"]:
            machines.append(
                {
                    "machine_id": int(machine.id),
                    "location": list(machine.location),
                    "status": str(machine.status),
                    "down_elapsed": int(machine.down_elapsed),
                    "current_operation": _operation_key(machine.current_op),
                    "current_remaining_time": _current_remaining_time(
                        machine,
                        pogema.machine_process_time,
                    ),
                    "input_queue": [
                        _queued_operation(operation)
                        for operation in machine.input_queue
                    ],
                    "suspended_operations": [
                        _queued_operation(operation)
                        for operation in machine.suspended_ops
                    ],
                }
            )

        return {
            "schema_version": 2,
            "simulation_time": self.simulation_time,
            "state_version": self.state_version,
            "jobs": jobs,
            "planning_observation": self._session.obs["planning_observation"],
            "machines": machines,
            "native_observation": _policy_observation(
                self._policy_state()
            ),
            "frame": frame,
        }

    def validate(self, action: Mapping[str, object]) -> ValidationResult:
        dispatches = _dispatches(action)
        if not isinstance(dispatches, (list, tuple)):
            return ValidationResult(
                valid=False,
                violations=(
                    "action.dispatches or action.native_action.production "
                    "must be an array",
                ),
            )

        visible_jobs = {
            int(job.job_id): job for job in self._session.env.pogema_env.jobs
        }
        committed = self._committed_operations()
        native: Mapping = action.get("native_action", action)
        cancelled: set = {tuple(key) for key in native.get("reschedule", {}).get("cancel_operations", [])}
        committed.difference_update(cancelled)
        proposed: set[tuple[int, int]] = set()
        violations: list[str] = []
        for index, item in enumerate(dispatches):
            if not isinstance(item, Mapping):
                violations.append(f"dispatches[{index}] must be an object")
                continue
            if any(type(item.get(name)) is not int for name in ("job_id", "op_id", "machine_id")):
                violations.append(
                    f"dispatches[{index}] requires integer job_id, op_id and machine_id"
                )
                continue
            job_id = int(item["job_id"])
            operation_id = int(item["op_id"])
            machine_id = int(item["machine_id"])
            key = (job_id, operation_id)
            job = visible_jobs.get(job_id)
            if job is None:
                violations.append(
                    f"dispatches[{index}] references an unreleased or unknown job"
                )
                continue
            if not 0 <= operation_id < len(job.ops):
                violations.append(f"dispatches[{index}] references an unknown operation")
                continue
            operation = job.ops[operation_id]
            if key in committed or key in proposed:
                violations.append(f"dispatches[{index}] duplicates a committed operation")
            if operation.status != "PENDING" or (operation.assigned_machine is not None and key not in cancelled):
                violations.append(f"dispatches[{index}] operation is not pending")
            if operation_id > 0 and job.ops[operation_id - 1].status != "FINISHED":
                violations.append(
                    f"dispatches[{index}] predecessor operation is not finished"
                )
            eligible_machines = {
                int(candidate)
                for candidate, _ in (operation.machine_options_with_time or ())
            }
            if machine_id not in eligible_machines:
                violations.append(
                    f"dispatches[{index}] machine is not eligible for the operation"
                )
            proposed.add(key)
        return ValidationResult(valid=not violations, violations=tuple(violations))

    def step(
        self,
        action: Mapping[str, object],
    ) -> StepResult[dict[str, object], dict[str, object]]:
        # DecisionResponse freezes nested mappings. The core owns a mutable
        # copy of the formal action and must never receive those wrappers.
        action = to_jsonable(action)
        if "native_action" in action:
            formal_action = self._expand_native_action(action["native_action"])
        else:
            formal_action = self._dispatch_action(action)
        serialized_formal_action = serialize_action(formal_action)
        _, _, _, _, info = self._session.step(
            formal_action
        )
        self._advance_task_sequence(serialized_formal_action)
        self._action_history.append(
            {
                "requested_action": dict(to_jsonable(action)),
                "formal_action": serialized_formal_action,
            }
        )

        observation = self.observe()
        state_hash = hash_state(observation["frame"])
        events = _domain_events(
            observation["frame"],
            info,
            self.simulation_time,
            state_hash,
        )
        executed_action = serialize_action(self._session.last_actions)
        all_jobs_completed = self._session.env.job_all_done()
        return StepResult(
            observation=observation,
            executed_action=executed_action,
            simulation_time=self.simulation_time,
            state_version=self.state_version,
            metrics=self.metrics(),
            state_hash=state_hash,
            events=events,
            terminated=self.terminated,
            termination_reason=(
                "all_jobs_completed"
                if all_jobs_completed
                else "environment_step_limit"
                if self.terminated
                else None
            ),
        )

    def metrics(self) -> dict[str, float]:
        raw_metrics = self._session.metrics()
        metrics = {
            str(name): float(value)
            for name, value in raw_metrics.items()
            if type(value) in {int, float}
        }
        pogema = self._session.env.pogema_env
        all_jobs = list(getattr(pogema, "_all_jobs", pogema.jobs))
        completed = [job for job in all_jobs if job.is_completed]
        urgent_jobs = [
            job
            for job in all_jobs
            if int(getattr(job, "priority", 0)) >= DFJSPT_URGENT_PRIORITY
        ]
        completed_urgent = [job for job in urgent_jobs if job.is_completed]
        now = self.simulation_time
        unfinished_jobs = len(all_jobs) - len(completed)
        unfinished_urgent_jobs = len(urgent_jobs) - len(completed_urgent)
        c_max = max(
            (float(job.completion_time) for job in completed),
            default=now,
        )
        if unfinished_jobs:
            c_max = max(c_max, now)
        c_max_e = max(
            (float(job.completion_time) for job in completed_urgent),
            default=0.0,
        )
        if unfinished_urgent_jobs:
            c_max_e = max(c_max_e, now)
        total_tardiness = 0.0
        weighted_tardiness = 0.0
        for job in all_jobs:
            if job.due is None:
                continue
            completion = (
                float(job.completion_time)
                if job.is_completed
                else now
            )
            tardiness = max(0.0, completion - float(job.due))
            total_tardiness += tardiness
            weighted_tardiness += tardiness * max(
                1.0,
                float(job.priority) / 100.0,
            )
        metrics.update(
            {
                "C_max": c_max,
                "C_max_E": c_max_e,
                "completed_jobs": float(len(completed)),
                "unfinished_jobs": float(unfinished_jobs),
                "urgent_jobs": float(len(urgent_jobs)),
                "unfinished_urgent_jobs": float(unfinished_urgent_jobs),
                "success_rate": 1.0 if not unfinished_jobs else 0.0,
                "job_completion_rate": (
                    float(len(completed)) / len(all_jobs)
                    if all_jobs
                    else 1.0
                ),
                "total_tardiness": total_tardiness,
                "weighted_tardiness": weighted_tardiness,
            }
        )
        return metrics

    def close(self) -> None:
        self._session.close()

    def snapshot(self) -> StateSnapshot:
        observation = self.observe()
        state_hash = hash_state(observation["frame"])
        artifact = self._context.artifact_publisher.publish_json(
            {
                "schema_version": 2,
                "environment_seed": self._environment_seed,
                "state_version": self.state_version,
                "simulation_time": self.simulation_time,
                "state_hash": state_hash,
                "actions": tuple(self._action_history),
            },
            kind=ArtifactKind.STATE_SNAPSHOT,
            metadata={
                "domain": "dfjsp_t",
                "snapshot_format": "deterministic_formal_action_history",
                "scenario_digest": self._context.run.scenario.digest,
                "environment_seed": self._environment_seed,
                "state_version": self.state_version,
                "state_hash": state_hash,
            },
        )
        return StateSnapshot(
            state_version=self.state_version,
            simulation_time=self.simulation_time,
            artifact=artifact,
            state_hash=state_hash,
        )

    def restore(self, snapshot: StateSnapshot) -> dict[str, object]:
        payload = json.loads(
            self._context.artifact_resolver.read_bytes(snapshot.artifact)
        )
        if int(payload["schema_version"]) != 2:
            raise ValueError("unsupported DFJSP-T snapshot schema")
        if int(payload["environment_seed"]) != self._environment_seed:
            raise ValueError("snapshot belongs to a different environment seed")
        if int(payload["state_version"]) != snapshot.state_version:
            raise ValueError("snapshot artifact has a different state version")
        if float(payload["simulation_time"]) != snapshot.simulation_time:
            raise ValueError("snapshot artifact has a different simulation time")
        if str(payload["state_hash"]) != snapshot.state_hash:
            raise ValueError("snapshot artifact has a different state hash")
        actions = tuple(payload["actions"])
        self.reset()
        for action in actions:
            formal_action = action["formal_action"]
            self._session.step(formal_action)
            self._advance_task_sequence(formal_action)
            self._action_history.append(dict(action))
        observation = self.observe()
        state_hash = hash_state(observation["frame"])
        if self.state_version != snapshot.state_version:
            raise ValueError("restored snapshot has a different state version")
        if self.simulation_time != snapshot.simulation_time:
            raise ValueError("restored snapshot has a different simulation time")
        if state_hash != snapshot.state_hash:
            raise ValueError("restored snapshot has a different state hash")
        return observation

    def _advance_task_sequence(
        self,
        formal_action: Mapping[str, object],
    ) -> None:
        requests = formal_action.get("job_actions", {}).get(
            "transfer_requests",
            (),
        )
        if requests:
            self._task_sequence = max(
                self._task_sequence,
                max(int(item["task_id"]) for item in requests) + 1,
            )

    def _dispatch_action(
        self,
        action: Mapping[str, object],
    ) -> dict[str, object]:
        # Dispatch-only algorithms delegate transport to the platform. Native
        # policies and action replay never instantiate these solvers.
        if self._session.coordinator is None:
            from sky_executor.grid_factory.factory.Component.Coordinator.coordinator import Coordinator
            self._session.coordinator = Coordinator(
                job_solver="greedy", route_solver=self._route_solver, assigner=self._assigner,
            )
        dispatches = []
        pogema = self._session.env.pogema_env
        jobs = {int(job.job_id): job for job in pogema.jobs}
        for item in action.get("dispatches", ()):
            job = jobs[int(item["job_id"])]
            operation = job.ops[int(item["op_id"])]
            machine_id = int(item["machine_id"])
            dispatches.append(
                {
                    "task_id": self._task_sequence,
                    "job_id": int(job.job_id),
                    "op_id": int(operation.op_id),
                    "source": [-1, 0],
                    "destination_machine_id": machine_id,
                    "candidate_machines": [machine_id],
                    "ready_time": self.simulation_time,
                    "priority": int(job.priority),
                    "request_id": job.request_id,
                }
            )
            self._task_sequence += 1

        raw_observation = self._session.obs
        task_observation = raw_observation["task_observation"]
        assign_actions = self._session.coordinator.assigner.plan(task_observation)
        route_solver = self._session.coordinator.route_solver
        if getattr(route_solver, "accepts_task_observation", False):
            agent_actions = route_solver.plan(
                raw_observation["agent_observation"],
                task_observation=task_observation,
            )
        else:
            agent_actions = route_solver.plan(raw_observation["agent_observation"])
        return {
            "reschedule": dict(action.get("reschedule", {})),
            "job_actions": {"transfer_requests": dispatches},
            "assign_actions": assign_actions,
            "agent_actions": agent_actions,
        }

    def _expand_native_action(self, value: object) -> dict[str, object]:
        native = dict(value)
        if "job_actions" in native:
            return native

        raw_observation = self._session.obs
        task_observation = raw_observation["task_observation"]
        machines = list(task_observation.get("machines") or ())
        machine_by_id = {
            int(getattr(machine, "id", index)): machine
            for index, machine in enumerate(machines)
        }
        jobs = {
            int(job.job_id): job
            for job in self._session.env.pogema_env.jobs
        }
        requests = []
        for item in native.get("production", ()):
            job = jobs[int(item["job_id"])]
            machine_id = int(item["machine_id"])
            machine = machine_by_id[machine_id]
            requests.append(
                {
                    "task_id": self._task_sequence,
                    "job_id": int(item["job_id"]),
                    "op_id": int(item["op_id"]),
                    "source": [-1, -1],
                    "destination": list(machine.location),
                    "destination_machine_id": machine_id,
                    "candidate_machines": [machine_id],
                    "ready_time": self.simulation_time,
                    "priority": int(job.priority),
                    "request_id": job.request_id,
                }
            )
            self._task_sequence += 1

        agents = list(task_observation.get("agents") or ())
        assignments = {
            int(item["agv_id"]): int(item["task_id"])
            for item in native.get("logistics", ())
        }
        assigned_task_ids = {
            task_id for task_id in assignments.values() if task_id is not None
        }
        pending_transfers = [
            task
            for task in task_observation.get("pending_transfers", ())
            if int(task.task_id) not in assigned_task_ids
        ]
        for index, agent in enumerate(agents):
            assignments.setdefault(int(getattr(agent, "id", index)), None)
        route_by_agv = {
            int(item["agv_id"]): int((item.get("path") or (0,))[0])
            for item in native.get("route", ())
        }
        agent_actions = [
            route_by_agv.get(int(getattr(agent, "id", index)), 0)
            for index, agent in enumerate(agents)
        ]
        return {
            "reschedule": dict(native.get("reschedule", {})),
            "job_actions": {"transfer_requests": requests},
            "assign_actions": {
                "assignments": assignments,
                "pending_transfers": pending_transfers,
            },
            "agent_actions": agent_actions,
        }

    def _committed_operations(self) -> set[tuple[int, int]]:
        pogema = self._session.env.pogema_env
        tasks = []
        for name in (
            "pending_transfers",
            "buffered_tasks",
            "transfers_to_assign",
            "active_transfers",
            "agv_current_task",
        ):
            tasks.extend(item for item in getattr(pogema, name, ()) if item is not None)
        committed = {(int(task.job_id), int(task.op_id)) for task in tasks}
        for machine in pogema.machines:
            operations = [machine.current_op, *machine.input_queue, *machine.suspended_ops]
            committed.update(
                (int(operation.job_id), int(operation.op_id))
                for operation in operations
                if operation is not None and operation.status != "FINISHED"
            )
        return committed

    def _policy_state(self) -> RaceState:
        state = self._state_encoder.encode(self._session.obs)
        committed = self._committed_operations()
        jobs = {
            int(job.job_id): job
            for job in self._session.env.pogema_env.jobs
        }
        operation_keys = state.metadata["operation_keys"]
        production_mask = state.action_masks["production"]
        for edge_index, (operation_index, _) in enumerate(
            state.metadata["operation_machine_edges"]
        ):
            job_id, operation_id = operation_keys[operation_index]
            job = jobs[int(job_id)]
            operation = job.ops[int(operation_id)]
            predecessor_ready = (
                int(operation_id) == 0
                or job.ops[int(operation_id) - 1].status == "FINISHED"
            )
            production_mask[edge_index] = bool(
                production_mask[edge_index]
                and (int(job_id), int(operation_id)) not in committed
                and operation.status == "PENDING"
                and operation.assigned_machine is None
                and predecessor_ready
            )
        return state


def _scenario_path(root: Path, uri: str) -> tuple[Path, str]:
    direct_uri, separator, direct_fragment = uri.partition("#")
    direct_path = Path(direct_uri)
    if direct_path.is_absolute():
        return direct_path.resolve(strict=True), (
            unquote(direct_fragment) if separator else ""
        )
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        file_path = unquote(parsed.path)
        if len(file_path) >= 3 and file_path[0] == "/" and file_path[2] == ":":
            file_path = file_path[1:]
        path = Path(f"//{parsed.netloc}{file_path}" if parsed.netloc else file_path)
    elif parsed.scheme:
        raise ValueError(f"unsupported scenario URI scheme: {parsed.scheme}")
    else:
        path = Path(unquote(parsed.path))
    if not path.is_absolute():
        path = root / path
    return path.resolve(strict=True), unquote(parsed.fragment)


def _scenario_ref(value: object) -> ScenarioRef:
    item = dict(value)
    return ScenarioRef(
        scenario_id=str(item["scenario_id"]),
        uri=str(item["uri"]),
        digest=str(item["digest"]),
        metadata=dict(item.get("metadata", {})),
    )


def _expand_problem(problem: DFJSPTProblem) -> tuple[DFJSPTProblem, ...]:
    if not problem.is_corpus:
        return (problem,)
    result = []
    for index, instance in enumerate(problem.corpus_instances):
        instance_id = str(instance.get("instance_id", index))
        result.append(
            DFJSPTProblem(
                scenario_id=f"{problem.scenario_id}:{instance_id}",
                scenario_digest=(
                    f"sha256:{instance['canonical_hash']}"
                ),
                _instance=instance,
                metadata={
                    **problem.metadata,
                    "corpus": False,
                    "corpus_scenario_id": problem.scenario_id,
                    "corpus_digest": problem.scenario_digest,
                    "instance_id": instance_id,
                },
            )
        )
    return tuple(result)


def _contains_instance_split(
    problem: DFJSPTProblem,
    split: str,
) -> bool:
    instances = (
        problem.corpus_instances
        if problem.is_corpus
        else (problem.instance,)
    )
    return any(
        str(instance.get("split", "")).lower() == split
        for instance in instances
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl_corpus(
    path: Path,
    instance_ids: tuple[str, ...],
) -> tuple[dict[str, object], ...]:
    if len(instance_ids) != len(set(instance_ids)):
        raise ValueError("corpus instance_ids must be unique")
    instances: list[dict[str, object]] = []
    by_id: dict[str, dict[str, object]] = {}
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            instance = json.loads(line)
            if not isinstance(instance, dict):
                raise ValueError(f"{path}:{line_number} is not an object")
            instance_id = str(instance.get("instance_id", ""))
            if not instance_id:
                raise ValueError(
                    f"{path}:{line_number} has no instance_id"
                )
            if instance_id in by_id:
                raise ValueError(
                    f"corpus contains duplicate instance_id {instance_id!r}"
                )
            by_id[instance_id] = instance
            instances.append(instance)
    selected = (
        tuple(by_id[instance_id] for instance_id in instance_ids)
        if instance_ids
        else tuple(instances)
    )
    if not selected:
        raise ValueError("corpus must contain at least one instance")
    for instance in selected:
        validate_instance(instance)
        if not str(instance.get("canonical_hash", "")):
            raise ValueError("every corpus instance requires canonical_hash")
    canonical_hashes = [str(instance["canonical_hash"]) for instance in selected]
    if len(canonical_hashes) != len(set(canonical_hashes)):
        raise ValueError("corpus contains duplicate canonical instances")
    return selected


def _policy_observation(state: RaceState) -> dict[str, object]:
    return {
        "nodes": {
            name: values.tolist()
            for name, values in state.nodes.items()
        },
        "node_shapes": {
            name: tuple(int(size) for size in values.shape)
            for name, values in state.nodes.items()
        },
        "edges": {
            name: values.tolist()
            for name, values in state.edges.items()
        },
        "action_masks": {
            name: values.tolist()
            for name, values in state.action_masks.items()
        },
        "coupling_vector": state.coupling_vector.tolist(),
        "timeline": int(state.timeline),
        "metadata": dict(to_jsonable(state.metadata)),
    }


def _dispatches(action: Mapping[str, object]) -> object:
    if "native_action" not in action:
        return action.get("dispatches", ())
    native = action["native_action"]
    if "production" in native:
        return native["production"]
    requests = native.get("job_actions", {}).get("transfer_requests", ())
    return tuple(
        {
            "job_id": item["job_id"],
            "op_id": item["op_id"],
            "machine_id": (
                item["machine_id"]
                if "machine_id" in item
                else item["destination_machine_id"]
            ),
        }
        for item in requests
    )


def _read_jsonl_instance(path: Path, instance_id: str) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            instance = json.loads(line)
            if str(instance.get("instance_id")) == instance_id:
                return instance
    raise KeyError(f"instance {instance_id!r} does not exist in {path}")


def _operation_key(operation: object | None) -> dict[str, int] | None:
    if operation is None:
        return None
    return {
        "job_id": int(operation.job_id),
        "op_id": int(operation.op_id),
    }


def _current_remaining_time(machine: object, process_times: Mapping[int, object]) -> float:
    operation = machine.current_op
    if operation is None:
        return 0.0
    if operation.remaining_proc_time is not None:
        return float(operation.remaining_proc_time)
    return max(0.0, float(operation.nominal_proc_time or operation.proc_time) - operation.processed_time)


def _queued_operation(operation: object) -> dict[str, object]:
    return {
        "job_id": int(operation.job_id),
        "op_id": int(operation.op_id),
        "priority": int(operation.priority),
        "processing_time": float(
            operation.remaining_proc_time
            if operation.remaining_proc_time is not None
            else operation.proc_time
        ),
    }


def _domain_events(
    frame: Mapping[str, object],
    info: Mapping[str, object],
    simulation_time: float,
    state_hash: str,
) -> tuple[DomainEvent, ...]:
    # The formal environment publishes the same committed events in both
    # outputs. Use one authoritative window instead of recording each twice.
    values = info.get("events", frame.get("events", ())) or ()
    events = [
        DomainEvent(
            event_type="runtime_frame",
            payload={"frame": frame},
            simulation_time=simulation_time,
            state_hash=state_hash,
        )
    ]
    for value in values:
        payload = dict(value) if isinstance(value, Mapping) else {"value": value}
        events.append(
            DomainEvent(
                event_type=str(payload.get("type", "dfjsp_t_event")),
                payload=payload,
                simulation_time=simulation_time,
                state_hash=state_hash,
            )
        )
    return tuple(events)
