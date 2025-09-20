'''
@Project ：tiangong 
@File    ：PathCount.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 14:33 
'''
# 该回调计算单个AGV自己经过的路径

from tiangong_simulator.call_back.EnvCallback import EnvCallback
from tiangong_simulator.registry import register_component
from tiangong_logs.logger import AGV_LOGGER as LOGGER

@register_component("agv_callback.PathCount")
class PathCount(EnvCallback):
    def __init__(self):
        super().__init__()

    def __call__(self,component):
        """使类的实例可以像函数一样被调用"""
        LOGGER.info("测试AGV的回调")
        return {
            'success':"agv_callback.BaseCount success"
        }


