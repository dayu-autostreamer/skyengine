from typing import Dict
from sky_simulator.call_back.EnvCallback import EnvCallback
from sky_simulator.call_back.base_callback.EnvMapLoader import EnvMapLoader
from sky_simulator.call_back.base_callback.EnvVisualizer import EnvVisualizer
from sky_simulator.call_back.base_callback.EventQueue import EventQueue


class CallbackManager:
    def __init__(self):
        self._callbacks: Dict[str, EnvCallback] = {
            'load_graph': EnvMapLoader("/brandimarte/simple_agv.txt"),
            'initialize_visualizer': EnvVisualizer(),
            'event_queue': EventQueue()
        }

    def register(self, name: str, callback: EnvCallback):
        """注册/替换一个回调"""
        if not isinstance(callback, EnvCallback):
            raise TypeError(f"[CallbackManager] 回调 '{name}' 必须继承 EnvCallback")
        if not self.has(name):
            raise ValueError(f"[CallbackManager] 环境中预先未包含 '{name}' 回调设计")

        self._callbacks[name] = callback

    def get(self, name: str) -> EnvCallback:
        """获取回调对象 有时候需要当场调用 有的时候不需要"""
        if name not in self._callbacks:
            raise KeyError(f"[CallbackManager] 未找到名为 '{name}' 的回调")
        return self._callbacks[name]

    def has(self, name: str) -> bool:
        return name in self._callbacks.keys()

    def list_all(self) -> Dict[str, EnvCallback]:
        """列出所有已注册的回调"""
        return self._callbacks.copy()
