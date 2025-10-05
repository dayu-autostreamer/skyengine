'''
@Project ：tiangong
@File    ：ProcessCount.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2025/09/21
'''
# 该回调计算job完成的各个时延

from sky_simulator.call_back.packet_factory_callback.component_callback.job_callback.BaseCount import BaseCount
from sky_simulator.registry import register_component
from sky_logs.logger import JOB_LOGGER as LOGGER
from sky_logs.dc_helper import DiskCacheHelper
from config.all_field_const import CacheInfo

@register_component("job_callback.DelayCount")
class DelayCount(BaseCount):
    def __init__(self):
        super().__init__()
        self.dc_helper = DiskCacheHelper()
        self.job_start_times = {}  # 记录每个job的开始时间
        self.job_step_times = {}  # 记录每个job各步骤的时间

    def __call__(self, *args, **kwargs):
        """计算job的各个时延"""
        job_component = kwargs.get('job', None)

        if job_component is None:
            LOGGER.warning("传入job_component为none")
            return {'success': False, 'message': "job_component is None"}

        job_id = job_component.id

        # 计算总时延
        total_delay = job_component.timer - job_component.begin_time

        LOGGER.info(f"Job {job_id} 当前总时延: {job_component.timer}, 总时延: {total_delay}")

        # 返回指标数据，将被记录到cache中

        data = {
            'success': True,
            'timestamp': job_component.timer,
            'job_id': job_id,
            'total_delay': total_delay,
            'indicator_type': 'job_delay'
        }
        print(f'JOB_{job_component.id:02d}的数据为:{data}')

        # 返回指标数据，将被记录到cache中
        self.dc_helper.append_to_list(
            f'{CacheInfo.MONITOR_JOB.value}_{job_component.id:02d}', data, job_component.timer
        )
