'''
@Project ：tiangong 
@File    ：BaseComponentCall.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/22 0:06 
'''
'''
@Project ：tiangong 
@File    ：BaseCount.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 20:31 
'''

from sky_executor.utils.call_back.EnvCallback import EnvCallback
from sky_executor.utils.registry import register_component
from sky_logs.dc_helper import DiskCacheHelper

@register_component("component_callback.BaseComponentCall")
class BaseComponentCall(EnvCallback):
    def __init__(self):
        super().__init__()
        self.dc_helper = DiskCacheHelper(expire=600)

    def __call__(self, *args, **kwargs):
        """使类的实例可以像函数一样被调用"""
        pass
