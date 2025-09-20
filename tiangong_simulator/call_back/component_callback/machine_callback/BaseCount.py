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

    def __call__(self, *args, **kwargs):
        """使类的实例可以像函数一样被调用"""
        machine_component = kwargs.get('machine', None)  # 取关键字参数 'a'，默认值 0
        if machine_component is None:
            print("传入machine_component为none")
        else:
            print("传入了实际的machine_component")
            print(machine_component.id)
        return {
            'success': "machine_callback.BaseCount success"
        }
