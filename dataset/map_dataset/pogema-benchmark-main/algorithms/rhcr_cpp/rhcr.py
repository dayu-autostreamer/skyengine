from typing import Optional, Literal
from pydantic import BaseModel
from pydantic import Extra
from pogema_toolbox.algorithm_config import AlgoBase

import cppimport.import_hook
from rhcr_cpp.PogemaAgent import PogemaAgent


class RHCRConfig(AlgoBase, extra=Extra.forbid):
    name: Literal['RHCR'] = 'RHCR'
    simulation_window: int = 5
    planning_window: int = 10
    time_limit: int = 10
    low_level_planner: Literal['A*', 'SIPP'] = 'SIPP'
    solver: Literal['PBS', 'ECBS'] = 'PBS'


class RHCRInference:
    def __init__(self, cfg: RHCRConfig):
        self.cfg = cfg
        self.agent = None

    def act(self, observations, rewards=None, dones=None, info=None, skip_agents=None):
        if 'after_reset' in observations[0]:
            self.agent = PogemaAgent()
            starts = [obs['global_xy'] for obs in observations]
            if 'global_lifelong_targets_xy' in observations[0]:
                goals = [obs['global_lifelong_targets_xy'] for obs in observations]
            else:
                goals = [[obs['global_target_xy']] for obs in observations]
            self.agent.init(observations[0]['global_obstacles'].astype(int).tolist(), starts, goals,
                            self.cfg.simulation_window, self.cfg.planning_window, self.cfg.time_limit,
                            observations[0]['max_episode_steps'] + self.cfg.simulation_window,
                            self.cfg.low_level_planner, self.cfg.solver)
            
        assert self.agent is not None, "Error! Cannot initialize RHCR! Global obsctacles are not provided!"
        return self.agent.act()

    def after_step(self, dones):
        pass

    def reset_states(self):
        self.agent = None

    def after_reset(self):
        pass

    def get_additional_info(self):
        addinfo = {"rl_used": 0.0}
        return addinfo
