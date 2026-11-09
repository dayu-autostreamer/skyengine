"""Formal CTDE-PPO training and frozen online execution adapters."""

from __future__ import annotations

import io
import itertools
import random
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass
from numbers import Real
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from experiment.algorithm_platform.models import (
    ArtifactKind,
    ArtifactRef,
    ComparisonMode,
    Direction,
    DecisionRequest,
    DecisionResponse,
    DecisionStatus,
    EventType,
    Feedback,
    MetricSet,
    ObjectiveComponent,
    ObjectiveSpec,
    RunContext,
    RunPurpose,
)
from experiment.algorithm_platform.objectives import ObjectiveEngine
from experiment.algorithm_platform.orchestrator import AlgorithmExecutionCancelled
from experiment.algorithm_platform.serialization import to_jsonable
from experiment.algorithm_platform.training_checkpoints import (
    checkpoint_directory, save_training_checkpoint, read_training_checkpoint,
)
from experiment.rl_platform import SkyEngineTrainingEnv
from experiment.rl_platform.api import Trajectory, Transition
from experiment.rl_platform.cpu_affinity import available_worker_cpus
from experiment.rl_platform.parallel_rollout import ParallelRolloutCollector
from sky_executor.runtime_log import serialize_action

from .domain import DFJSPTDataSplit, DFJSPT_URGENT_PRIORITY


ALGORITHM_ID = "ctde_ppo"
CHECKPOINT_SCHEMA_VERSION = 4
PPO_SELECTION_OBJECTIVE = ObjectiveSpec(
    mode=ComparisonMode.SINGLE,
    components=(ObjectiveComponent(name="episode_reward", metric="episode_reward", direction=Direction.MAXIMIZE),),
)


@dataclass
class _RolloutBatch:
    trajectories: list[Trajectory]
    first_episode: int
    policy_version: int
    started_at: str
    completed_at: str
    started_monotonic: float
    completed_monotonic: float
    sampling_statistics: dict[str, object]

    @property
    def seconds(self) -> float:
        return self.completed_monotonic - self.started_monotonic


class _FormalRolloutPolicy:
    """Keep unassigned transport work alive at the formal env boundary."""

    def __init__(self, policy):
        self._policy = policy

    @property
    def last_action_data(self):
        return self._policy.last_action_data

    def reset(self) -> None:
        self._policy.reset()

    def bootstrap_value(self, observation) -> float:
        return self._policy.bootstrap_value(observation)

    def act(self, observation, action_mask=None, deterministic=False):
        action = self._policy.act(
            observation,
            action_mask,
            deterministic=deterministic,
        )
        return action


