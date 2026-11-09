"""Policy, snapshots, replanning and solving; independent of simulation ticks."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import Event, Lock
from time import perf_counter

from sky_executor.decision import DefaultDecisionPolicy, DecisionChoice, DecisionSelection, DecisionCycleResult
from sky_executor.grid_factory.factory.business import agv_action_basis
from sky_executor.lifecycle import RunReplaced
from sky_executor.actions import normalize_action


@dataclass
class DecisionContext:
    decision: dict
    movement_basis: tuple
    assigned_agv_ids: tuple = ()
    invalidated_agv_ids: set = field(default_factory=set)
    applied: bool = False
    dispatched: bool = False


class DecisionController:
    """Select fresh observations and apply solver decisions through the environment."""
    def __init__(self, env, coordinator, *, decision_policy=None,
                 required_position_samples=None, temporary_obstacle_source=None):
        base = env.state
        self._agv_ids = frozenset(range(base.grid_config.num_agents))
        if base.grid is None or set(env.latest_confirmed_positions) != self._agv_ids:
            raise ValueError("environment must complete reset before creating a controller")
        self._env = env
        self._coordinator = coordinator
        self._worker_options = dict(required_position_samples=required_position_samples,
                                    temporary_obstacle_source=temporary_obstacle_source)
        self._worker = env.start_perception_worker(**self._worker_options)
        self._notifications = env.decision_notifications
        self.decision_policy = decision_policy or DefaultDecisionPolicy()
        self._decision_lock = env.decision_lock
        self._loop_stop = Event()
        self._loop_lock = Lock()
        self._consumed_sequence = 0
        self._checked_sequence = 0
        self.decision_count = 0
        self.last_replan_error = None

    def snapshot(self):
        self._env.require_current_run(self._worker)
        snapshot = self._worker.request_snapshot().result()
        self._env.require_current_run(self._worker)
        return snapshot

    def _normalize_actions(self, actions):
        if len(actions) > len(self._agv_ids):
            raise ValueError("too many agent actions")
        if any(action not in range(5) for action in actions):
            raise ValueError("agent actions must be integers in [0, 4]")
        return tuple(actions) + (0,) * (len(self._agv_ids) - len(actions))

    def decide(self, snapshot):
        self.require_coordinator()
        with self._decision_lock, self._env.run_operation(self._worker):
            decision = self._coordinator.decide(deepcopy(snapshot.observation))
            context = self.accept_decision(snapshot, decision)
            self.decision_count += 1
            return context

    def accept_decision(self, snapshot, provided_decision):
        self._env.require_current_run(self._worker)
        agents = {agent.id: agent for agent in snapshot.observation["task_observation"]["agents"]}
        basis = tuple(agv_action_basis(agents[i].current_task, agents[i].task_phase, agents[i].pos)
                      for i in range(len(self._agv_ids)))
        decision = normalize_action(provided_decision)
        decision["agent_actions"] = list(self._normalize_actions(decision.get("agent_actions", [])))
        return DecisionContext(decision, basis)

    def try_snapshot_and_choose(self) -> DecisionSelection | None:
        """Try the snapshot policy, then choose whether and how to solve."""
        changes = self._notifications.since(self._consumed_sequence)
        if not changes or changes[-1].sequence <= self._checked_sequence:
            return None
        self._checked_sequence = changes[-1].sequence
        if not self.decision_policy.should_snapshot(changes):
            return None
        snapshot = self.snapshot()
        changes = self._notifications.since(self._consumed_sequence, through=snapshot.decision_sequence)
        choice = self.decision_policy.choose_decision(snapshot, changes)
        return DecisionSelection(snapshot, choice)

    def consume_decision_changes(self, selection: DecisionSelection | None):
        if selection is not None:
            self._consumed_sequence = selection.snapshot.decision_sequence
            self._checked_sequence = max(self._checked_sequence, self._consumed_sequence)
            self._notifications.consume(self._consumed_sequence)

    def replan_if_needed(self, choice: DecisionChoice):
        """Replan queued insertions, then residual work when the policy requests it."""
        changed = self.replan_pending_insertions()
        error = None
        if choice is DecisionChoice.REPLAN_AND_DECIDE:
            changed = True
            from sky_executor.job_insertion import build_replan_problem
            from sky_executor.perception.contracts import JobPlanningUpdate
            with self._env.read_state():
                problem, _ = build_replan_problem(self._env, self._env.scene_adapter.planning_time(), ())
            try:
                self._coordinator.job_solver.replan(problem)
            except Exception as failure:
                self._env.require_current_run(self._worker)
                error = str(failure)
            else:
                keys = frozenset((job["job_id"], op["op_id"])
                                 for job in problem["jobs"] for op in job["operations"])
                adopted = self._planning_update(JobPlanningUpdate(None, "scheduled", replanned_keys=keys))
                if not adopted.applied:
                    raise RuntimeError("current production-plan result was rejected: " + adopted.reason)
                changed = True
        self.last_replan_error = error
        return changed, error

    def run_decision_cycle(self):
        self.require_coordinator()
        with self._decision_lock, self._env.run_operation(self._worker):
            self._env.ensure_business_started(run_worker=self._worker)
            selection = self.try_snapshot_and_choose()
            if selection is None:
                return DecisionCycleResult()
            if selection.choice is DecisionChoice.SKIP:
                self.consume_decision_changes(selection)
                return DecisionCycleResult(selection.snapshot, selection.choice)
            changed, error = self.replan_if_needed(selection.choice)
            snapshot = self.snapshot() if changed else selection.snapshot
            context = self.decide(snapshot)
            self._env.apply_decision(context, run_worker=self._worker)
            self._env.submit_movement(context, run_worker=self._worker)
            self.consume_decision_changes(selection)
            return DecisionCycleResult(snapshot, selection.choice, deepcopy(context.decision), error)

    def run_decision_loop(self):
        self.require_coordinator()
        if not self._loop_lock.acquire(blocking=False):
            raise RuntimeError("decision loop is already running")
        self._loop_stop.clear()
        try:
            while not self._loop_stop.is_set() and not self._notifications.closed:
                self.run_decision_cycle()
                self._notifications.wait(self._checked_sequence, self._loop_stop)
        except RunReplaced:
            return
        finally:
            self._loop_lock.release()

    def stop_decision_loop(self):
        self._loop_stop.set()
        self._notifications.wake()

    def require_coordinator(self):
        if self._coordinator is None:
            raise ValueError("internal decision operations require a Coordinator")

    def _planning_update(self, update):
        with self._env.processing_lock:
            self._env.require_current_run(self._worker)
            report = self._env.scene_adapter.job_report(update)
            handle = self._worker.submit_report(report)
        result = handle.result()
        self._env.require_current_run(self._worker)
        return result

    def replan_pending_insertions(self):
        """Replan and install queued orders without blocking report consumption."""
        from sky_executor.job_insertion import build_replan_problem
        from sky_executor.perception.contracts import JobPlanningUpdate
        changed = False
        while True:
            with self._env.process_business_chain(run_worker=self._worker), self._env.state_lock:
                request = self._env.job_insertions.next_request()
                if request is None:
                    return changed
                problem, new_jobs = build_replan_problem(
                    self._env, self._env.scene_adapter.planning_time(), request["_jobs"])
            request_id = request["request_id"]
            adopted = self._planning_update(JobPlanningUpdate(request_id, "replanning"))
            if not adopted.applied:
                continue
            changed = True
            started = perf_counter()
            try:
                planning_result = self._coordinator.job_solver.replan(problem)
            except Exception as error:
                self._planning_update(JobPlanningUpdate(
                    request_id, "failed", latency_ms=(perf_counter() - started) * 1000, reason=str(error)))
                continue
            latency = float(planning_result.get("latency_ms", (perf_counter() - started) * 1000))
            replanned_keys = frozenset((job["job_id"], operation["op_id"])
                                      for job in problem["jobs"] for operation in job["operations"])
            adopted = self._planning_update(JobPlanningUpdate(
                request_id, "scheduled", tuple(new_jobs), replanned_keys, latency))
            changed = True
            if not adopted.applied:
                raise RuntimeError("current production-plan result was rejected: " + adopted.reason)
