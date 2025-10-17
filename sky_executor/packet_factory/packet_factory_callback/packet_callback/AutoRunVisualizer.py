from sky_executor.utils.call_back.base_callback.EnvVisualizer import EnvVisualizer
from sky_executor.utils.registry import register_component

# 仿真环境创建前的初始化
@register_component("packet_callback.AutoRunVisualizer")
class InteractiveVisualizer(EnvVisualizer):
    def __init__(self, _fps=3) -> None:
        super().__init__(_fps)

        self.should_run = True