class DFJSPTPPOTrainable:
    """Train CTDE-PPO in the formal headless SkyEngine environment."""

    def __init__(self, parameters: Mapping[str, object]):
        self._parameters = dict(parameters)
        self._policy = None
        self._trainer = None
        self._device = "cpu"
        self._policy_config: dict[str, object] = {}
        self._training_digests: frozenset[str] = frozenset()
        self._checkpoint_seeds: dict[str, int] = {}
        self._policy_version: int = 0
        self._barrier_round: int = 0
        self._pending_batch: _RolloutBatch | None = None
        self._training_evaluation: dict[str, float] = {}
        self._trained_sampling_jobs: set[int] = set()

    def _checkpoint_snapshot(self, context: RunContext, completed: int, steps: int,
                             training_digests: tuple[str, ...]) -> bytes:
        import torch
        import numpy as np

        policy_parameters: dict[str, object] = {**self._policy_config, "device": "cpu"}
        metadata = {
            "algorithm_id": ALGORITHM_ID, "run_id": context.run.run_id,
            "execution_id": context.execution_id, "completed_episodes": completed,
            "total_steps": steps, "created_at": datetime.now(timezone.utc).isoformat(),
            "model_captured_at": datetime.now(timezone.utc).isoformat(),
            "policy_version": self._policy_version,
            "parameters": dict(to_jsonable(self._parameters)),
            "training_scenario": {
                "id": context.run.scenario.scenario_id, "uri": context.run.scenario.uri,
                "digest": context.run.scenario.digest,
                "metadata": to_jsonable(context.run.scenario.metadata),
            },
        }
        payload = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION, "algorithm_id": ALGORITHM_ID,
            "policy_parameters": policy_parameters,
            "policy": {key: value.detach().cpu() for key, value in self._policy.state_dict().items()},
            "trainer": self._trainer.state_dict(), "completed_episodes": completed,
            "trained_sampling_jobs": sorted(self._trained_sampling_jobs),
            "total_steps": steps, "training_scenario_digests": training_digests,
            "seeds": dict(self._checkpoint_seeds),
            "pipeline": {"policy_version": self._policy_version, "barrier_round": self._barrier_round},
            "rng": {"python": random.getstate(), "numpy": np.random.get_state(),
                    "torch": torch.get_rng_state(),
                    "cuda": torch.cuda.get_rng_state_all() if self._device.startswith("cuda") else []},
        }
        buffer = io.BytesIO()
        torch.save((payload, metadata), buffer)
        return buffer.getvalue()

    def _save_checkpoint(self, context: RunContext, name: str, completed: int, steps: int,
                         training_digests: tuple[str, ...], selection_split: str,
                         metrics: Mapping[str, float], selection, selection_key,
                         *, snapshot: bytes | None = None) -> None:
        import torch

        if snapshot is None:
            snapshot = self._checkpoint_snapshot(context, completed, steps, training_digests)
        payload, metadata = torch.load(io.BytesIO(snapshot), map_location="cpu", weights_only=False)
        metadata.update({
            "created_at": datetime.now(timezone.utc).isoformat(), "selection_split": selection_split,
            "selection_sort_key": None if selection_key is None else list(selection_key),
            "selection_objective_values": [] if selection is None else list(selection.objective_values),
        })
        payload.update({"selection_split": selection_split, "selection_metrics": dict(metrics),
                        "selection_objective_values": metadata["selection_objective_values"],
                        "selection_sort_key": metadata["selection_sort_key"]})
        checkpoint_started: float = time.monotonic()
        record = save_training_checkpoint(checkpoint_directory(context.workspace_uri), name, payload, metadata)
        context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
            "phase": "checkpoint_saved", "episode": completed, "total_steps": steps,
            "checkpoint_seconds": time.monotonic() - checkpoint_started,
            "checkpoint": record, "message": f"已保存 {'最佳' if name == 'best' else '中间'} checkpoint，累计 {steps} 步",
        })

    def fit(
        self,
        training_data: DFJSPTDataSplit,
        validation_data: DFJSPTDataSplit | None,
        context: RunContext,
    ) -> tuple[ArtifactRef, ...]:
        if training_data.name != "training":
            raise ValueError("PPO fit requires a training data split")
        if not training_data.problems:
            raise ValueError("PPO training split must contain an instance")
        if context.run.objective != PPO_SELECTION_OBJECTIVE:
            raise ValueError("PPO 选模目标必须为单目标最大化验证平均累计奖励 episode_reward，请更新实验配置")

        torch, policy_type, reward_type, trainer_type = _algorithm_types()
        _seed_training(torch, context.run.seeds.algorithm)
        self._device = _resolve_device(torch, self._parameters, context)
        if not self._device.startswith("cuda"):
            raise ValueError("流水线 PPO 训练需要 GPU，请将训练设备设为 CUDA 并分配 GPU 预算")
        inherited_training_digests: tuple[str, ...] = ()
        resume_payload = None
        if context.run.input_artifacts:
            (
                self._policy,
                selected_artifact,
                inherited_training_digests,
                self._policy_config,
            ) = _load_policy(
                context.run.input_artifacts,
                self._device,
                context,
            )
            if selected_artifact.kind is ArtifactKind.CHECKPOINT:
                resume_payload = torch.load(context.artifact_resolver.resolve(selected_artifact), map_location="cpu", weights_only=False)
        else:
            self._policy_config = _policy_parameters(
                self._parameters,
                self._device,
            )
            self._policy = policy_type(**self._policy_config)
        self._trainer = trainer_type(
            policy=self._policy,
            device=self._device,
            gpu_ids=list(self._parameters.get("gpu_ids", ())),
            distributed=bool(self._parameters.get("distributed", False)),
            **_trainer_parameters(self._parameters),
        )
        completed_episodes: int = 0
        total_steps: int = 0
        algorithm_seed: int = context.run.seeds.algorithm
        environment_seed: int = context.run.seeds.environment
        if resume_payload is not None:
            import numpy as np
            self._trainer.load_state_dict(resume_payload["trainer"])
            completed_episodes = int(resume_payload["completed_episodes"])
            # Older full-batch checkpoints trained the contiguous prefix.
            self._trained_sampling_jobs = set(resume_payload["trained_sampling_jobs"]
                if "trained_sampling_jobs" in resume_payload else range(completed_episodes))
            total_steps = int(resume_payload["total_steps"])
            algorithm_seed = int(resume_payload["seeds"]["algorithm"])
            environment_seed = int(resume_payload["seeds"]["environment"])
            random.setstate(resume_payload["rng"]["python"])
            np.random.set_state(resume_payload["rng"]["numpy"])
            torch.set_rng_state(resume_payload["rng"]["torch"].cpu())
            if self._device.startswith("cuda") and resume_payload["rng"]["cuda"]:
                torch.cuda.set_rng_state_all([state.cpu() for state in resume_payload["rng"]["cuda"]])
            if "pipeline" in resume_payload:
                pipeline: dict = resume_payload["pipeline"]
                self._policy_version = pipeline["policy_version"]
                self._barrier_round = pipeline["barrier_round"]
            del resume_payload
        self._checkpoint_seeds = {"algorithm": algorithm_seed, "environment": environment_seed}

        episodes = int(self._parameters.get("episodes", 1000))
        for limit in (
            context.run.budget.max_iterations,
            context.run.budget.max_evaluations,
        ):
            if limit is not None:
                episodes = min(episodes, limit)
        if episodes <= 0:
            raise ValueError("episodes must be positive")
        if completed_episodes >= episodes:
            raise ValueError("训练总轮数必须大于 checkpoint 已完成轮数")
        # This queue is owned only by the sampling thread. Checkpoints record
        # trained IDs, so untrained/abandoned jobs are regenerated on resume.
        pending_job_ids: list[int] = list(itertools.islice(
            (job_id for job_id in itertools.count() if job_id not in self._trained_sampling_jobs),
            episodes - completed_episodes,
        ))
        max_steps = int(self._parameters.get("max_steps", 1000))
        if context.run.budget.max_steps is not None:
            max_steps = min(max_steps, context.run.budget.max_steps)
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")

        validation_interval = int(
            self._parameters.get("validation_interval", max(1, episodes // 10))
        )
        if validation_interval <= 0:
            raise ValueError("validation_interval must be positive")
        checkpoint_interval: int = int(self._parameters.get("checkpoint_interval_steps", 0))
        if checkpoint_interval < 0:
            raise ValueError("checkpoint_interval_steps must be non-negative")
        next_checkpoint: int = ((total_steps // checkpoint_interval) + 1) * checkpoint_interval if checkpoint_interval else 0
        training_digests: tuple[str, ...] = tuple(sorted({*inherited_training_digests, *(problem.scenario_digest for problem in training_data.problems)}))
        selection_data = validation_data or training_data
        started = time.monotonic()
        stats_history: list[dict[str, object]] = []
        validation_history: list[dict[str, object]] = []
        objective_engine = ObjectiveEngine(context.run.objective)
        best_key: tuple[float, ...] | None = None

        num_envs: int = min(int(self._parameters.get("num_envs", 4)), episodes - completed_episodes)
        dynamic_sampling: bool = self._parameters.get("dynamic_sampling", False)
        sampling_mode: str = "refill_until_each_worker_completed" if dynamic_sampling else "fixed_batch"
        evaluation_count: int = len(selection_data.problems) * int(self._parameters.get("evaluation_episodes", 1))
        evaluation_num_envs: int = min(int(self._parameters.get("evaluation_num_envs", 2)), evaluation_count)
        if num_envs < 1 or evaluation_num_envs < 1:
            raise ValueError("num_envs, evaluation_num_envs and evaluation_episodes must be positive")
        sampling_device: str = "cpu"
        evaluation_device: str = "cpu"
        worker_cpus: list[int] = available_worker_cpus()
        if len(worker_cpus) < num_envs + evaluation_num_envs:
            raise ValueError(f"采样与验证需要 {num_envs + evaluation_num_envs} 个独立 CPU 核心，"
                             f"当前可分配 {len(worker_cpus)} 个，请减少并行环境数")
        sampling_cpu_ids: list[int] = worker_cpus[:num_envs]
        evaluation_cpu_ids: list[int] = worker_cpus[num_envs:num_envs + evaluation_num_envs]
        policy_spec: dict = {"target": "dfjsp_t_rl.policy.DFJSPTPolicyPlugin", "kwargs": self._policy_config}
        reward_spec: dict = {"target": "dfjsp_t_rl.reward.SMDPMakespanReward", "kwargs": _reward_parameters(self._parameters)}
        collector = ParallelRolloutCollector(num_envs, policy_spec, reward_spec, SkyEngineTrainingEnv,
                                             _FormalRolloutPolicy, _formal_metrics, cpu_ids=sampling_cpu_ids)
        evaluation_collector = ParallelRolloutCollector(
            evaluation_num_envs, policy_spec, reward_spec, SkyEngineTrainingEnv,
            _FormalRolloutPolicy, _formal_metrics, evaluation=True, cpu_ids=evaluation_cpu_ids,
        )
        background_stop = threading.Event()
        pending_evaluations: list[Future] = []
        evaluation_scheduled: bool = False
        last_evaluation_episode: int = -1
        barrier_history: list[dict[str, object]] = []
        evaluation_directory: Path = checkpoint_directory(context.workspace_uri).parent / "evaluation_queue"
        evaluated_directory: Path = evaluation_directory.parent / "trash" / "evaluated_snapshots"
        evaluation_directory.mkdir(parents=True, exist_ok=True)
        evaluated_directory.mkdir(parents=True, exist_ok=True)

        def check_background() -> None:
            _raise_if_cancelled(context)
            if background_stop.is_set():
                raise AlgorithmExecutionCancelled("training pipeline stopped")

        def finish_evaluations(*, wait: bool = False) -> None:
            while pending_evaluations:
                future: Future = pending_evaluations[0]
                if not future.done():
                    if not wait:
                        return
                    check_background()
                    time.sleep(0.05)
                    continue
                future.result()
                pending_evaluations.pop(0)

        def evaluate_and_save(path: Path, completed: int, steps: int, version: int) -> None:
            nonlocal best_key
            check_background()
            snapshot: bytes = path.read_bytes()
            payload, _ = torch.load(io.BytesIO(snapshot), map_location="cpu", weights_only=False)
            weights = io.BytesIO()
            torch.save(payload["policy"], weights)
            del payload
            validation_metrics: dict[str, float] = _evaluate_snapshot(
                evaluation_collector, selection_data, self._parameters, context, weights.getvalue(), completed,
                environment_seed, algorithm_seed, background_stop, evaluation_device, version,
            )
            evaluation = objective_engine.evaluate_metrics((validation_metrics,))
            sort_key = _objective_selection_key(objective_engine, evaluation)
            validation_history.append({"episode": completed - 1, "policy_version": version,
                                       "metrics": validation_metrics,
                                       "objective_values": evaluation.objective_values, "feasible": evaluation.feasible})
            if best_key is None or sort_key < best_key:
                best_key = sort_key
                self._save_checkpoint(context, "best", completed, steps, training_digests,
                                      selection_data.name, validation_metrics, evaluation, sort_key, snapshot=snapshot)
            # Keep consumed temporary files in trash; never accumulate their payloads in RAM.
            path.rename(evaluated_directory / path.name)

        def schedule_evaluation(executor: ThreadPoolExecutor) -> None:
            nonlocal evaluation_scheduled, last_evaluation_episode
            finish_evaluations()
            path: Path = evaluation_directory / f"episode-{completed_episodes:08d}-v{self._policy_version:08d}.pt"
            path.write_bytes(self._checkpoint_snapshot(context, completed_episodes, total_steps, training_digests))
            pending_evaluations.append(executor.submit(
                evaluate_and_save, path, completed_episodes, total_steps, self._policy_version,
            ))
            evaluation_scheduled = True
            last_evaluation_episode = completed_episodes
            context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
                "phase": "evaluation_queued", "episode": completed_episodes, "policy_version": self._policy_version,
                "pending_evaluations": len(pending_evaluations),
                "message": f"第 {completed_episodes} 轮模型 V{self._policy_version} 已排入 CPU 验证队列，训练继续",
            })

        def collect_batch(first: int, weights: bytes, version: int, round_index: int) -> _RolloutBatch:
            nonlocal pending_job_ids
            job_ids: list[int] = pending_job_ids if dynamic_sampling else pending_job_ids[
                :min(num_envs, validation_interval - first % validation_interval)]
            count: int = min(num_envs, len(job_ids))
            jobs: list[dict] = [
                {"episode": episode, "instance": training_data.problems[episode % len(training_data.problems)].instance,
                 "seed": _episode_seed(environment_seed, episode),
                 "algorithm_seed": _episode_seed(algorithm_seed, episode)}
                for episode in job_ids
            ]
            collection_started: float = time.monotonic()
            started_at: str = datetime.now(timezone.utc).isoformat()
            context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
                "phase": "episode_started", "episode": first + 1,
                "episodes": episodes, "num_envs": count, "sampling_device": sampling_device,
                "sampling_mode": sampling_mode, "pending_jobs": len(jobs),
                "sampling_cpu_ids": sampling_cpu_ids[:count], "policy_version": version,
                "barrier_round": round_index, "sampling_started_at": started_at,
                "message": f"同步轮 {round_index}：{count} 个 CPU 使用 V{version} "
                           + ("动态领取任务，每个 worker 至少完成一次后同步" if dynamic_sampling
                              else "各采样一个回合，全部完成后同步"),
            })

            def publish_progress(episode: int, steps: int) -> None:
                context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
                    "phase": "collecting", "episode": first + 1, "sampling_job_id": episode,
                    "episodes": episodes,
                    "step": steps, "max_steps": max_steps, "num_envs": count,
                    "sampling_device": sampling_device, "policy_version": version, "barrier_round": round_index,
                    "message": f"同步轮 {round_index}：V{version} 采样任务 {episode + 1}，{steps}/{max_steps} 步",
                })

            trajectories: list[Trajectory] = collector.collect(jobs, None, max_steps, publish_progress,
                check_background, weights=weights, stop_after_each_worker=dynamic_sampling)
            completed_ids: set[int] = {int(item.metadata["episode"]) for item in trajectories}
            retry_ids: list[int] = collector.discarded_episode_ids
            attempted_ids: set[int] = completed_ids | set(retry_ids)
            pending_job_ids = retry_ids + [job_id for job_id in pending_job_ids if job_id not in attempted_ids]
            completed_monotonic: float = time.monotonic()
            completed_at: str = datetime.now(timezone.utc).isoformat()
            for trajectory in trajectories:
                trajectory.metadata["behavior_policy_version"] = version
            batch = _RolloutBatch(trajectories, first, version, started_at, completed_at,
                                  collection_started, completed_monotonic, dict(collector.round_statistics))
            context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
                "phase": "sampling_completed", "episode": first + len(trajectories), "batch_start_episode": first + 1,
                "policy_version": version, "barrier_round": round_index, "sampling_completed_at": completed_at,
                "sampling_seconds": batch.seconds, **batch.sampling_statistics,
                "message": f"同步轮 {round_index}：收集 {len(trajectories)} 个完整回合，"
                           + (f"丢弃 {len(retry_ids)} 个未接收任务（{collector.round_statistics['discarded_steps']} 步），"
                              "下一轮优先重跑；" if retry_ids else "")
                           + f"耗时 {batch.seconds:.2f} 秒",
            })
            return batch

        def stop_background() -> None:
            background_stop.set()
            for future in pending_evaluations:
                future.cancel()

        context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
            "phase": "pipeline_started", "device": self._device, "sampling_device": "cpu", "evaluation_device": "cpu",
            "sampling_cpu_ids": sampling_cpu_ids, "evaluation_cpu_ids": evaluation_cpu_ids,
            "max_policy_lag": 1,
            "message": f"流水线启动：采样 CPU {sampling_cpu_ids}，训练 {self._device}，验证 CPU {evaluation_cpu_ids}",
        })
        with ExitStack() as stack:
            evaluation_executor = stack.enter_context(ThreadPoolExecutor(max_workers=1, thread_name_prefix="ppo-evaluation"))
            sampling_executor = stack.enter_context(ThreadPoolExecutor(max_workers=1, thread_name_prefix="ppo-sampling"))
            stack.enter_context(collector)
            stack.enter_context(evaluation_collector)
            stack.callback(stop_background)
            if completed_episodes:
                schedule_evaluation(evaluation_executor)
            # Resume starts by resampling from the saved trained-episode count.
            weights = io.BytesIO()
            torch.save({key: value.detach().cpu() for key, value in self._policy.state_dict().items()}, weights)
            self._pending_batch = collect_batch(completed_episodes, weights.getvalue(),
                                                self._policy_version, self._barrier_round)
            del weights
            warmup: dict[str, object] = {
                "phase": "barrier_completed", "barrier_round": self._barrier_round, "stage": "warmup",
                "sampling_start_episode": self._pending_batch.first_episode + 1,
                "sampling_end_episode": self._pending_batch.first_episode + len(self._pending_batch.trajectories),
                "sampling_policy_version": self._policy_version,
                "sampling_started_at": self._pending_batch.started_at,
                "sampling_completed_at": self._pending_batch.completed_at,
                "sampling_seconds": self._pending_batch.seconds, "training_completed_at": None,
                "sampling_statistics": self._pending_batch.sampling_statistics,
                "training_seconds": None, "sampling_wait_seconds": 0.0, "training_wait_seconds": 0.0,
                "barrier_released_at": datetime.now(timezone.utc).isoformat(),
                "message": "首批采样完成，进入采样与训练并行阶段",
            }
            barrier_history.append(warmup)
            context.event_publisher.emit(EventType.TRAINING_PROGRESS, warmup)

            while self._pending_batch is not None:
                check_background()
                finish_evaluations()
                wall_time: float | None = context.run.budget.wall_time_seconds
                if stats_history and wall_time is not None and time.monotonic() - started >= wall_time:
                    break
                current: _RolloutBatch = self._pending_batch
                batch_count: int = len(current.trajectories)
                first_episode: int = current.first_episode
                next_episode: int = first_episode + batch_count
                policy_lag: int = self._policy_version - current.policy_version
                if policy_lag not in (0, 1):
                    raise RuntimeError(f"采样策略 V{current.policy_version} 与训练策略 V{self._policy_version} 相差 {policy_lag} 轮")
                self._barrier_round += 1
                version_before: int = self._policy_version
                next_sampling: Future | None = None
                if next_episode < episodes and (wall_time is None or time.monotonic() - started < wall_time):
                    # Freeze before update: the sampler must never read live learner tensors.
                    weights = io.BytesIO()
                    torch.save({key: value.detach().cpu() for key, value in self._policy.state_dict().items()}, weights)
                    next_sampling = sampling_executor.submit(collect_batch, next_episode, weights.getvalue(),
                                                              version_before, self._barrier_round)
                    del weights
                transition_count: int = sum(int(item.metadata["simulation_steps"]) for item in current.trajectories)
                decision_count: int = sum(len(item.transitions) for item in current.trajectories)
                update_started_at: str = datetime.now(timezone.utc).isoformat()
                update_started: float = time.monotonic()
                context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
                    "phase": "updating", "episode": first_episode + 1, "episodes": episodes,
                    "batch_end_episode": next_episode, "num_envs": num_envs, "batch_episodes": batch_count,
                    "steps": transition_count,
                    "transitions": decision_count, "device": self._device, "barrier_round": self._barrier_round,
                    "behavior_policy_version": current.policy_version, "learner_policy_version": version_before,
                    "policy_lag": policy_lag, "training_started_at": update_started_at,
                    "message": f"同步轮 {self._barrier_round}：GPU 训练第 {first_episode + 1}—{next_episode} 回合，"
                               f"采样 V{current.policy_version} / 训练 V{version_before}，滞后 {policy_lag} 轮",
                })
                def publish_update_progress(progress: dict) -> None:
                    stage: str = {"history": "重算历史", "forward": "片段前向",
                                  "backward": "反向传播", "minibatch_completed": "小批更新完成"}[progress["update_stage"]]
                    context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
                        "phase": "update_progress", "episode": first_episode + 1, "episodes": episodes,
                        "batch_end_episode": next_episode, "barrier_round": self._barrier_round,
                        "device": self._device, "training_started_at": update_started_at, **progress,
                        "message": f"同步轮 {self._barrier_round}：GPU {stage}，"
                                   f"epoch {progress['epoch']}/{progress['epochs']}，"
                                   f"小批 {progress['minibatch']}/{progress['minibatches']}，"
                                   f"已更新 {progress['optimizer_steps']}/{progress['optimizer_steps_total']} 次，"
                                   f"耗时 {progress['elapsed_seconds']:.1f} 秒",
                    })

                update: dict = self._trainer.update(current.trajectories, cancel_check=check_background,
                                                   progress_callback=publish_update_progress)
                torch.cuda.synchronize(self._device)
                update_finished: float = time.monotonic()
                update_completed_at: str = datetime.now(timezone.utc).isoformat()
                update_seconds: float = update_finished - update_started
                if update["updated"]:
                    self._policy_version += 1
                context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
                    "phase": "update_completed", "episode": next_episode, "batch_start_episode": first_episode + 1,
                    "episodes": episodes, "total_steps": total_steps + transition_count,
                    "barrier_round": self._barrier_round, "behavior_policy_version": current.policy_version,
                    "learner_policy_version": version_before, "policy_version": self._policy_version,
                    "policy_lag": policy_lag, "training_started_at": update_started_at,
                    "training_completed_at": update_completed_at,
                    "batch_collection_seconds": current.seconds, "batch_update_seconds": update_seconds,
                    "device": self._device, "trainer": dict(to_jsonable(update)),
                    "message": f"同步轮 {self._barrier_round}：GPU 更新完成，耗时 {update_seconds:.2f} 秒，模型 V{self._policy_version}",
                })
                for offset, trajectory in enumerate(current.trajectories):
                    job_id: int = int(trajectory.metadata["episode"])
                    episode: int = first_episode + offset
                    self._trained_sampling_jobs.add(job_id)
                    steps: int = int(trajectory.metadata["simulation_steps"])
                    episode_metrics: dict = trajectory.metadata["metrics"]
                    stats_history.append({
                        "episode": episode, "sampling_job_id": job_id,
                        "transitions": len(trajectory.transitions), "simulation_steps": steps,
                        "num_envs": num_envs, "collection_seconds": trajectory.metadata["collection_seconds"],
                        "batch_collection_seconds": current.seconds, "batch_update_seconds": update_seconds,
                        "behavior_policy_version": current.policy_version, "policy_lag": policy_lag,
                        "trainer": dict(to_jsonable(update)), "metrics": episode_metrics,
                    })
                    context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
                        "phase": "episode_completed", "episode": episode + 1, "episodes": episodes, "steps": steps,
                        "sampling_job_id": job_id,
                        "device": self._device, "num_envs": num_envs, "metrics": episode_metrics,
                        "message": f"第 {episode + 1}/{episodes} 回合训练完成（采样任务 {job_id + 1}），共 {steps} 仿真步，"
                                   f"累计奖励 {episode_metrics['episode_reward']:.4f}",
                    })
                    trajectory.transitions.clear()
                current.trajectories.clear()
                self._policy.last_action_data = None
                completed_episodes += batch_count
                total_steps += transition_count
                if next_sampling is not None:
                    while not next_sampling.done():
                        check_background()
                        finish_evaluations()
                        time.sleep(0.05)
                    self._pending_batch = next_sampling.result()
                else:
                    self._pending_batch = None
                sampled: _RolloutBatch | None = self._pending_batch
                sampling_wait: float = 0.0 if sampled is None else max(0.0, update_finished - sampled.completed_monotonic)
                training_wait: float = 0.0 if sampled is None else max(0.0, sampled.completed_monotonic - update_finished)
                barrier: dict[str, object] = {
                    "phase": "barrier_completed", "barrier_round": self._barrier_round,
                    "stage": "drain" if sampled is None else "overlap",
                    "episode": completed_episodes, "total_steps": total_steps,
                    "sampling_start_episode": None if sampled is None else sampled.first_episode + 1,
                    "sampling_end_episode": None if sampled is None else sampled.first_episode + len(sampled.trajectories),
                    "sampling_policy_version": None if sampled is None else sampled.policy_version,
                    "sampling_started_at": None if sampled is None else sampled.started_at,
                    "sampling_completed_at": None if sampled is None else sampled.completed_at,
                    "sampling_seconds": None if sampled is None else sampled.seconds,
                    "sampling_statistics": None if sampled is None else sampled.sampling_statistics,
                    "training_start_episode": first_episode + 1, "training_end_episode": completed_episodes,
                    "training_behavior_policy_version": current.policy_version,
                    "training_policy_version_before": version_before, "training_policy_version_after": self._policy_version,
                    "training_started_at": update_started_at, "training_completed_at": update_completed_at,
                    "training_seconds": update_seconds, "policy_lag": policy_lag,
                    "sampling_wait_seconds": sampling_wait, "training_wait_seconds": training_wait,
                    "barrier_released_at": datetime.now(timezone.utc).isoformat(),
                    "message": f"同步轮 {self._barrier_round} 完成：采样等待训练 {sampling_wait:.2f} 秒，"
                               f"训练等待采样 {training_wait:.2f} 秒",
                }
                barrier_history.append(barrier)
                context.event_publisher.emit(EventType.TRAINING_PROGRESS, barrier)
                if checkpoint_interval and total_steps >= next_checkpoint:
                    self._save_checkpoint(context, f"step-{total_steps:012d}", completed_episodes, total_steps,
                                          training_digests, "unevaluated", {}, None, None)
                    next_checkpoint = (total_steps // checkpoint_interval + 1) * checkpoint_interval
                stopping: bool = sampled is None or (wall_time is not None and time.monotonic() - started >= wall_time)
                should_validate: bool = (not evaluation_scheduled or
                    completed_episodes // validation_interval > first_episode // validation_interval or stopping)
                if should_validate:
                    schedule_evaluation(evaluation_executor)
                finish_evaluations()
            if completed_episodes != last_evaluation_episode:
                schedule_evaluation(evaluation_executor)
            context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
                "phase": "evaluation_draining", "episode": completed_episodes,
                "pending_evaluations": len(pending_evaluations),
                "message": f"采样和训练已结束，剩余 {len(pending_evaluations)} 个模型等待验证完成后选出最佳模型",
            })
            finish_evaluations(wait=True)
        _raise_if_cancelled(context)
        if not stats_history:
            raise TimeoutError("training budget expired before the first episode")
        best_metadata, best_bytes = read_training_checkpoint(checkpoint_directory(context.workspace_uri) / "best.ckpt")
        best_checkpoint = torch.load(io.BytesIO(best_bytes), map_location="cpu", weights_only=False)
        self._policy.load_state_dict(best_checkpoint["policy"])
        self._trainer.load_state_dict(best_checkpoint["trainer"])
        _raise_if_cancelled(context)
        selection_metrics: dict[str, float] = dict(best_checkpoint["selection_metrics"])
        self._training_evaluation = dict(selection_metrics)
        del best_checkpoint
        selection = objective_engine.evaluate_metrics((selection_metrics,))
        selection_key = _objective_selection_key(objective_engine, selection)
        policy_parameters = dict(self._policy_config)
        policy_parameters["device"] = "cpu"
        policy_state = {
            name: value.detach().cpu()
            for name, value in self._policy.state_dict().items()
        }
        provenance = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "algorithm_id": ALGORITHM_ID,
            "policy_version": best_metadata["policy_version"],
            "policy_parameters": policy_parameters,
            "policy": policy_state,
            "training_scenario_digests": tuple(
                sorted(
                    {
                        *inherited_training_digests,
                        *(
                            problem.scenario_digest
                            for problem in training_data.problems
                        ),
                    }
                )
            ),
            "selection_split": selection_data.name,
            "selection_metrics": selection_metrics,
            "selection_objective_values": selection.objective_values,
        }
        self._training_digests = frozenset(
            provenance["training_scenario_digests"]
        )

        model_buffer = io.BytesIO()
        torch.save(provenance, model_buffer)
        artifact_metadata = {
            "algorithm_id": ALGORITHM_ID,
            "policy_version": best_metadata["policy_version"],
            "format": "pytorch_state_dict",
            "selection_split": selection_data.name,
            "selection_sort_key": tuple(selection_key),
            "selection_objective_values": selection.objective_values,
        }
        model = context.artifact_publisher.publish_bytes(
            model_buffer.getvalue(),
            kind=ArtifactKind.MODEL,
            media_type="application/x-pytorch",
            metadata=artifact_metadata,
        )

        checkpoint = context.artifact_publisher.publish_bytes(
            best_bytes,
            kind=ArtifactKind.CHECKPOINT,
            media_type="application/x-pytorch",
            metadata={**artifact_metadata, **best_metadata},
        )
        report = context.artifact_publisher.publish_json(
            {
                "schema_version": 1,
                "algorithm_id": ALGORITHM_ID,
                "completed_episodes": completed_episodes,
                "total_steps": total_steps,
                "checkpoint_interval_steps": checkpoint_interval,
                "best_checkpoint_steps": best_metadata["total_steps"],
                "requested_episodes": episodes,
                "num_envs": num_envs,
                "sampling_device": sampling_device,
                "evaluation_device": evaluation_device,
                "evaluation_num_envs": evaluation_num_envs,
                "sampling_cpu_ids": sampling_cpu_ids,
                "evaluation_cpu_ids": evaluation_cpu_ids,
                "max_policy_lag": 1,
                "barrier_history": tuple(barrier_history),
                "sampling_mode": sampling_mode,
                "dynamic_sampling": dynamic_sampling,
                "trained_sampling_jobs": sorted(self._trained_sampling_jobs),
                "latest_policy_version": self._policy_version,
                "best_policy_version": best_metadata["policy_version"],
                "max_steps": max_steps,
                "device": self._device,
                "gpu_ids": tuple(self._parameters.get("gpu_ids", ())),
                "distributed": bool(
                    self._parameters.get("distributed", False)
                ),
                "last_training_episode": stats_history[-1],
                "validation_history": tuple(validation_history),
                "selection_split": selection_data.name,
                "selection_metrics": selection_metrics,
                "selection_objective_values": selection.objective_values,
            },
            kind=ArtifactKind.REPORT,
            metadata={
                "algorithm_id": ALGORITHM_ID,
                "report_type": "training_summary",
            },
        )
        return model, checkpoint, report

    def load_artifacts(
        self,
        artifacts: Sequence[ArtifactRef],
        context: RunContext,
    ) -> None:
        torch, _, _, _ = _algorithm_types()
        self._device = _resolve_device(torch, self._parameters, context)
        self._policy, _, training_digests, self._policy_config = _load_policy(
            artifacts,
            self._device,
            context,
        )
        self._training_digests = frozenset(training_digests)

    def evaluate(
        self,
        evaluation_data: DFJSPTDataSplit,
        context: RunContext,
    ) -> MetricSet:
        _raise_if_cancelled(context)
        if self._policy is None:
            raise RuntimeError("PPO policy has not been trained or loaded")
        if context.run.purpose is RunPurpose.TRAIN:
            # fit restored this exact checkpoint after its CPU validation.
            return dict(self._training_evaluation)
        evaluation_digests = {
            problem.scenario_digest
            for problem in evaluation_data.problems
        }
        if self._training_digests.intersection(evaluation_digests):
            raise ValueError(
                "frozen evaluation data overlaps the model training corpus"
            )
        return _evaluate_policy(
            self._policy,
            evaluation_data,
            self._parameters,
            context,
            seed_offset=3_000_000,
        )


