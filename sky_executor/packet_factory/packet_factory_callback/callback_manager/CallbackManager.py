from typing import Dict
from sky_executor.utils.call_back.EnvCallback import EnvCallback


class CallbackManager:
    def __init__(self):
        self._callbacks: Dict[str, EnvCallback | list ] = {
            'load_graph': EnvCallback(),
            'initialize_visualizer': EnvCallback(),
            'event_queue': EnvCallback()
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

    def add_callback_to_group(self, name: str, callback: EnvCallback):
        """
        向名为 name 的回调组中添加一个回调。
        如果原本是单个回调，会自动转为列表。
        """
        if not isinstance(callback, EnvCallback):
            raise TypeError(f"[CallbackManager] 回调 '{name}' 必须继承 EnvCallback")

        if name not in self._callbacks:
            raise KeyError(f"[CallbackManager] 未找到名为 '{name}' 的回调")

        existing = self._callbacks[name]

        # 如果原来是单个回调，转换为 list
        if isinstance(existing, EnvCallback):
            self._callbacks[name] = [existing, callback]
        elif isinstance(existing, list):
            self._callbacks[name].append(callback)
        else:
            raise TypeError(f"[CallbackManager] 回调 '{name}' 的类型错误: {type(existing)}")
