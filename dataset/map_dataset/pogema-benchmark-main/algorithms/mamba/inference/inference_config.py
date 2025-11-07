from typing import Any, Optional

from pogema_toolbox.algorithm_config import AlgoBase
from pydantic import Extra
from follower.follower_python.preprocessing import PreprocessorConfig


class MAMBAInferenceConfig(AlgoBase, extra=Extra.forbid):

    name = "MAMBA"
    preprocessing: PreprocessorConfig = PreprocessorConfig()
    num_envs: int = 1
    path_to_weights: str = "./mamba/inference/ckpt_lifelong_8agents.pt"
    num_agents: int = 8
    training_config: Optional[Any] = None
    custom_path_to_save_gifs: Optional[str] = "./renders"
    use_follower_wrapper: Optional[bool] = True
    env_name: Optional[str] = "benchmark_follower_pogema_env_mazes_random"
    on_target = "restart"