class FrozenDFJSPTPPOPolicy:
    """Run a published PPO model through the online decision protocol."""

    def __init__(self, parameters: Mapping[str, object]):
        self._parameters = dict(parameters)
        self._context: RunContext | None = None
        self._policy = None
        self._trajectory: list[dict[str, object]] = []
        self._selected_artifact: ArtifactRef | None = None

    def initialize(self, context: RunContext) -> None:
        if not context.run.input_artifacts:
            raise ValueError("frozen PPO online execution requires a model")
        torch, _, _, _ = _algorithm_types()
        device = _resolve_device(torch, self._parameters, context)
        self._policy, self._selected_artifact, _, _ = _load_policy(
            context.run.input_artifacts,
            device,
            context,
        )
        self._policy.reset()
        self._context = context
        self._trajectory.clear()

    def decide(
        self,
        request: DecisionRequest[Mapping[str, object]],
    ) -> DecisionResponse[dict[str, object]]:
        # Requests are deeply frozen; the algorithm owns and copies its input.
        policy_observation = {"planning_observation": to_jsonable(request.observation["planning_observation"])}
        native_action = self._policy.act(
            policy_observation,
            deterministic=True,
        )
        action = {"native_action": serialize_action(native_action)}
        return DecisionResponse(
            request_id=request.request_id,
            status=DecisionStatus.FEASIBLE,
            action=action,
            diagnostics={
                "policy": ALGORITHM_ID,
                "deterministic": True,
                "model_digest": self._selected_artifact.digest,
                **self._policy.diagnostics,
            },
        )

    def observe(
        self,
        feedback: Feedback[
            Mapping[str, object],
            Mapping[str, object],
        ],
    ) -> None:
        self._trajectory.append(
            {
                "request_id": feedback.request_id,
                "accepted": feedback.accepted,
                "simulation_time": feedback.simulation_time,
                "state_version": feedback.state_version,
                "proposed_action": to_jsonable(feedback.proposed_action),
                "executed_action": to_jsonable(feedback.executed_action),
                "metrics": dict(feedback.metrics),
                "terminated": feedback.terminated,
                "rejection_reason": feedback.rejection_reason,
            }
        )

    def finalize(self) -> tuple[ArtifactRef, ...]:
        if self._context is None or self._selected_artifact is None:
            raise RuntimeError("frozen PPO policy was not initialized")
        trajectory = self._context.artifact_publisher.publish_json(
            {
                "schema_version": 1,
                "algorithm_id": ALGORITHM_ID,
                "model_digest": self._selected_artifact.digest,
                "deterministic": True,
                "steps": tuple(self._trajectory),
            },
            kind=ArtifactKind.SOLUTION,
            metadata={
                "algorithm_id": ALGORITHM_ID,
                "solution_type": "online_trajectory",
                "model_digest": self._selected_artifact.digest,
            },
        )
        return (trajectory,)


