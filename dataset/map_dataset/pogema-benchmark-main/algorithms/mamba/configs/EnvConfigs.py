import pogema
from pogema import AnimationMonitor, AnimationConfig

from mamba.configs.Config import Config
from mamba.env.pogema.example import (
    benchmark_pogema_env,
    follower_pogema_env,
    follower_pogema_env_from_config,
    follower_pogema_env_mazes,
    follower_pogema_env_mazes_random,
)


class EnvConfig(Config):
    def __init__(self):
        pass

    def create_env(self):
        pass


class StarCraftConfig(EnvConfig):

    def __init__(self, env_name):
        self.env_name = env_name

    def create_env(self):
        from mamba.env.starcraft.StarCraft import StarCraft
        return StarCraft(self.env_name)


class PogemaConfig(EnvConfig):
    def __init__(self, env_name, num_agents, on_target, use_follower):
        self.env_name = env_name
        self.num_agents = num_agents
        self.use_follower = use_follower
        self.RENDER = False
        self.SAVE_DIR = None
        self.str2env = {
            "simple_benchmark": benchmark_pogema_env,
            "simple_benchmark_follower": follower_pogema_env,
            "mazes_benchmark_follower": follower_pogema_env_mazes,
            "benchmark_follower_pogema_env_mazes_random": follower_pogema_env_mazes_random,
            "Easy8x8": pogema.Easy8x8,
            "Normal8x8": pogema.Normal8x8,
            "Hard8x8": pogema.Hard8x8,
            "ExtraHard8x8": pogema.ExtraHard8x8,
            "Easy16x16": pogema.Easy16x16,
            "Normal16x16": pogema.Normal16x16,
            "Hard16x16": pogema.Hard16x16,
            "ExtraHard16x16": pogema.ExtraHard16x16,
            "Easy32x32": pogema.Easy32x32,
            "Normal32x32": pogema.Normal32x32,
            "Hard32x32": pogema.Hard32x32,
            "ExtraHard32x32": pogema.ExtraHard32x32,
            "Easy64x64": pogema.Easy64x64,
            "Normal64x64": pogema.Normal64x64,
            "Hard64x64": pogema.Hard64x64,
            "ExtraHard64x64": pogema.ExtraHard64x64,
        }
        self.on_target = on_target

    def create_env(self, validation_set=False):
        assert self.on_target in ["finish", "restart", "nothing"]
        env = None
        if "benchmark" not in self.env_name:
            if not self.use_follower:
                env = pogema.pogema_v0(
                    grid_config=self.str2env[self.env_name](on_target=self.on_target)
                )
            else:
                env = follower_pogema_env_from_config(
                    self.str2env[self.env_name](
                        on_target=self.on_target, observation_type="POMAPF"
                    )
                )
        else:
            env = self.str2env[self.env_name](self.num_agents, validation_set, self.on_target)

        if self.RENDER and env is not None:
            env = AnimationMonitor(env)
        return env
