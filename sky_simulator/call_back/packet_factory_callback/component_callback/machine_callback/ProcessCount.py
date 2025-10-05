'''
@Project ：tiangong
@File    ：ProcessCount.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2025/09/21
'''
# 该回调计算machine完成操作的工件数量

from sky_simulator.call_back.packet_factory_callback.component_callback.machine_callback.BaseCount import BaseCount
from sky_simulator.registry import register_component
from sky_logs.logger import MACHINE_LOGGER as LOGGER
from config.all_field_const import CacheInfo


@register_component("machine_callback.ProcessCount")
class ProcessCount(BaseCount):
    def __init__(self):
        super().__init__()
        self.process_counts = {}  # 记录每个machine处理的工件数量

    def __call__(self, *args, **kwargs):
        """计算machine完成操作的工件数量"""
        machine_component = kwargs.get('machine', None)

        if machine_component is None:
            LOGGER.info("传入machine_component为none")
            return {'success': False, 'message': "machine_component is None"}

        machine_id = machine_component.id

        # 初始化该machine的计数器（如果不存在）
        if machine_id not in self.process_counts:
            self.process_counts[machine_id] = 0

        # 增加处理工件计数
        self.process_counts[machine_id] += 1

        LOGGER.info(f"Machine {machine_id} 已处理工件数量: {self.process_counts[machine_id]}")

        # 返回指标数据，将被记录到cache中

        data = {
            'success': True,
            'machine_id': machine_id,
            'process_count': self.process_counts[machine_id],
            'indicator_type': 'machine_process_count'
        }
        # 返回指标数据，将被记录到cache中
        self.dc_helper.append_to_list(
            f"{CacheInfo.MONITOR_MACHINE.value}_{machine_component.id:02d}", data, machine_component.timer
        )
