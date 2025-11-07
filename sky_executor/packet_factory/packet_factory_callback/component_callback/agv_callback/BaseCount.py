'''
@Project ：tiangong 
@File    ：BaseCount.py.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 20:31 
'''

from sky_executor.utils.registry import register_component
from sky_logs.logger import AGV_LOGGER as LOGGER
from sky_executor.packet_factory.packet_factory_callback.component_callback.BaseComponentCall import BaseComponentCall

@register_component("agv_callback.BaseCount")
class BaseCount(BaseComponentCall):
    def __init__(self):
        super().__init__()

    def __call__(self, *args, **kwargs):
        """使类的实例可以像函数一样被调用"""
        agv_component = kwargs.get('agv', None)  # 取关键字参数 'a'，默认值 0
        if agv_component is None:
            LOGGER.info("传入agv_component为none")
        else:
            LOGGER.info("传入了实际的agv_component")
        return {
            'success': "agv_callback.BaseCount success"
        }