def _algorithm_types():
    import torch
    from dfjsp_t_rl.policy import DFJSPTPolicyPlugin
    from dfjsp_t_rl.reward import SMDPMakespanReward
    from dfjsp_t_rl.trainer import CTDEPPOTrainer

    return torch, DFJSPTPolicyPlugin, SMDPMakespanReward, CTDEPPOTrainer


def _seed_training(torch, seed: int) -> None:
    import numpy

    random.seed(seed)
    numpy.random.seed(seed % (2**32 - 1))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _policy_parameters(
    parameters: Mapping[str, object],
    device: str,
) -> dict[str, object]:
    result = {
        "hidden_dim": int(parameters.get("hidden_dim", 128)),
        "max_production_actions": int(
            parameters.get("max_production_actions", 32)
        ),
        "max_logistics_actions": int(
            parameters.get("max_logistics_actions", 32)
        ),
        "device": device,
        "candidate_limit": int(parameters.get("candidate_limit", 24)),
        "scenario_count": int(parameters.get("scenario_count", 8)),
        "search_seconds": float(parameters.get("search_seconds", 0.0)),
        "routing_horizon": int(parameters.get("routing_horizon", 24)),
        "decision_interval": int(parameters.get("decision_interval", 5)),
        "inference_budget_ms": float(parameters.get("inference_budget_ms", 300.0)),
    }
    return result


