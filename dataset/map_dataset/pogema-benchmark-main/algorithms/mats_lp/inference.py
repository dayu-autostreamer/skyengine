from typing import Optional, Literal
from pydantic import BaseModel
from pydantic import Extra
import gymnasium
from pogema_toolbox.algorithm_config import AlgoBase

import cppimport.import_hook
from mats_lp.config import Config
from mats_lp.environment import Environment
from mats_lp.mcts import Decentralized_MCTS

class MATS_LPConfig(AlgoBase, extra=Extra.forbid):
    name: Literal['MATS-LP'] = 'MATS-LP'
    num_process: int = 8
    gamma: float = 0.96
    num_expansions: int = 250
    steps_limit: int = 128
    use_move_limits: bool = True
    agents_as_obstacles: bool = False
    render: bool = False
    reward_type: Literal['cost2go'] = 'cost2go'
    obs_radius: int = 5
    random_action_chance: float = 0.6
    ppo_only: bool = False
    use_nn_module: bool = True
    agents_to_plan: int = 3
    path_to_weights: str = 'mats_lp/model/cost-tracer.onnx'
    num_threads: int = 8
    progressed_reward: float = 0.1
    collision_system: Literal['soft'] = 'soft'
    pb_c_init: float = 4.44
    precompute_cost2go: bool = False


class MATS_LPInference:
    def __init__(self, cfg: MATS_LPConfig):
        self.cfg = cfg
        self.mcts = Decentralized_MCTS()
        cppconfig = Config()
        cppconfig.gamma = cfg.gamma
        cppconfig.num_expansions = cfg.num_expansions
        cppconfig.steps_limit = cfg.steps_limit
        cppconfig.use_move_limits = cfg.use_move_limits
        cppconfig.agents_as_obstacles = cfg.agents_as_obstacles
        cppconfig.render = cfg.render
        cppconfig.obs_radius = cfg.obs_radius
        cppconfig.random_action_chance = cfg.random_action_chance
        cppconfig.ppo_only = cfg.ppo_only
        cppconfig.use_nn_module = cfg.use_nn_module
        cppconfig.agents_to_plan = cfg.agents_to_plan
        cppconfig.path_to_weights = cfg.path_to_weights
        cppconfig.num_threads = cfg.num_threads
        cppconfig.progressed_reward = cfg.progressed_reward
        cppconfig.pb_c_init = cfg.pb_c_init

        self.cppconfig = cppconfig

    def act(self, observations):
        if 'after_reset' in observations[0]:
            cpp_env = Environment(self.cfg.obs_radius, self.cfg.collision_system, 'restart', self.cfg.progressed_reward)
            cpp_env.create_grid(len(observations[0]['global_obstacles']), len(observations[0]['global_obstacles'][0]))
            for i in range(len(observations[0]['global_obstacles'])):
                for j in range(len(observations[0]['global_obstacles'][0])):
                    if observations[0]['global_obstacles'][i][j]:
                        cpp_env.add_obstacle(i, j)
            if self.cfg.precompute_cost2go:
                cpp_env.precompute_cost2go()
            for agent_idx in range(len(observations)):
                if 'global_lifelong_targets_xy' in observations[agent_idx]:
                    cpp_env.add_agent(observations[agent_idx]['global_xy'],
                                      observations[agent_idx]['global_lifelong_targets_xy'])
                else:
                    cpp_env.add_agent(observations[agent_idx]['global_xy'],
                                      [observations[agent_idx]['global_target_xy']])
            self.mcts.set_config(self.cppconfig)
            cpp_env.set_seed(1)
            self.mcts.set_env(cpp_env, 5)
        action = self.mcts.act()
        return action
    
    def reset_states(self):
        self.mcts = Decentralized_MCTS()
