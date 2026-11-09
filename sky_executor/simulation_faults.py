"""Step-based random faults and grid obstacle candidates for simulation scenes."""
from __future__ import annotations
import math
import random
from typing import Any, Dict


class SimulationFaultSource:
    def __init__(self, scene):
        self.scene = scene
        self.config = scene.fault_injector.config
        self.reset()

    def reset(self, seed=None):
        seed = self.config.get("random_seed") if seed is None else int(seed) ^ 0x5EEDFA17
        self.rng = random.Random(seed)
        self._last_step = None

    def sample_step(self, step):
        with self.scene.fault_injector.input_lock:
            if self.scene.fault_injector.enabled and step != self._last_step:
                self._apply_probabilistic_events(self.scene.env.state)
                self._last_step = step

    def _prob_from_config(self, cfg: Dict[str, Any], prob_key: str, mean_key: str) -> float:
        prob = float(cfg.get(prob_key, 0.0) or 0.0)
        if prob > 0:
            return self._clamp_probability(prob)
        mean_steps = float(cfg.get(mean_key, 0.0) or 0.0)
        if mean_steps > 0:
            return self._clamp_probability(1.0 - math.exp(-1.0 / mean_steps))
        return 0.0


    def _sample_arrival_count(self, cfg: Dict[str, Any], prob_key: str, max_key: str) -> int:
        if not cfg.get("enabled"):
            return 0

        max_count = int(cfg.get(max_key, 1) or 1)
        if max_count <= 0:
            return 0

        lambda_per_step = float(cfg.get("lambda_per_step", 0.0) or 0.0)
        mean_steps = float(cfg.get("mean_interarrival_steps", 0.0) or 0.0)
        if lambda_per_step <= 0 and mean_steps > 0:
            lambda_per_step = 1.0 / mean_steps

        if lambda_per_step > 0:
            return min(max_count, self._sample_poisson(lambda_per_step))

        prob = self._clamp_probability(float(cfg.get(prob_key, 0.0) or 0.0))
        if max_count == 1:
            return 1 if self.rng.random() < prob else 0
        return sum(1 for _ in range(max_count) if self.rng.random() < prob)


    def _sample_poisson(self, lambda_per_step: float) -> int:
        if lambda_per_step <= 0:
            return 0
        threshold = math.exp(-lambda_per_step)
        count = 0
        product = 1.0
        while product > threshold:
            count += 1
            product *= self.rng.random()
        return max(0, count - 1)


    @staticmethod
    def _clamp_probability(value: float) -> float:
        return max(0.0, min(1.0, float(value)))


    def _apply_probabilistic_events(self, penv) -> None:
        cfg = self.config.get("machine_failure", {})
        if cfg.get("enabled"):
            prob = self._prob_from_config(cfg, "prob_per_machine_step", "mtbf_steps")
            busy_only = bool(cfg.get("busy_only", False))
            for m in penv.machines:
                if m.status != "OK":
                    continue
                if busy_only and m.current_op is None:
                    continue
                if self.rng.random() < prob:
                    self.scene.fault_injector.apply_event(dict(type="machine_breakdown", machine_id=m.id,
                        duration_steps=self._sample_duration(cfg.get("repair_time")), reason="probabilistic_machine_failure"))

        cfg = self.config.get("agv_failure", {})
        if cfg.get("enabled"):
            prob = self._prob_from_config(cfg, "prob_per_agv_step", "mtbf_steps")
            busy_only = bool(cfg.get("busy_only", False))
            for idx in range(penv.grid_config.num_agents):
                if penv.agv_status[idx] != "OK":
                    continue
                if busy_only and penv.agv_current_task[idx] is None:
                    continue
                if self.rng.random() < prob:
                    self.scene.fault_injector.apply_event(dict(type="agv_breakdown", agv_id=idx,
                        duration_steps=self._sample_duration(cfg.get("repair_time")), reason="probabilistic_agv_failure"))

        cfg = self.config.get("temporary_obstacle", {})
        for _ in range(self._sample_arrival_count(cfg, "prob_per_step", "max_new_per_step")):
            cell = self._choose_obstacle_cell(penv)
            if cell is not None:
                self.scene.fault_injector.apply_event(dict(type="temporary_obstacle", cell=cell,
                    duration_steps=self._sample_duration(cfg.get("duration")), reason="probabilistic_temporary_obstacle"))


    def _choose_obstacle_cell(self, penv):
        occupied = {tuple(penv._to_public_xy(pos)) for pos in penv.grid.positions_xy}
        machines = {tuple(m.location) for m in penv.machines}
        preserve = self.config.get("temporary_obstacle", {}).get("preserve_connectivity", True)
        candidates = []
        width, height = self.scene.env.public_grid_size
        for x in range(width):
            for y in range(height):
                cell = (x, y)
                internal = penv._to_internal_xy(cell)
                if cell in occupied or cell in machines or penv.grid.obstacles[internal] != 0:
                    continue
                if preserve and not self.scene.can_block_cell(cell):
                    continue
                candidates.append(cell)
        return self.rng.choice(candidates) if candidates else None


    def _sample_duration(self, spec) -> int:
        if spec is None:
            return 1
        if isinstance(spec, int):
            return max(1, spec)
        dist = str(spec.get("dist", "fixed")).lower()
        if dist == "fixed":
            return max(1, int(spec.get("value", 1)))
        if dist in {"uniform", "discrete_uniform"}:
            return max(1, self.rng.randint(int(spec.get("low", 1)), int(spec.get("high", 1))))
        if dist in {"triangular", "discrete_triangular"}:
            low = int(spec.get("low", 1))
            high = int(spec.get("high", low))
            mode = int(spec.get("mode", low))
            return max(1, int(round(self.rng.triangular(low, high, mode))))
        return max(1, int(spec.get("value", 1)))