def _reward_parameters(parameters: Mapping[str, object]) -> dict[str, object]:
    return {
        "horizon": float(parameters.get("reward_horizon", 1000.0)),
        "shaping_scale": float(parameters.get("shaping_scale", 0.1)),
    }


def _trainer_parameters(parameters: Mapping[str, object]) -> dict[str, object]:
    return {
        "learning_rate": float(parameters.get("learning_rate", 3e-4)),
        "gamma": float(parameters.get("gamma", 1.0)),
        "gae_lambda": float(parameters.get("gae_lambda", 0.95)),
        "clip_ratio": float(parameters.get("clip_ratio", 0.2)),
        "epochs": int(parameters.get("ppo_epochs", 4)),
        "value_coef": float(parameters.get("value_coef", 0.5)),
        "entropy_coef": float(parameters.get("entropy_coef", 0.01)),
        "minibatch_size": int(parameters.get("minibatch_size", 64)),
        "sequence_length": int(parameters.get("sequence_length", 32)),
        "graph_batch_size": int(parameters.get("graph_batch_size", 16)),
        "input_cache_mb": int(parameters.get("input_cache_mb", 256)),
    }


def _resolve_device(torch, parameters: Mapping[str, object], context: RunContext) -> str:
    requested = str(parameters.get("device", "auto"))
    gpu_ids = tuple(int(value) for value in parameters.get("gpu_ids", ()))
    gpu_budget = context.run.budget.gpu_count
    if gpu_budget is not None and len(gpu_ids) > gpu_budget:
        raise ValueError("gpu_ids exceed the run GPU budget")
    if requested == "auto":
        if gpu_budget == 0:
            return "cpu"
        if torch.cuda.is_available():
            return f"cuda:{gpu_ids[0] if gpu_ids else 0}"
        if gpu_budget is not None and gpu_budget > 0:
            raise RuntimeError("the run requests a GPU but CUDA is unavailable")
        return "cpu"
    if requested.startswith("cuda"):
        if gpu_budget == 0:
            raise ValueError("CUDA execution conflicts with a zero-GPU run budget")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA execution was requested but CUDA is unavailable")
    if requested == "cuda" and gpu_ids:
        return f"cuda:{gpu_ids[0]}"
    return requested


