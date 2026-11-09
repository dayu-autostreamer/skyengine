"""Scene I/O and explicitly supplied execution capabilities."""
from dataclasses import replace
from copy import deepcopy
from threading import RLock

from sky_executor.faults import FaultInjector
from sky_executor.grid_factory.factory.obstacles import can_block_cell
from sky_executor.perception.contracts import AgvObservation, ObservationBatch, PerceptionReport, TemporaryObstacleObservation


class SceneAdapter:
    """Adapt sources and ports without reading core execution records."""
    immediate_material_settlement = True
    def __init__(self, env, *, agv, machine, clock, position_source=None,
                 initial_positions=None, source="scene"):
        self.env = env
        self.agv_binding = agv
        self.machine_binding = machine
        self.position_source = position_source
        self._initial_positions = initial_positions
        self._clock = clock
        self.source = source
        self._input_lock = RLock()
        self._accepting = False
        self._sequence = 0
        self.fault_injector = FaultInjector(self, env.fault_config)

    def capture_positions(self):
        if self.position_source is not None:
            return self.position_source.observe()
        if self._initial_positions is None:
            raise RuntimeError("push-only scenes must provide initial positions")
        self._sequence += 1
        return ObservationBatch(self.source + "-initial", self._sequence, float(self.now()), tuple(
            AgvObservation(i, tuple(position)) for i, position in enumerate(self._initial_positions())))

    def close(self):
        if self.position_source is not None:
            self.position_source.close()

    def now(self):
        return self._clock()

    def planning_time(self):
        return self.now()

    def check_job_releases(self):
        """Explicitly check this clock, ordered with other scene inputs."""
        from sky_executor.perception.contracts import JobReleaseCheck
        with self.env.processing_lock:
            self._require_input_open()
            worker = self.env.ensure_perception_worker()
            handle = worker.submit_report(self.job_report(JobReleaseCheck(self.planning_time())))
        with self.env.run_operation(worker):
            return handle.result()

    def event_time(self):
        return self.now()

    def step_start_time(self, number):
        """Independent scenes retain explicit-step labels and their own clock."""
        return number

    def validate_initial_layout(self):
        """Independent scenes impose their own initial travel constraints."""
        pass

    def reset_state(self):
        with self._input_lock:
            self._sequence = 0
            self.fault_injector.reset()
            self._accepting = True

    def stop_inputs(self):
        with self._input_lock:
            self._accepting = False

    def _require_input_open(self):
        if not self._accepting:
            raise RuntimeError("scene input is stopped")
        self.env.require_execution_running()

    def _report(self, fact, source, movement_request_id=None):
        self._sequence += 1
        return PerceptionReport(source, self._sequence, float(self.now()), fact, movement_request_id)

    def execution_report(self, update):
        with self._input_lock:
            return self._report(update, self.source + "-execution")

    def job_report(self, content):
        with self._input_lock:
            return self._report(content, self.source + "-jobs")

    def position_report(self, agv_id, position, *, source="scene-positions"):
        return self.env.make_position_report(agv_id, position, source=source)

    def publish_report(self, report):
        with self.env.processing_lock, self._input_lock:
            self._require_input_open()
            return self.env.ensure_perception_worker().submit_report(report)

    def _enqueue_facts(self, facts):
        with self._input_lock:
            self._require_input_open()
            worker = self.env.ensure_perception_worker()
            handles = []
            for fact in facts:
                report = self._report(fact, self.source + (
                    "-map" if isinstance(fact, TemporaryObstacleObservation) else "-faults"))
                handles.append(worker.submit_report(report))
            return tuple(handles)

    def publish_facts(self, facts):
        with self.env.processing_lock:
            handles = self._enqueue_facts(facts)
            worker = self.env.perception_worker
        with self.env.run_operation(worker):
            return tuple(handle.result() for handle in handles)

    def set_agv_fault(self, agv_id, *, active, reason=None, remaining=0):
        """Apply the effect and enqueue its evidence before another scene operation."""
        with self.env.processing_lock, self._input_lock:
            self._require_input_open()
            worker = self.env.ensure_perception_worker()
            with self.env.run_operation(worker):
                if self.agv_binding.fault_control is None:
                    raise RuntimeError("AGV fault control is not configured for this scene")
                fact = (self.agv_binding.fault_control.inject_fault(agv_id, reason) if active else
                        self.agv_binding.fault_control.clear_fault(agv_id))
                handles = self._enqueue_facts((replace(fact, repair_remaining=remaining),))
        with self.env.run_operation(worker):
            report_outcome = handles[0].result()
            if not report_outcome.committed.applied:
                raise RuntimeError("scene fault report was rejected")
            return report_outcome

    def set_machine_fault(self, machine_id, *, active, reason=None, remaining=0):
        """Freeze local execution first, then publish the established availability."""
        with self.env.processing_lock, self._input_lock:
            self._require_input_open()
            worker = self.env.ensure_perception_worker()
            with self.env.run_operation(worker):
                if self.machine_binding.fault_control is None:
                    raise RuntimeError("machine fault control is not configured for this scene")
                fact = (self.machine_binding.fault_control.inject_fault(machine_id, reason) if active else
                        self.machine_binding.fault_control.clear_fault(machine_id))
                handles = self._enqueue_facts((replace(fact, repair_remaining=remaining),))
        with self.env.run_operation(worker):
            report_outcome = handles[0].result()
            if not report_outcome.committed.applied:
                raise RuntimeError("scene machine fault report was rejected")
            return report_outcome

    def configure_operations(self, profiles):
        configure = self.machine_binding.configure_simulation_operations
        if configure is not None:
            configure(profiles)

    def failure_priors(self):
        priors = {name: deepcopy(self.fault_injector.config[name])
                  for name in ("machine_failure", "agv_failure")}
        if not self.fault_injector.enabled:
            for prior in priors.values():
                prior["enabled"] = False
        return priors

    def machine_diagnostics(self, request_id):
        diagnostics = self.machine_binding.simulation_diagnostics
        return diagnostics(request_id) if diagnostics is not None else None

    def submit_agv_request(self, request):
        return self.agv_binding.execution_port.submit(request)

    def cancel_simulation_requests(self, request_ids):
        self.agv_binding.cancel_simulation_requests(request_ids)

    def submit_machine_request(self, request):
        return self.machine_binding.execution_port.submit(request)


    def step(self, provided_decision=None, *, evaluate_decision=False, run_worker):
        raise NotImplementedError("this scene does not provide simulation steps")

    def movement_groups(self, actions):
        raise NotImplementedError("scene must provide movement grouping")

    def record_movement_result(self, request, update):
        pass

    def release_movement_positions(self, request_ids):
        pass

    def check_position_reports(self, reports):
        pass

    def observable_positions(self):
        return None

    def can_block_cell(self, cell):
        with self.env.read_state():
            preserve = self.fault_injector.config.get("temporary_obstacle", {}).get("preserve_connectivity", True)
            return can_block_cell(self.env.state, self.env.public_grid_size, cell,
                                  preserve_connectivity=preserve)


    def check_due_faults(self):
        self.fault_injector.expire_effects(self.now())



