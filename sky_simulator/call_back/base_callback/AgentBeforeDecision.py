from sky_simulator.call_back.EnvCallback import EnvCallback
from sky_simulator.registry import register_component

@register_component("base_callback.BeforeDecision")
class AgentBeforeDecision(EnvCallback):
    def __init__(self):
        super().__init__()

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        print("b4 decision")