def _load_policy(
    artifacts: Sequence[ArtifactRef],
    device: str,
    context: RunContext,
):
    torch, policy_type, _, _ = _algorithm_types()
    candidates = tuple(
        artifact
        for artifact in artifacts
        if artifact.kind in {ArtifactKind.MODEL, ArtifactKind.CHECKPOINT}
    )
    if not candidates:
        raise ValueError("PPO requires a MODEL or CHECKPOINT artifact")
    models = tuple(
        artifact
        for artifact in candidates
        if artifact.kind is ArtifactKind.MODEL
    )
    selected = min(models or candidates, key=_artifact_selection_key)
    payload = torch.load(
        context.artifact_resolver.resolve(selected),
        map_location="cpu",
        weights_only=False,
    )
    if payload["algorithm_id"] != ALGORITHM_ID:
        raise ValueError("artifact was produced by a different algorithm")
    if payload["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError("控制器已升级为可执行事务策略，请使用第四版 checkpoint 或从头训练")
    policy_parameters = dict(payload["policy_parameters"])
    policy_parameters["device"] = device
    policy = policy_type(**policy_parameters)
    policy.load_state_dict(payload["policy"])
    policy.model.eval()
    return (
        policy,
        selected,
        tuple(str(value) for value in payload["training_scenario_digests"]),
        dict(payload["policy_parameters"]),
    )


def _artifact_selection_key(artifact: ArtifactRef) -> tuple[object, ...]:
    value = artifact.metadata.get("selection_sort_key")
    if value is None:
        return (1, artifact.digest)
    return (0, *tuple(value), artifact.digest)


def _objective_selection_key(engine, evaluation) -> tuple[float, ...]:
    if engine.spec.mode is not ComparisonMode.PARETO:
        return engine.sort_key(evaluation)
    key: list[float] = []
    if engine.spec.feasibility_first:
        key.extend(
            (
                0.0 if evaluation.feasible else 1.0,
                float(evaluation.violated_constraint_count),
                evaluation.total_constraint_violation,
            )
        )
    for component, value in zip(
        engine.spec.components,
        evaluation.objective_values,
        strict=True,
    ):
        key.append(value if component.direction.value == "minimize" else -value)
    return tuple(key)


def _evaluate_snapshot(collector: ParallelRolloutCollector, data: DFJSPTDataSplit,
                       parameters: Mapping[str, object], context: RunContext, weights: bytes,
                       completed: int, environment_seed: int, algorithm_seed: int,
                       stop_event: threading.Event, device: str, policy_version: int) -> dict[str, float]:
    """Evaluate one immutable version in dedicated workers, without learner state."""
    max_steps: int = int(parameters.get("evaluation_max_steps", parameters.get("max_steps", 1000)))
    if context.run.budget.max_steps is not None:
        max_steps = min(max_steps, context.run.budget.max_steps)
    repetitions: int = int(parameters.get("evaluation_episodes", 1))
    if max_steps <= 0 or repetitions <= 0:
        raise ValueError("evaluation_max_steps and evaluation_episodes must be positive")
    jobs: list[dict] = []
    for problem_index, problem in enumerate(data.problems):
        for repetition in range(repetitions):
            index: int = problem_index * repetitions + repetition
            jobs.append({"episode": index, "instance": problem.instance,
                         "seed": _episode_seed(environment_seed, 1_000_000 + index),
                         "algorithm_seed": _episode_seed(algorithm_seed, 1_000_000 + index)})
    started: float = time.monotonic()
    context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
        "phase": "evaluating", "episode": completed, "selection_split": data.name,
        "policy_version": policy_version,
        "evaluation_episodes": len(jobs), "evaluation_max_steps": max_steps,
        "evaluation_device": device, "evaluation_num_envs": collector.num_envs,
        "message": f"CPU 后台验证第 {completed} 回合模型 V{policy_version}，{collector.num_envs} 个环境，共 {len(jobs)} 回合",
    })

    def check_cancelled() -> None:
        _raise_if_cancelled(context)
        if stop_event.is_set():
            raise AlgorithmExecutionCancelled("background evaluation stopped")

    def progress(index: int, steps: int) -> None:
        context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
            "phase": "evaluating", "episode": completed, "evaluation_episode": index + 1,
            "policy_version": policy_version,
            "evaluation_episodes": len(jobs), "step": steps, "max_steps": max_steps,
            "message": f"CPU 验证模型 V{policy_version}：回合 {index + 1}/{len(jobs)}，{steps}/{max_steps} 步",
        })

    episode_metrics: list[dict[str, float]] = []
    for first in range(0, len(jobs), collector.num_envs):
        trajectories = collector.collect(jobs[first:first + collector.num_envs], None, max_steps,
                                          progress, check_cancelled, weights=weights)
        episode_metrics.extend(trajectory.metadata["metrics"] for trajectory in trajectories)
    summary: dict[str, float] = _summarize_evaluation(episode_metrics)
    elapsed: float = time.monotonic() - started
    context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
        "phase": "evaluation_completed", "episode": completed, "selection_split": data.name,
        "policy_version": policy_version,
        "evaluation_seconds": elapsed, "metrics": summary,
        "message": f"第 {completed} 回合模型 V{policy_version} 验证完成，{len(jobs)} 回合耗时 {elapsed:.2f} 秒",
    })
    return summary


