'''
@Project ：tiangong
@File    ：ProcessCount.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2025/09/21
'''
# 该回调计算单个AGV的运输次数

from sky_executor.packet_factory.packet_factory_callback.component_callback.agv_callback.BaseCount import BaseCount
from sky_executor.utils.registry import register_component
from sky_logs.logger import AGV_LOGGER as LOGGER
from config.all_field_const import CacheInfo

@register_component("agv_callback.TransportCount")
class TransportCount(BaseCount):
    def __init__(self):
        super().__init__()
        self.transport_count = 0  # 初始化运输次数计数器

    def __call__(self, *args, **kwargs):
        """计算AGV的运输次数"""
        agv_component = kwargs.get('agv', None)
        if agv_component is None:
            LOGGER.warning("传入agv_component为none")
            return {'success': False, 'message': "agv_component is None"}

        # 增加运输次数计数
        self.transport_count += 1

        LOGGER.info(f"AGV {agv_component.id} 运输次数: {self.transport_count}")
        data = {
            'success': True,
            'timestamp': agv_component.timer,
            'agv_id': agv_component.id,
            'transport_count': self.transport_count,
            'indicator_type': 'transport_count'
        }
        # 返回指标数据，将被记录到cache中
        self.dc_helper.append_to_list(
            f'{CacheInfo.MONITOR_AGV.value}_{agv_component.id:02d}', data, agv_component.timer
        )
