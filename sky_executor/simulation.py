"""Pogema fleet movement and explicit virtual-time advancement."""
from __future__ import annotations

from contextlib import nullcontext
from collections import deque
from copy import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pogema.envs import PogemaLifeLong
from sky_executor.decision import DecisionChoice
from sky_executor.lifecycle import RunReplaced
from sky_executor.planning import PlanRejected
from sky_executor.scenario import SceneAdapter
from gymnasium import Wrapper

if TYPE_CHECKING:
    from sky_executor.perception import PerceptionWorker


class SimulationAdapter(SceneAdapter):
    immediate_material_settlement = False
    def __init__(self, env, *, agv=None, machine=None, position_source=None):
        from sky_executor.simulated_execution import SimulatedAgvExecutor
        from sky_executor.simulated_execution import SimulatedMachineExecutor
        from sky_executor.execution import ExecutionBinding
        from sky_executor.perception import create_observation_source
        self._check_pogema_layout = agv is None and machine is None and position_source is None
        self.immediate_material_settlement = not self._check_pogema_layout
        if agv is None:
            executor = SimulatedAgvExecutor(lambda actions: compute_pogema_candidate(env, actions),
                dropoff_admission=env.can_complete_dropoff, **{key: value
                for key, value in (env.material_handling_config or {}).items()
                if key in ("pickup_dwell_steps", "dropoff_dwell_steps")})
            agv = ExecutionBinding(executor, executor, executor,
                                   cancel_simulation_requests=executor.cancel_requests)
        if machine is None:
            executor = SimulatedMachineExecutor(env.processing_time_config)
            machine = ExecutionBinding(executor, executor, executor, executor.diagnostics,
                                       executor.configure_operations, executor.configure_seed)
        if position_source is None:
            position_source = create_observation_source(env.perception_config, env)
        self._virtual_time = 0
        super().__init__(env, agv=agv, machine=machine, clock=lambda: self._virtual_time,
                         position_source=position_source, source="simulation")
        from sky_executor.simulation_faults import SimulationFaultSource
        self.step_fault_source = SimulationFaultSource(self)
        self.candidate_positions = None
        self.candidate_movement_request_id = None

    def validate_initial_layout(self):
        if not self._check_pogema_layout:
            return
        state = self.env.state
        endpoints: set[tuple[int, int]] = {machine.location for machine in state.machines}
        endpoints.update(state._to_public_xy(pos) for pos in state.grid.positions_xy)
        endpoints.update(job.raw_material_source for job in state._all_jobs if job.raw_material_source is not None)
        endpoints.update(job.finished_goods_destination for job in state._all_jobs if job.finished_goods_destination is not None)
        endpoints.update(pos for pos in (state.raw_material_source, state.finished_goods_destination) if pos is not None)
        cells: set[tuple[int, int]] = {state._to_internal_xy(pos) for pos in endpoints}
        grid = state.grid.obstacles
        for x, y in cells:
            if not (0 <= x < grid.shape[0] and 0 <= y < grid.shape[1]) or grid[x, y] != 0:
                raise ValueError("material stations, machines and AGVs must lie on traversable cells")
        start: tuple[int, int] = min(cells)
        seen: set = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbour = (x + dx, y + dy)
                if (0 <= neighbour[0] < grid.shape[0] and 0 <= neighbour[1] < grid.shape[1]
                        and grid[neighbour] == 0 and neighbour not in seen):
                    seen.add(neighbour)
                    queue.append(neighbour)
        if not cells <= seen:
            unreachable: list[tuple[int, int]] = sorted(state._to_public_xy(pos) for pos in cells - seen)
            raise ValueError(f"工厂机器、AGV 和物料站必须位于同一四邻接连通区域；与 {state._to_public_xy(start)} 不连通的位置：{unreachable}")
        return {state._to_public_xy(pos) for pos in seen}
    def reset_state(self):
        super().reset_state()
        self.step_fault_source.reset(self.env.state.episode_seed)
        self._virtual_time = 0
        self.candidate_positions = None
        self.candidate_movement_request_id = None

    def movement_groups(self, actions):
        return ((tuple(range(len(actions))), tuple(actions)),) if any(actions) else ()

    def record_movement_result(self, request, execution_update):
        if execution_update.positions is None:
            raise RuntimeError("completed simulation movement has no positions")
        self.candidate_positions = execution_update.positions
        self.candidate_movement_request_id = request.request_id

    def check_position_reports(self, reports):
        linked = [report for report in reports if self.candidate_movement_request_id is not None
                  and report.movement_request_id == self.candidate_movement_request_id]
        if linked:
            positions = {report.fact.agv_id: report.fact.grid_cell for report in reports}
            actual = tuple(positions[i] for i in range(len(positions)))
            if actual != self.candidate_positions:
                raise RuntimeError("simulation execution and position report disagree")

    def release_movement_positions(self, request_ids):
        if self.candidate_movement_request_id in request_ids:
            self.candidate_positions = None
            self.candidate_movement_request_id = None

    def observable_positions(self):
        return self.candidate_positions

    def event_time(self):
        return self.env.env_timeline

    def planning_time(self):
        return self.env.env_timeline

    def step_start_time(self, number):
        return number - 1

    def step(self, provided_decision=None, *, evaluate_decision=False, run_worker):
        return run_simulation_step(self, provided_decision,
            evaluate_decision=evaluate_decision, run_worker=run_worker)

    def begin_simulation_effects(self, *, run_worker):
        with self.fault_injector.input_lock:
            with self.env.processing_lock:
                self.env.require_current_run(run_worker)
                self.env.events.begin_frame()
            self.fault_injector.trigger_scheduled(self.event_time(), skip_expired=True)
            self.step_fault_source.sample_step(self.event_time())

    def finish_simulation_effects(self, *, run_worker):
        with self.fault_injector.input_lock:
            with self.env.processing_lock:
                self.env.require_current_run(run_worker)
                self._virtual_time += 1
            self.check_due_faults()


