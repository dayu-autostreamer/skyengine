from executor.packet_factory.call_back.EnvCallback import EnvCallback
from executor.packet_factory.registry import register_component

@register_component("base_callback.AfterDecision")
class AgentAfterDecision(EnvCallback):
    def __init__(self):
        super().__init__()

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        print("after decision")