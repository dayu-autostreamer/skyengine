from typing import Optional, Union

from follower.follower_python.model import EncoderConfig
from follower.follower_python.preprocessing import PreprocessorConfig

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pogema import GridConfig
from pydantic import BaseModel


class DecMAPFConfig(GridConfig):
    integration: Literal['SampleFactory'] = 'SampleFactory'
    collision_system: Literal['priority', 'block_both', 'soft'] = 'soft'
    observation_type: Literal['POMAPF'] = 'POMAPF'
    auto_reset: Literal[False] = False

    num_agents: int = 64
    obs_radius: int = 5
    max_episode_steps: int = 512


class Environment(BaseModel, ):
    grid_config: DecMAPFConfig = DecMAPFConfig()
    env: Literal['PogemaMazes-v0'] = "PogemaMazes-v0"
    with_animation: bool = False
    worker_index: int = None
    vector_index: int = None
    env_id: int = None
    target_num_agents: Optional[int] = None
    agent_bins: Optional[list] = [64, 128, 256, 256]
    use_maps: bool = True

    every_step_metrics: bool = False


class EnvironmentMazes(Environment):
    env: Literal['PogemaMazes-v0'] = "PogemaMazes-v0"
    use_maps: bool = True
    target_num_agents: Optional[int] = 256
    agent_bins: Optional[list] = [128, 256, 256, 256]
    grid_config: DecMAPFConfig = DecMAPFConfig(on_target='restart', max_episode_steps=512)
    integration: Literal['SampleFactory'] = 'SampleFactory'
    on_target: Literal['restart'] = 'restart'
    MOVES: list = [[0, 0], [-1, 0], [1, 0], [0, -1], [0, 1], ]
    seed: int = 0
    obs_radius: int = 5
    observation_type: Literal['POMAPF'] = 'POMAPF'
    max_episode_steps: int = 256
    persistent: bool = False
    auto_reset: Optional[bool] = None
    map_name: str = None
    


class Experiment(BaseModel):
    environment: EnvironmentMazes = EnvironmentMazes()
    encoder: EncoderConfig = EncoderConfig()
    preprocessing: PreprocessorConfig = PreprocessorConfig()

    rollout: int = 8
    num_workers: int = 4

    recurrence: int = 8
    use_rnn: bool = False
    rnn_size: int = 256

    ppo_clip_ratio: float = 0.1
    batch_size: int = 2048

    exploration_loss_coeff: float = 0.018
    num_envs_per_worker: int = 4
    worker_num_splits: int = 1
    max_policy_lag: int = 1

    force_envs_single_thread: bool = True
    optimizer: Literal["adam", "lamb"] = 'adam'
    restart_behavior: str = "overwrite"  # ["resume", "restart", "overwrite"]
    normalize_returns: bool = False
    async_rl: bool = False
    num_batches_per_epoch: int = 16

    num_batches_to_accumulate: int = 1
    normalize_input: bool = False
    decoder_mlp_layers = []
    save_best_metric: str = "avg_throughput"
    value_bootstrap: bool = True
    save_milestones_sec: int = -1

    keep_checkpoints: int = 1
    stats_avg: int = 10
    learning_rate: float = 0.000146
    train_for_env_steps: int = 1_000_000

    gamma: float = 0.965

    lr_schedule: str = 'kl_adaptive_minibatch'

    experiment: str = 'exp'
    train_dir: str = 'experiments/train_dir'
    seed: Optional[int] = 42
    use_wandb: bool = True

    env: Literal['PogemaMazes-v0'] = "PogemaMazes-v0"
