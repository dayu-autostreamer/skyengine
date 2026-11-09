"""Processing-time uncertainty for GridFactoryEnv.

This is not an Exception mechanism. It samples the actual operation duration
when a machine starts processing an operation, while keeping the nominal time
available for scheduling and display.
"""

from __future__ import annotations

import math
import random
import hashlib
from copy import deepcopy
from typing import Any, Optional


class ProcessingTimeSampler:
    PRESETS = {
        "none": {"enabled": False},
        "no_variance": {"enabled": False},
        "mild_variance": {
            "enabled": True,
            "default_distribution": {"dist": "multiplier_uniform", "low": 0.9, "high": 1.1},
        },
        "moderate_variance": {
            "enabled": True,
            "default_distribution": {"dist": "multiplier_uniform", "low": 0.8, "high": 1.2},
        },
        "high_variance": {
            "enabled": True,
            "default_distribution": {"dist": "multiplier_uniform", "low": 0.6, "high": 1.4},
        },
    }

    DEFAULT_CONFIG = {
        "enabled": False,
        "preset": "none",
        "random_seed": 42,
        "sample_on": "operation_start",
    }

    def __init__(self, config: Optional[dict] = None):
        self.raw_config = deepcopy(config) if isinstance(config, dict) else None
        self.config = normalize_processing_config(config)
        self.enabled = bool(self.config.get("enabled", False))
        self._seed = int(self.config.get("random_seed", 42))
        self._episode_seed = self._seed
        self.rng = random.Random(self._seed)

    @classmethod
    def from_config(cls, config: Optional[dict]) -> "ProcessingTimeSampler":
        return cls(config)

    def reset(self, seed: int | None = None):
        self._episode_seed = self._seed if seed is None else int(seed)
        self.rng = random.Random(self._episode_seed)

    def sample_for_operation(self, operation: Any, machine_id: int, nominal_time: float) -> tuple[float, Optional[dict]]:
        nominal = float(nominal_time or 0)
        if not self.enabled:
            return nominal, None

        dist = resolve_processing_distribution(self.config, operation, machine_id)
        if not dist:
            return nominal, None

        # Entity-keyed draws keep a scenario comparable when policies change
        # the order in which operations start. Durations remain continuous.
        key: str = f"{self._episode_seed}:processing:{operation.job_id}:{operation.op_id}:{machine_id}"
        self.rng = random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big"))
        sampled = self._sample_distribution(dist, nominal)
        return sampled, deepcopy(dist)

    def _sample_distribution(self, dist: dict, nominal: float) -> float:
        kind = str(dist.get("dist", "")).lower()
        unit: float = 1.0 if kind.startswith("multiplier_") else nominal
        family: str = kind.removeprefix("multiplier_")
        if family == "fixed":
            return nominal
        if family in {"uniform", "discrete_uniform", "triangular"}:
            low, high = float(dist.get("low", unit)), float(dist.get("high", unit))
            if low <= 0 or high < low:
                raise ValueError("processing duration bounds must satisfy 0 < low <= high")
            mean: float = (low + high) / 2.0
            if family == "triangular":
                mode: float = float(dist.get("mode", (low + high) / 2))
                if not low <= mode <= high:
                    raise ValueError("triangular mode must lie inside its bounds")
                mean = (low + high + mode) / 3.0
                draw = self.rng.triangular(low, high, mode)
            elif family == "discrete_uniform":
                if low != int(low) or high != int(high):
                    raise ValueError("discrete uniform bounds must be integers")
                draw = self.rng.randint(int(low), int(high))
            else:
                draw = self.rng.uniform(low, high)
            return nominal * draw / mean
        if family == "lognormal":
            sigma: float = float(dist.get("sigma", 0.2))
            if sigma < 0:
                raise ValueError("lognormal sigma must be nonnegative")
            return nominal * self.rng.lognormvariate(-sigma * sigma / 2, sigma)
        if family == "normal":
            mean, std = float(dist.get("mean", unit)), float(dist.get("std", 0))
            if mean <= 0 or std < 0:
                raise ValueError("normal processing parameters require mean > 0 and std >= 0")
            if std == 0:
                return nominal
            # Positive truncated normal, normalized by its analytic mean.
            alpha: float = mean / std
            positive_mean: float = mean + std * math.exp(-alpha * alpha / 2) / (math.sqrt(2 * math.pi) * (0.5 * (1 + math.erf(alpha / math.sqrt(2)))))
            draw = self.rng.gauss(mean, std)
            while draw <= 0:
                draw = self.rng.gauss(mean, std)
            return nominal * draw / positive_mean
        raise ValueError(f"unsupported processing distribution: {kind}")


def normalize_processing_config(config: Optional[dict]) -> dict:
    if not isinstance(config, dict):
        return deepcopy(ProcessingTimeSampler.DEFAULT_CONFIG)
    preset_name = config.get("preset", "none")
    preset = deepcopy(ProcessingTimeSampler.PRESETS.get(preset_name, {}))
    merged = deepcopy(ProcessingTimeSampler.DEFAULT_CONFIG)
    merged.update(preset)
    merged.update(deepcopy(config))
    if preset_name not in ("none", "no_variance") and "enabled" not in config:
        merged["enabled"] = True
    return merged


def resolve_processing_distribution(config, operation: Any, machine_id: int) -> Optional[dict]:
    op_cfg = getattr(operation, "processing_time_config", None)
    for cfg in (op_cfg, config):
        dist = _distribution_from_config(cfg, operation, machine_id)
        if dist:
            return dist
    return None


def _distribution_from_config(cfg: Any, operation: Any, machine_id: int) -> Optional[dict]:
    if not isinstance(cfg, dict):
        return None

    machine_dist = _lookup_machine_distribution(
        cfg.get("machine_distributions")
        or cfg.get("distributions_by_machine")
        or cfg.get("processing_time_distributions"),
        machine_id,
    )
    if machine_dist:
        return machine_dist

    op_dist = _lookup_operation_distribution(
        cfg.get("operation_distributions")
        or cfg.get("operations")
        or cfg.get("processing_time_distributions"),
        operation,
        machine_id,
    )
    if op_dist:
        return op_dist

    for key in ("distribution", "processing_time_distribution", "default_distribution"):
        value = cfg.get(key)
        if _looks_like_distribution(value):
            return value
    if _looks_like_distribution(cfg):
        return cfg
    return None


def _lookup_machine_distribution(mapping: Any, machine_id: int) -> Optional[dict]:
    if not isinstance(mapping, dict):
        return None
    value = mapping.get(str(machine_id), mapping.get(machine_id))
    return value if _looks_like_distribution(value) else None


def _lookup_operation_distribution(mapping: Any, operation: Any, machine_id: int) -> Optional[dict]:
    if not isinstance(mapping, dict):
        return None
    job_id = getattr(operation, "job_id", None)
    op_id = getattr(operation, "op_id", None)
    keys = [
        f"{job_id}:{op_id}",
        f"{job_id}.{op_id}",
        f"{job_id}-{op_id}",
        str(op_id),
        op_id,
    ]
    for key in keys:
        value = mapping.get(key)
        if _looks_like_distribution(value):
            return value
        if isinstance(value, dict):
            machine_value = _lookup_machine_distribution(
                value.get("machine_distributions")
                or value.get("distributions_by_machine")
                or value.get("processing_time_distributions"),
                machine_id,
            )
            if machine_value:
                return machine_value
            if _looks_like_distribution(value.get("distribution")):
                return value.get("distribution")
    return None


def _looks_like_distribution(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("dist"), str)