def _summarize_evaluation(episode_metrics: list[dict[str, float]]) -> dict[str, float]:
    keys: list[str] = sorted({key for metrics in episode_metrics for key in metrics})
    summary: dict[str, float] = {
        key: sum(metrics[key] for metrics in episode_metrics if key in metrics)
        / sum(1 for metrics in episode_metrics if key in metrics)
        for key in keys
    }
    successful: list[float] = sorted(metrics["C_max"] for metrics in episode_metrics if metrics["success_rate"] == 1.0)
    summary["tail_completed_episodes"] = float(len(successful))
    if successful:
        tail: list[float] = successful[min(len(successful) - 1, int(.95 * len(successful))):]
        summary["C_max_p95_completed"] = tail[0]
        summary["C_max_cvar95_completed"] = sum(tail) / len(tail)
    return summary


def _evaluate_policy(
    policy,
    data: DFJSPTDataSplit,
    parameters: Mapping[str, object],
    context: RunContext,
    *,
    seed_offset: int,
    seed_base: int | None = None,
    training_episode: int | None = None,
) -> dict[str, float]:
    max_steps = int(parameters.get("evaluation_max_steps", parameters.get("max_steps", 1000)))
    if context.run.budget.max_steps is not None:
        max_steps = min(max_steps, context.run.budget.max_steps)
    repetitions = int(parameters.get("evaluation_episodes", 1))
    if max_steps <= 0 or repetitions <= 0:
        raise ValueError("evaluation_max_steps and evaluation_episodes must be positive")
    evaluation_started: float = time.monotonic()
    _, _, reward_type, _ = _algorithm_types()
    reward = reward_type(**_reward_parameters(parameters))
    evaluation_count: int = len(data.problems) * repetitions
    if training_episode is not None:
        context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
            "phase": "evaluating", "episode": training_episode, "selection_split": data.name,
            "evaluation_episodes": evaluation_count, "evaluation_max_steps": max_steps,
            "message": f"开始模型选择评估：{data.name}，共 {evaluation_count} 回合，每回合最多 {max_steps} 步",
        })
    episode_metrics: list[dict[str, float]] = []
    for problem_index, problem in enumerate(data.problems):
        _raise_if_cancelled(context)
        for repetition in range(repetitions):
            _raise_if_cancelled(context)
            env = SkyEngineTrainingEnv(problem.instance)
            try:
                policy.reset()
                observation, _ = env.reset(
                    seed=_episode_seed(
                        context.run.seeds.environment if seed_base is None else seed_base,
                        seed_offset + problem_index * repetitions + repetition,
                    )
                )
                before_metrics: dict = env.metrics()
                episode_reward: float = 0.0
                for step in range(max_steps):
                    _raise_if_cancelled(context)
                    action = policy.act(observation, deterministic=True)
                    observation, raw_reward, terminated, truncated, info = env.step(action)
                    after_metrics: dict = info["metrics"]
                    episode_reward += reward.compute(Transition(None, None, raw_reward, None, terminated, truncated, {
                        "before_metrics": before_metrics, "after_metrics": after_metrics, "metrics": after_metrics,
                        "delta_t": after_metrics["timeline"] - before_metrics.get("timeline", 0.0),
                    }))
                    before_metrics = after_metrics
                    if training_episode is not None and ((step + 1) % 100 == 0 or terminated or truncated or step + 1 == max_steps):
                        evaluation_episode: int = problem_index * repetitions + repetition + 1
                        context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
                            "phase": "evaluating", "episode": training_episode,
                            "evaluation_episode": evaluation_episode, "evaluation_episodes": evaluation_count,
                            "step": step + 1, "max_steps": max_steps, "selection_split": data.name,
                            "message": f"模型选择评估 {evaluation_episode}/{evaluation_count} 回合，{step + 1}/{max_steps} 步",
                        })
                    if terminated or truncated:
                        break
                episode_metrics.append({**_formal_metrics(env), **policy.planning_metrics, "episode_reward": episode_reward})
            finally:
                env.close()
    summary: dict[str, float] = _summarize_evaluation(episode_metrics)
    if training_episode is not None:
        evaluation_seconds: float = time.monotonic() - evaluation_started
        context.event_publisher.emit(EventType.TRAINING_PROGRESS, {
            "phase": "evaluation_completed", "episode": training_episode,
            "selection_split": data.name, "evaluation_seconds": evaluation_seconds, "metrics": summary,
            "message": f"模型选择评估完成，{evaluation_count} 回合耗时 {evaluation_seconds:.2f} 秒",
        })
    return summary


