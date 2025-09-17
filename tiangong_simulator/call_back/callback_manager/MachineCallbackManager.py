'''
@Project ：tiangong 
@File    ：MachineCallbackManager.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 20:22 
'''
from tiangong_simulator.call_back.callback_manager.CallbackManager import CallbackManager
from tiangong_simulator.call_back.machine_callback.BaseCount import BaseCount


class MachineCallbackManager(CallbackManager):
    def __init__(self):
        super().__init__()
        self._callbacks.clear()
        # 这里可以根据 Machine 环境需要，替换或新增一些回调
        self._callbacks.update({
            "statis": BaseCount()
        })

    def use_all(self, env_state=None, *args, **kwargs):
        """
        执行所有回调，但这里可以做一些 Machine 特定的前后处理
        """
        print("[MachineCallbackManager] 开始执行所有回调...")
        results = {}
        for name, cb in self._callbacks.items():
            try:
                if env_state is not None:
                    results[name] = cb(env_state, *args, **kwargs)
                else:
                    results[name] = cb(*args, **kwargs)
            except Exception as e:
                print(f"[MachineCallbackManager] 回调 '{name}' 执行出错: {e}")
                results[name] = None
        print("[MachineCallbackManager] 所有回调执行完成")
        return results
