
from sky_executor.utils.call_back.EnvCallback import EnvCallback
from sky_executor.utils.registry import register_component

# 仿真环境创建前的初始化
@register_component("base_callback.MapLoader")
class EnvMapLoader(EnvCallback):
    def __init__(self,):
        super().__init__()
        pass
    def __call__(self):
        pass
