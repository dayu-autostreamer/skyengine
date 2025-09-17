'''
@Project ：tiangong 
@File    ：BaseCount.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 20:31 
'''

from tiangong_simulator.call_back.EnvCallback import EnvCallback
from tiangong_simulator.registry import register_component


@register_component("machine_callback.BaseCount")
class BaseCount(EnvCallback):
    def __init__(self):
        super().__init__()

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        print("测试Machine的回调")
