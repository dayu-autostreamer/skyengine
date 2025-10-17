'''
@Project ：tiangong 
@File    ：JobCallbackManager.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 20:22 
'''
from sky_executor.packet_factory.packet_factory_callback.callback_manager.CallbackManager import CallbackManager
from sky_executor.packet_factory.packet_factory_callback.component_callback.job_callback.BaseCount import BaseCount
from sky_logs.logger import JOB_LOGGER as LOGGER


class JobCallbackManager(CallbackManager):
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
        LOGGER.info("[JOBCallbackManager] 开始执行所有 after_work 回调...")
        results = {}
        for cb in self._callbacks.get("after_work", []):
            cb_name = cb.__class__.__name__

            try:
                if component is not None:
                    result = cb(job=component)
                else:
                    result = cb()
                results[cb_name] = result
            except Exception as e:
                LOGGER(f"[JOBCallbackManager] 回调 '{cb_name}' 执行出错: {e}")
                results[cb_name] = None

        LOGGER.info("[JOBCallbackManager] after_work 回调执行完成")
        return results
