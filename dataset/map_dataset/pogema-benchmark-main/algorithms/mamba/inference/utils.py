import numpy as np
import math
import torch

from mamba.agent.runners.DreamerRunner import DreamerRunner
from mamba.inference.inference_config import MAMBAInferenceConfig
from mamba.configs.dreamer.DreamerControllerConfig import DreamerControllerConfig
from mamba.configs.dreamer.DreamerLearnerConfig import DreamerLearnerConfig
from mamba.configs.EnvConfigs import PogemaConfig
from mamba.environments import Env

def get_env_info_pogema(configs, env):
    for config in configs:
        config.IN_DIM = 3 * 11 * 11
        config.ACTION_SIZE = env.action_space.n
    env.close()


def prepare_pogema_configs(env_name, num_agents, on_target, use_follower):
    agent_configs = [DreamerControllerConfig(), DreamerLearnerConfig()]
    env_config = PogemaConfig(env_name, num_agents, on_target, use_follower)
    get_env_info_pogema(agent_configs, env_config.create_env())
    return {
        "env_config": (env_config, 100),
        "controller_config": agent_configs[0],
        "learner_config": agent_configs[1],
        "reward_config": None,
        "obs_builder_config": None,
    }

class MAMBAInference:

    def __init__(self, config):

        self.algo_cfg: MAMBAInferenceConfig = config
        
        dreamer_config = prepare_pogema_configs(
            config.env_name, 
            config.num_agents, 
            config.on_target, 
            config.use_follower_wrapper
        )

        dreamer_config["env_config"][0].ENV_TYPE = Env.POGEMA
        dreamer_config["learner_config"].ENV_TYPE = Env.POGEMA
        dreamer_config["controller_config"].ENV_TYPE = Env.POGEMA

        self.runner = DreamerRunner(
            dreamer_config,
            dreamer_config["env_config"],
            dreamer_config["learner_config"],
            dreamer_config["controller_config"],
            n_workers=1,
            save_dir=config.custom_path_to_save_gifs,
            save_every=None,
            checkpoint_path=config.path_to_weights,
            evaluate=True,
        )

        self.rnn_states = None

    def act(self, observations):
        with torch.no_grad():
            actions = self.runner.act(observations)
        return np.array(actions)

    def reset_states(self):
        torch.manual_seed(self.algo_cfg.seed)
        self.runner.reset_states()

    @staticmethod
    def count_parameters(model):
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def get_model_parameters(self):
        return self.count_parameters(self.net)

