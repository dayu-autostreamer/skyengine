'''
@Project ：SkyEngine 
@File    ：thread_pool.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/13 23:10
'''
import threading
from typing import Callable
from sky_logs.logger import Logger
import config

LOGGER = Logger(log_path=config.BACKEND_LOG_DIR, name="backend").logger


class ThreadPool:
    def __init__(self):
        self.threads = []
        self.stop_event = threading.Event()

    def __len__(self):
        return len(self.threads)

    def submit(self, func: Callable, *args, **kwargs):
        """提交任务到线程池,确保当前只有单个在修改env"""
        if len(self.threads) >= 1:
            self.shutdown()
        try:
            thread = threading.Thread(target=func, args=(self.stop_event, *args), kwargs=kwargs)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
        except Exception as e:
            LOGGER.error(e)

    def shutdown(self, wait=True):
        """请求线程退出（通过事件标志）"""
        self.stop_event.set()  # 通知线程退出
        if wait:
            for thread in self.threads:
                thread.join()
        self.threads = []  # 清空缓冲池
        self.stop_event.clear()  # 清除退出标志
        LOGGER.info("[INFO] 线程池已关闭")
