'''
@Project ：tiangong 
@File    ：BaseCount.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/20 23:30 
'''
from tiangong_simulator.call_back.EnvCallback import EnvCallback
from tiangong_simulator.registry import register_component
from tiangong_logs.logger import MACHINE_LOGGER as LOGGER


@register_component("job_callback.BaseCount")
class BaseCount(EnvCallback):
    def __init__(self):
        super().__init__()

    def __call__(self, *args, **kwargs):
        """使类的实例可以像函数一样被调用"""
        job_component = kwargs.get('job', None)  # 取关键字参数 'a'，默认值 0
        if job_component is None:
            print("传入job_component为none")
        else:
            print("传入了实际的job_component")

        LOGGER.info("测试Job的回调")
        return {
            'success':"job_callback.BaseCount success"
        }