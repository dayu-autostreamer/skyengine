'''
@Project ：tiangong 
@File    ：TimeCount.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/20 23:28 
'''
from sky_executor.utils.call_back.EnvCallback import EnvCallback
from sky_executor.utils.registry import register_component
from sky_logs.logger import JOB_LOGGER as LOGGER


@register_component("job_callback.TimeCount")
class TimeCount(EnvCallback):
    def __init__(self):
        super().__init__()

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        LOGGER.info("测试Job的Timer回调")
