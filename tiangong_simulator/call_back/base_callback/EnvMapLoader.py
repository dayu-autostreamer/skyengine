
from tiangong_simulator.call_back.EnvCallback import EnvCallback
from tiangong_simulator.registry import register_component

# 仿真环境创建前的初始化
@register_component("base_callback.MapLoader")
class EnvMapLoader(EnvCallback):
    def __init__(self,):
        super().__init__()
        pass
    def __call__(self):
        pass