def _raise_if_cancelled(context: RunContext) -> None:
    if context.cancel_event.is_set():
        raise AlgorithmExecutionCancelled("PPO execution was cancelled")


def _formal_metrics(env: SkyEngineTrainingEnv) -> dict[str, float]:
    metrics = {
        str(name): float(value)
        for name, value in env.metrics().items()
        if isinstance(value, Real)
    }
    pogema = env.session.env.pogema_env
    jobs = list(getattr(pogema, "_all_jobs", pogema.jobs))
    completed = [job for job in jobs if job.is_completed]
    urgent = [
        job
        for job in jobs
        if int(getattr(job, "priority", 0)) >= DFJSPT_URGENT_PRIORITY
    ]
    completed_urgent = [job for job in urgent if job.is_completed]
    now = float(pogema.env_timeline)
    unfinished = len(jobs) - len(completed)
    unfinished_urgent = len(urgent) - len(completed_urgent)
    c_max = max(
        (float(job.completion_time) for job in completed),
        default=now,
    )
    c_max_e = max(
        (float(job.completion_time) for job in completed_urgent),
        default=0.0,
    )
    if unfinished:
        c_max = max(c_max, now)
    if unfinished_urgent:
        c_max_e = max(c_max_e, now)
    total_tardiness = 0.0
    weighted_tardiness = 0.0
    for job in jobs:
        due = getattr(job, "due", None)
        if due is None:
            continue
        completion = (
            float(job.completion_time)
            if job.is_completed
            else now
        )
        tardiness = max(0.0, completion - float(due))
        total_tardiness += tardiness
        weighted_tardiness += tardiness * max(
            1.0,
            float(getattr(job, "priority", 0)) / 100.0,
        )
    metrics.update(
        {
            "C_max": c_max,
            "C_max_E": c_max_e,
            "completed_jobs": float(len(completed)),
            "unfinished_jobs": float(unfinished),
            "urgent_jobs": float(len(urgent)),
            "unfinished_urgent_jobs": float(unfinished_urgent),
            "success_rate": 1.0 if not unfinished else 0.0,
            "job_completion_rate": (
                float(len(completed)) / len(jobs) if jobs else 1.0
            ),
            "total_tardiness": total_tardiness,
            "weighted_tardiness": weighted_tardiness,
        }
    )
    return metrics


def _episode_seed(base: int, offset: int) -> int:
    return (int(base) + int(offset)) % 2_147_483_647


__all__ = [
    "ALGORITHM_ID",
    "DFJSPTPPOTrainable",
    "FrozenDFJSPTPPOPolicy",
]
