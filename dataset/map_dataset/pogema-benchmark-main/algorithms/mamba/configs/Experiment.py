from mamba.configs.Config import Config
from datetime import datetime


class Experiment(Config):
    def __init__(
        self,
        steps,
        episodes,
        random_seed,
        env_config,
        controller_config,
        learner_config,
        save_every,
        save_directory,
        num_eval_episodes,
    ):
        super(Experiment, self).__init__()
        self.steps = steps
        self.episodes = episodes
        self.random_seed = random_seed
        self.env_config = env_config
        self.controller_config = controller_config
        self.learner_config = learner_config

        self.save_every = save_every
        self.save_directory = save_directory
        self.num_eval_episodes = num_eval_episodes
