from mamba.agent.controllers.DreamerController import DreamerController
from mamba.configs.dreamer.DreamerAgentConfig import DreamerConfig


class DreamerControllerConfig(DreamerConfig):
    def __init__(self):
        super().__init__()

        self.EXPL_DECAY = 0.9999
        self.EXPL_NOISE = 0.0
        self.EXPL_MIN = 0.0

    def create_controller(self):
        return DreamerController(self)
