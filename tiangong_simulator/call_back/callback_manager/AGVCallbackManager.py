'''
@Project ：tiangong 
@File    ：AGVCallbackManager.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 20:22 
'''
from tiangong_simulator.call_back.callback_manager.CallbackManager import CallbackManager
from tiangong_simulator.call_back.component_callback.agv_callback.BaseCount import BaseCount
from tiangong_logs.logger import AGV_LOGGER as LOGGER


class AGVCallbackManager(CallbackManager):
    def __init__(self):
        super().__init__()
        self._callbacks.clear()
        self._callbacks.update({
            "after_work": [BaseCount()]
        })

    def use_all_after_work(self, component=None):
        """
        执行所有 'after_work' 回调
        """
        LOGGER("[AGVCallbackManager] 开始执行所有 after_work 回调...")
        results = {}

        for cb in self._callbacks.get("after_work", []):
            cb_name = cb.__class__.__name__
            try:
                if component is not None:
                    result = cb(component)
                else:
                    result = cb()
                results[cb_name] = result
            except Exception as e:
                LOGGER(f"[AGVCallbackManager] 回调 '{cb_name}' 执行出错: {e}")
                results[cb_name] = None

        LOGGER("[AGVCallbackManager] after_work 回调执行完成")
        return results
