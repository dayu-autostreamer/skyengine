'''
@Project ：tiangong
@File    ：ProcessCount.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2025/09/21
'''
# 该回调计算单个物件从开始到结束的时延

from sky_executor.utils.call_back.EnvCallback import EnvCallback
from sky_executor.utils.registry import register_component
from sky_logs.logger import JOB_LOGGER as LOGGER
import time

@register_component("job_callback.ItemDelayCount")
class ItemDelayCount(EnvCallback):
    def __init__(self):
        super().__init__()
        self.item_start_times = {}  # 记录每个物件的开始时间
        self.item_end_times = {}    # 记录每个物件的结束时间

    def __call__(self, *args, **kwargs):
        """计算单个物件从开始到结束的时延"""
        job_component = kwargs.get('job', None)
        item_id = kwargs.get('item_id', None)
        status = kwargs.get('status', None)  # 'start' 或 'end'
        event_time = kwargs.get('time', time.time())
        
        if job_component is None or item_id is None:
            LOGGER.warning("传入job_component或item_id为none")
            return {'success': False, 'message': "Missing required parameters"}
        
        # 记录物件开始时间
        if status == 'start':
            self.item_start_times[item_id] = event_time
            LOGGER.info(f"物件 {item_id} 开始处理, 时间: {event_time}")
            return {
                'success': True,
                'item_id': item_id,
                'start_time': event_time,
                'status': 'started',
                'indicator_type': 'item_delay'
            }
        
        # 记录物件结束时间并计算时延
        elif status == 'end':
            if item_id not in self.item_start_times:
                LOGGER.warning(f"物件 {item_id} 没有记录开始时间")
                return {'success': False, 'message': f"No start time for item {item_id}"}
            
            self.item_end_times[item_id] = event_time
            delay = event_time - self.item_start_times[item_id]
            
            LOGGER.info(f"物件 {item_id} 完成处理, 总时延: {delay}")
            
            return {
                'success': True,
                'item_id': item_id,
                'start_time': self.item_start_times[item_id],
                'end_time': event_time,
                'total_delay': delay,
                'status': 'completed',
                'indicator_type': 'item_delay'
            }
        
        else:
            LOGGER.warning(f"未知的状态: {status}")
            return {'success': False, 'message': f"Unknown status: {status}"}