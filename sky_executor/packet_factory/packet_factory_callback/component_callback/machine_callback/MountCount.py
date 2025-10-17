'''
@Project ：tiangong 
@File    ：MountCount.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 14:34 
'''
# 机器用于计算自己运行了多长时间

from sky_executor.utils.call_back.EnvCallback import EnvCallback
from sky_executor.utils.registry import register_component
from sky_logs.logger import MACHINE_LOGGER as LOGGER


@register_component("machine_callback.MountCount")
class MountCount(EnvCallback):
    def __init__(self):
        super().__init__()

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        LOGGER.info("测试Machine的回调")
        return {
            'success': "machine_callback.BaseCount success"
        }

