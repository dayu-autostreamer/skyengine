'''
@Project ：tiangong 
@File    ：BaseCount.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 20:31 
'''

from tiangong_simulator.call_back.EnvCallback import EnvCallback
from tiangong_simulator.registry import register_component
from tiangong_logs.logger import AGV_LOGGER as LOGGER

@register_component("agv_callback.BaseCount")
class BaseCount(EnvCallback):
    def __init__(self):
        super().__init__()

    def __call__(self, *args, **kwargs):
        """使类的实例可以像函数一样被调用"""
        agv_component = kwargs.get('agv', None)  # 取关键字参数 'a'，默认值 0
        if agv_component is None:
            print("传入job_component为none")
        else:
            print("传入了实际的job_component")
        return {
            'success':"agv_callback.BaseCount success"
        }