class IndependentAgvAdapter(SceneAdapter):
    """Group single-vehicle commands and expose final coordinates when supplied."""
    def __init__(self, env, *, agv, machine, clock, position_source=None, initial_positions=None):
        super().__init__(env, agv=agv, machine=machine, clock=clock,
                         position_source=position_source, initial_positions=initial_positions)

    def step(self, provided_decision=None, *, evaluate_decision=False, run_worker):
        from sky_executor.simulation import run_simulation_step
        return run_simulation_step(self, provided_decision,
            evaluate_decision=evaluate_decision, run_worker=run_worker)

    def begin_simulation_effects(self, *, run_worker):
        with self.fault_injector.input_lock:
            with self.env.processing_lock:
                self.env.require_current_run(run_worker)
                self.env.events.begin_frame()
            self.fault_injector.trigger_scheduled(self.event_time())

    def finish_simulation_effects(self, *, run_worker):
        with self.fault_injector.input_lock:
            self.env.require_current_run(run_worker)
            self.check_due_faults()

    def movement_groups(self, actions):
        return tuple(((agv_id,), (action,)) for agv_id, action in enumerate(actions) if action)

    def record_movement_result(self, request, update):
        if update.positions is not None and self.position_source is None:
            with self._input_lock:
                reports = tuple(self._report(AgvObservation(agv_id, position), "scene-positions", request.request_id)
                                for agv_id, position in zip(request.agv_ids, update.positions))
                worker = self.env.ensure_perception_worker()
                for report in reports:
                    worker.submit_report(report)
