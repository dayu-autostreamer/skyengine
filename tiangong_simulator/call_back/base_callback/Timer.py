'''
@Project ：tiangong 
@File    ：Timer.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 19:47 
'''

# 该回调用于在环境中执行确定性事件
from tiangong_simulator.registry import register_component
from tiangong_simulator.call_back.EnvCallback import EnvCallback
import threading

# 环境中的定时器,便于定时执行某类任务
@register_component("base_callback.Timer")
class Timer(EnvCallback):
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def _task_loop(self, time):
        """
        循环任务，每隔 interval 秒执行一次 callback
        """
        while not self._stop_event.is_set():
            start = time.time()
            try:
                callback()
            except Exception as e:
                print(f"任务执行出错: {e}")
            # 保证精确间隔
            elapsed = time.time() - start
            time.sleep(max(0, interval - elapsed))

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        print("定时执行样例")




