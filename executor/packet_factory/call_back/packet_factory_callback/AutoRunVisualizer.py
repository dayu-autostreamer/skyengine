from executor.packet_factory.call_back.base_callback.EnvVisualizer import EnvVisualizer
from executor.packet_factory.registry import register_component

# 仿真环境创建前的初始化
@register_component("packet_factory_callback.AutoRunVisualizer")
class InteractiveVisualizer(EnvVisualizer):
    def __init__(self, _fps=3) -> None:
        super().__init__(_fps)

        self.should_run = True