@dataclass
class SimulationStepContext:
    number: int
    run_worker: PerceptionWorker
    handling_request_ids: tuple[str, ...] = ()
    machine_request_ids: tuple[str, ...] = ()
    timing_basis: tuple = ()
    handling_advanced_agvs: set = field(default_factory=set)
    timed_work_processed: bool = False
    finished: bool = False


def compute_pogema_candidate(env, actions):
    """Calculate a whole-fleet candidate without modifying confirmed positions."""
    state = env.state
    shadow = copy(state)
    shadow.grid = copy(state.grid)
    # Pogema writes these fields and may modify the supplied action list.
    shadow.grid.positions_xy = list(state.grid.positions_xy)
    shadow.grid.positions = state.grid.positions.copy()
    PogemaLifeLong.move_agents(shadow, list(actions))
    return tuple(state._to_public_xy(position) for position in shadow.grid.positions_xy)


def begin_simulation_step(env, *, run_worker=None):
    """Reserve a round; default simulation decisions and starts use its beginning."""
    if run_worker is None:
        run_worker = env.ensure_perception_worker()
    with env.process_business_chain(run_worker=run_worker), env.state_lock:
        number = env.env_timeline + 1
        start_time = env.scene_adapter.step_start_time(number)
        env.set_env_timeline(start_time)
        env.state.env_timeline = start_time
        return SimulationStepContext(number, run_worker)


def _advance_execution(scene, binding, participants, *, run_worker=None):
    if binding.simulation_driver is None:
        return frozenset()
    groups = ((request_id,) for request_id in participants) if binding is scene.agv_binding else (participants,)
    advanced = set()
    for group in groups:
        updates, advanced_requests = binding.simulation_driver.advance(group)
        scene.env.apply_execution_reports(tuple(scene.execution_report(update) for update in updates),
                                          run_worker=run_worker)
        advanced.update(advanced_requests)
    return frozenset(advanced)


def prepare_simulation_work(scene, step):
    """Freeze handling first, prepare machines, then freeze processing and timing basis."""
    env = scene.env
    with env.process_business_chain(run_worker=step.run_worker):
        step.handling_request_ids = env.runnable_handling_request_ids()
        if env.machine_preparation == "before_simulation_step":
            env.prepare_machine_work()
            env.dispatch_pending_requests()
        step.machine_request_ids = env.runnable_machine_request_ids()
        with env.state_lock:
            step.timing_basis = env.business_statistics.timing_basis()
            env.state.agv_last_step_phase = [basis.phase for basis in step.timing_basis]


def advance_timed_work(scene, step):
    """Advance the prepared machines and handling once; do not select or start work."""
    if step.timed_work_processed:
        raise RuntimeError("timed work already processed")
    with scene.env.process_business_chain(run_worker=step.run_worker):
        with scene.env.state_lock:
            scene.env.set_env_timeline(step.number)
            scene.env.state.env_timeline = step.number
        _advance_execution(scene, scene.machine_binding, step.machine_request_ids, run_worker=step.run_worker)
        advanced = _advance_execution(scene, scene.agv_binding, step.handling_request_ids, run_worker=step.run_worker)
        step.handling_advanced_agvs = scene.env.handling_agv_ids(advanced)
    step.timed_work_processed = True


