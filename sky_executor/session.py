"""Shared headless Grid simulation session.

The HTTP server and batch runner use this class as their runtime boundary.  It
contains no FastAPI or timing code, so callers can drive the same environment
from a web service, a command line process, or a future training loop.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pogema import GridConfig

from sky_executor.grid_factory.factory.Component.Coordinator.coordinator import Coordinator
from sky_executor.grid_factory.factory.Utils.structure import JobConfig, MachineConfig
from sky_executor.grid_factory.factory.grid_factory_env import GridFactoryEnv


def _obstacle_map(topology: dict, machine_positions: list[tuple[int, int]], agent_positions: list[tuple[int, int]], extra_passable: list[tuple[int, int]]) -> str:
    width = int(topology.get("gridWidth", 20))
    height = int(topology.get("gridHeight", 20))
    size = max(width, height)
    blocked: set[tuple[int, int]] = set()
    for zone in topology.get("zones", []):
        if zone.get("type") != "obstacle":
            continue
        area = zone.get("area", {})
        for dy in range(int(area.get("h", 0))):
            for dx in range(int(area.get("w", 0))):
                blocked.add((int(area.get("x", 0)) + dx, int(area.get("y", 0)) + dy))
    blocked.difference_update(machine_positions, agent_positions, extra_passable)
    return "\n".join(
        "".join("#" if x >= width or y >= height or (x, y) in blocked else "." for y in range(size))
        for x in range(size)
    )


def _processing_config(operation: dict) -> dict | None:
    for key in ("processing_time_config", "processing_time_distribution", "processing_time_distributions"):
        value = operation.get(key)
        if isinstance(value, dict):
            return deepcopy(value)
    return None


def _material_config(raw: dict | None, topology: dict) -> dict:
    raw = raw or {}
    if not isinstance(raw, dict):
        raise ValueError("material_handling_config must be an object")
    result = {}
    for key in ("pickup_dwell_steps", "dropoff_dwell_steps"):
        value = raw.get(key, 2)
        if type(value) is not int or value < 0:
            raise ValueError(f"material_handling_config.{key} must be a non-negative integer")
        result[key] = value
    result["buffer_capacity"] = int(raw.get("buffer_capacity", 4))
    if result["buffer_capacity"] < 1:
        raise ValueError("buffer_capacity must be positive")
    result["machine_buffer_capacities"] = dict(raw.get("machine_buffer_capacities", {}))
    for name, topology_name in (("raw_material_source", "depot"), ("finished_goods_destination", "product")):
        source = raw.get(name)
        if source is None:
            source = topology.get(topology_name)
        if source is None:
            continue
        if not isinstance(source, (list, tuple)) or len(source) != 2 or any(type(v) is not int for v in source):
            raise ValueError(f"material station {name} must be [x, y] integers")
        width = int(topology.get("gridWidth", 20))
        height = int(topology.get("gridHeight", 20))
        if not (0 <= source[0] < width and 0 <= source[1] < height):
            raise ValueError(f"material station {name} must be inside the configured map")
        result[name] = list(source)
    return result


def _exception_config(raw: dict | None, obs_radius: int) -> dict | None:
    if not raw:
        return raw
    return deepcopy(raw)


def create_env_from_config(config: dict, *, agent_observation_type: str = "default",
                           headless: bool = False, scene_factory=None,
                           machine_preparation="before_simulation_step") -> GridFactoryEnv:
    """Create the shared Grid environment from the public factory schema."""
    topology = config.get("topology", {})
    agvs = config.get("agvs", [])
    machines = topology.get("machines") or {}
    machine_values = list(machines.values())
    machine_positions = [tuple(m["location"]) for m in machine_values if "location" in m]
    agent_positions = [tuple(a["initialLocation"]) for a in agvs]
    occupied = {}
    for agv, position in zip(agvs, agent_positions):
        if position in occupied:
            raise ValueError(f"AGV {occupied[position]} 和 AGV {agv['id']} 初始位置重复: {position}")
        occupied[position] = agv["id"]
    material = _material_config(config.get("material_handling_config"), topology)
    extra = [tuple(material[key]) for key in ("raw_material_source", "finished_goods_destination") if key in material]
    configured_jobs = config.get("jobs") or {}
    configured_jobs = configured_jobs.get("job_list", []) if isinstance(configured_jobs, dict) else configured_jobs
    extra.extend(tuple(job[key]) for job in configured_jobs
                 for key in ("raw_material_source", "finished_goods_destination") if job.get(key) is not None)

    raw_map = config.get("map") or topology.get("map")
    if raw_map:
        map_text = "\n".join(str(raw_map).splitlines())
        map_width = max((len(line) for line in map_text.splitlines()), default=20)
        map_height = len(map_text.splitlines())
    else:
        map_text = _obstacle_map(topology, machine_positions, agent_positions, extra)
        map_width = int(topology.get("gridWidth", 20))
        map_height = int(topology.get("gridHeight", 20))
    num_agents = len(agent_positions) or int(config.get("num_agents", 4))

    grid_kwargs = dict(
        size=max(int(topology.get("gridWidth", map_width)), int(topology.get("gridHeight", map_height)), map_width, map_height),
        map=map_text,
        num_agents=num_agents,
        seed=int(config.get("seed", 42)),
        max_episode_steps=int((config.get("simulation_control") or {}).get("max_steps", 256)),
        obs_radius=int(config.get("obs_radius", 5)),
        on_target="restart",
        agents_xy=agent_positions or None,
        targets_xy=agent_positions or None,
    )
    if agent_observation_type != "default":
        grid_kwargs["observation_type"] = agent_observation_type
    grid = GridConfig(**grid_kwargs)

    custom_jobs = []
    durations = []
    jobs = config.get("jobs") or {}
    job_list = jobs.get("job_list", []) if isinstance(jobs, dict) else jobs
    for job in job_list:
        operations = []
        for operation in job.get("operations", []):
            options = operation.get("machine_options_with_time")
            if options is None and operation.get("machine_id") is not None and operation.get("duration") is not None:
                options = [[operation["machine_id"], operation["duration"]]]
            if not isinstance(options, list) or not options:
                raise ValueError("each operation must define machine_options_with_time")
            normalized = [(int(machine), float(duration)) for machine, duration in options]
            durations.extend(duration for _, duration in normalized)
            operations.append((normalized, normalized[0][1], _processing_config(operation)))
        custom_jobs.append(operations)

    job_config = JobConfig(
        num_jobs=len(custom_jobs),
        min_ops_per_job=min((len(job) for job in custom_jobs), default=1),
        max_ops_per_job=max((len(job) for job in custom_jobs), default=1),
        min_proc_time=min(durations, default=1),
        max_proc_time=max(durations, default=1),
        machine_choices=1,
        total_machines=len(machine_values) or int(config.get("machine_count", 5)),
        seed=int(config.get("seed", 42)),
        strategy="custom_time",
        custom_jobs=custom_jobs,
    )
    machine_count = len(machine_values) or int(config.get("machine_count", 5))
    machine_strategy = config.get("machine_strategy", "custom" if machine_positions else "random")
    machine_config = MachineConfig(
        num_machines=machine_count,
        strategy=machine_strategy,
        custom_positions=machine_positions or None,
        seed=int(config.get("seed", 42)),
    )
    if machine_positions:
        grid.possible_targets_xy = machine_positions
    env = GridFactoryEnv(
        grid_config=grid,
        machine_config=machine_config,
        job_config=job_config,
        random_target=False,
        exception_config=_exception_config(config.get("exception_config"), grid.obs_radius or 0),
        processing_time_config=config.get("processing_time_config"),
        material_handling_config=material,
        headless=headless,
        perception_config=config.get("perception"),
        scene_factory=scene_factory,
        machine_preparation=machine_preparation,
    )
    for generated, source in zip(env.init_jobs, job_list):
        generated.job_id = int(source.get("job_id", generated.job_id))
        generated.release = float(source.get("release", source.get("release_time", 0)) or 0)
        generated.due = source.get("due")
        generated.priority = int(source.get("priority", 0) or 0)
        generated.request_id = source.get("request_id")
        for operation, definition in zip(generated.ops, source.get("operations", ())):
            operation.job_id = generated.job_id
            operation.release = float(definition.get("release", generated.release) or generated.release)
            operation.due = definition.get("due", generated.due)
            operation.priority = int(definition.get("priority", generated.priority) or generated.priority)
        for field in ("raw_material_source", "finished_goods_destination"):
            value = source.get(field)
            setattr(generated, field, tuple(value) if value is not None else None)
    return env


class SimulationSession:
    """Framework-independent environment/coordinator session."""

    def __init__(self, env: GridFactoryEnv, coordinator: Coordinator | None = None, *, decision_policy=None):
        self.env = env
        self.coordinator = coordinator
        self.decision_policy = decision_policy
        self.obs, self.info = self.env.reset()
        self.step_index = 0
        self.done = False

    @classmethod
    def from_config(
        cls,
        config: dict,
        *,
        job_solver: str = "greedy",
        route_solver: str = "astar",
        assigner: str = "nearest",
        native_actions: bool = False,
        agent_observation_type: str = "default",
        headless: bool = False,
        scene_factory=None,
        decision_policy=None,
        machine_preparation="before_simulation_step",
        **kwargs,
    ):
        env = create_env_from_config(config, agent_observation_type=agent_observation_type,
                                     headless=headless, scene_factory=scene_factory,
                                     machine_preparation=machine_preparation)
        coordinator = None if native_actions else Coordinator(
            job_solver=job_solver, route_solver=route_solver, assigner=assigner, **kwargs)
        return cls(env, coordinator, decision_policy=decision_policy)

    @classmethod
    def from_environment(
        cls, env: GridFactoryEnv, *, job_solver: str = "greedy", route_solver: str = "astar",
        assigner: str = "nearest", native_actions: bool = False, decision_policy=None, **kwargs,
    ):
        coordinator = None if native_actions else Coordinator(
            job_solver=job_solver, route_solver=route_solver, assigner=assigner, **kwargs)
        return cls(env, coordinator, decision_policy=decision_policy)

    def reset(self, seed: int | None = None):
        if self.coordinator is not None:
            self.coordinator.reset()
        self.obs, self.info = self.env.reset(seed=seed)
        self.step_index = 0
        self.done = False
        return self.obs, self.info

    def _controller(self):
        return self.env.ensure_controller(self.coordinator, decision_policy=self.decision_policy)

    def snapshot(self):
        return self._controller().snapshot()

    def run_decision_cycle(self):
        return self._controller().run_decision_cycle()

    def run_decision_loop(self):
        self._controller().run_decision_loop()

    def stop_decision_loop(self):
        if self.env._controller is not None:
            self.env._controller.stop_decision_loop()

    @property
    def last_actions(self):
        with self.env.read_state():
            return deepcopy(self.env.last_actions)

    @property
    def decision_count(self):
        return self.env._controller.decision_count if self.env._controller is not None else 0

    def _simulation_step(self, provided_decision=None, *, evaluate_decision):
        with self.env.simulation_step_lock:
            if self.done:
                raise RuntimeError("simulation session is already done")
            self._controller()
            worker = self.env.perception_worker
            with self.env.run_operation(worker):
                output = self.env.synchronous_step(self.coordinator, provided_decision,
                    evaluate_decision=evaluate_decision, run_worker=worker)
                with self.env.read_state():
                    self.env.require_current_run(worker)
                    self.obs, rewards, terminations, truncations, infos = output
                    self.step_index = self.env.env_timeline
                    agent_truncated = truncations.get("agent_truncated", {})
                    self.done = bool(terminations.get("job_done")
                        or (isinstance(agent_truncated, dict) and agent_truncated.get("__all__"))
                        or truncations.get("__all__"))
                return output

    def step(self, actions: dict | None = None):
        if actions is None and self.coordinator is None:
            raise ValueError("native-action sessions require an explicit action")
        return self._simulation_step(actions, evaluate_decision=True)

    def normalize_action(self, actions: dict) -> dict:
        from sky_executor.actions import normalize_action
        return normalize_action(actions)

    def advance_simulation_step(self):
        return self._simulation_step(evaluate_decision=False)

    def _save_observation(self, worker):
        snapshot = worker.request_snapshot().result()
        with self.env.read_state():
            self.env.require_current_run(worker)
            self.obs = snapshot.observation

    def inject_exception(self, event: dict, step: int | None = None) -> dict:
        worker = self.env.ensure_perception_worker()
        injector = self.env.scene_adapter.fault_injector
        with self.env.run_operation(worker):
            with injector.input_lock:
                self.env.require_current_run(worker)
                result = injector.inject_manual(event, step=self.step_index if step is None else step)
            self._save_observation(worker)
            return result

    def clear_exceptions(self, target: dict | None = None, step: int | None = None) -> dict:
        worker = self.env.ensure_perception_worker()
        injector = self.env.scene_adapter.fault_injector
        with self.env.run_operation(worker):
            with injector.input_lock:
                self.env.require_current_run(worker)
                result = injector.clear_manual(target, step=self.step_index if step is None else step)
            self._save_observation(worker)
            return result

    def _submit_job_report(self, content):
        with self.env.processing_lock:
            worker = self.env.ensure_perception_worker()
            report = self.env.scene_adapter.job_report(content)
            handle = worker.submit_report(report)
        with self.env.run_operation(worker):
            report_result = handle.result()
            self._save_observation(worker)
            return report_result

    def submit_job_insertion(self, request):
        """Register a request through the same report queue as device inputs."""
        return self._submit_job_report(request)

    def apply_job_plan(self, update):
        """Apply a production-plan outcome without bypassing report ordering."""
        return self._submit_job_report(update)

    def residual_problem(self):
        return self.env.residual_problem()

    def reschedule(self, action):
        from sky_executor.perception.contracts import RescheduleRequest
        return self._submit_job_report(RescheduleRequest(deepcopy(action)))

    def check_job_releases(self):
        return self.env.scene_adapter.check_job_releases()

    def state_frame(self) -> dict:
        from sky_executor.runtime_log import build_runtime_frame
        return build_runtime_frame(self)

    def metrics(self) -> dict:
        return self.env.metrics_hub.get_episode_summary()

    def heatmaps(self) -> dict:
        return self.env.metrics_hub.get_heatmaps()

    def close(self) -> None:
        self.stop_decision_loop()
        self.env.decision_notifications.close()
        try:
            if self.coordinator is not None:
                for component in (self.coordinator.job_solver, self.coordinator.route_solver, self.coordinator.assigner):
                    close = getattr(component, "close", None)
                    if close is not None:
                        close()
        finally:
            self.env.close()