def advance_movement(scene, *, run_worker=None):
    """Consume accepted simulated moves once, then obtain their position evidence."""
    env = scene.env
    if run_worker is None:
        run_worker = env.ensure_perception_worker()
    with env.process_business_chain(run_worker=run_worker):
        with env.state_lock:
            participants = env.simulated_movement_participants() if scene.agv_binding.simulation_driver is not None else ()
        _advance_execution(scene, scene.agv_binding, participants, run_worker=run_worker)
    env.submit_scene_positions(run_worker=run_worker)


def finish_simulation_step(scene, step):
    """Classify time, finish scene clocks/effects, and publish the completed-step change."""
    env = scene.env
    if step.finished:
        raise RuntimeError("simulation step already finished")
    with env.process_business_chain(run_worker=step.run_worker), env.state_lock:
        moved_with_load = env._movement_since_tick
        for agv_id, basis in enumerate(step.timing_basis):
            env.business_statistics.record_agv_time(agv_id, basis, moved=agv_id in moved_with_load,
                handling_advanced=agv_id in step.handling_advanced_agvs,
                movement_loaded=moved_with_load.get(agv_id))
        env._movement_since_tick = {}
    env.release_due_jobs(scene.planning_time(), run_worker=step.run_worker)
    # Fault expiry waits for queued reports; both core locks are released here.
    scene.finish_simulation_effects(run_worker=step.run_worker)
    with env.process_business_chain(run_worker=step.run_worker):
        env.events.finish_frame()
        env.record_business_change("simulation_step_finished", step.number)
    snapshot = step.run_worker.request_snapshot().result()
    env.require_current_run(step.run_worker)
    step.finished = True
    return snapshot


def run_simulation_step(scene, provided_decision=None, *, evaluate_decision=False, run_worker):
    """Default discrete recipe; all decision/business operations remain shared."""
    env = scene.env
    with env.simulation_step_lock, env.run_operation(run_worker):
        if provided_decision is not None:
            env.validate_reschedule(provided_decision.get("reschedule") or {})
        controller = env._controller
        context = None
        adjusts_plan = provided_decision is not None and bool(provided_decision.get("reschedule"))
        with env.decision_lock if evaluate_decision or provided_decision is not None else nullcontext():
            if not adjusts_plan:
                env.ensure_business_started(run_worker=run_worker)
            selection = controller.try_snapshot_and_choose() if evaluate_decision and provided_decision is None else None
            solving = selection is not None and selection.choice in (DecisionChoice.DECIDE, DecisionChoice.REPLAN_AND_DECIDE)
            if solving:
                controller.replan_if_needed(selection.choice)
            step = begin_simulation_step(env, run_worker=run_worker)
            if provided_decision is not None:
                context = controller.accept_decision(controller.snapshot(), provided_decision)
            elif solving:
                # Default simulation solves at the beginning of [t, t+1].
                context = controller.decide(controller.snapshot())
            scene.begin_simulation_effects(run_worker=run_worker)
            env.release_due_jobs(scene.planning_time(), run_worker=run_worker)
            if context is not None:
                env.apply_decision(context, run_worker=run_worker)
            if adjusts_plan:
                env.ensure_business_started(run_worker=run_worker)
            controller.consume_decision_changes(selection)
        with env.process_business_chain(run_worker=run_worker):
            prepare_simulation_work(scene, step)
            advance_timed_work(scene, step)
        if context is not None:
            env.submit_movement(context, run_worker=run_worker)
        advance_movement(scene, run_worker=run_worker)
        return finish_simulation_step(scene, step)


class PogemaSimulationStepBridge(Wrapper):
    """Give vendor animation/history wrappers the final result of a scene step."""
    def __init__(self, state, get_scene):
        super().__init__(state)
        self._get_scene = get_scene

    def step(self, request):
        scene = self._get_scene()
        env = scene.env
        run_worker, provided_decision, evaluate_decision = request
        try:
            snapshot = scene.step(provided_decision,
                evaluate_decision=evaluate_decision, run_worker=run_worker)
        except (RunReplaced, PlanRejected):
            raise
        except BaseException:
            env.close_run_worker(run_worker)
            raise
        with env.processing_lock:
            env.require_current_run(run_worker)
            env._simulation_snapshot = snapshot
        count = env.grid_config.num_agents
        return (snapshot.observation["agent_observation"], [],
                [False] * count, [False] * count, [{} for _ in range(count)])
