"""
@Project ：tiangong
@File    ：monitor_service.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2025/9/20 22:52
"""
from typing import Any, Dict, Optional, List
import asyncio
import json
import time
from sky_logs.dc_helper import DiskCacheHelper
import config
from config.all_field_const import CacheInfo

# 初始化一个全局缓存对象
dc = DiskCacheHelper(config.CACHE_DIR, expire=600)


async def get_agv_indicator(default: Optional[List[Dict[str, Any]]] = None):
    while True:
        current_keys = dc.keys()
        agv_data = []
        for key in current_keys:
            if key.startswith(CacheInfo.MONITOR_AGV.value):
                agv_data.append(dc.get(key, default or {}))
        payload = {
            "data": agv_data
        }
        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(2)  # 每2秒推送一次


async def get_machine_indicator(default: Optional[List[Dict[str, Any]]] = None):
    while True:
        current_keys = dc.keys()
        machine_data = []
        for key in current_keys:
            if key.startswith(CacheInfo.MONITOR_MACHINE.value):
                machine_data.append(dc.get(key, default or {}))
        payload = {
            "data": machine_data
        }
        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(2)  # 每2秒推送一次


async def get_job_indicator(default: Optional[List[Dict[str, Any]]] = None):
    while True:
        current_keys = dc.keys()
        job_data = []
        for key in current_keys:
            if key.startswith(CacheInfo.MONITOR_JOB.value):
                job_data.append(dc.get(key, default or {}))
        payload = {
            "data": job_data
        }
        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(2)  # 每2秒推送一次


async def get_system_indicator():
    while True:
        online = True
        activeAGVs = dc.get(CacheInfo.KEY_AGV_NUM.value)
        activeMACHINES = dc.get(CacheInfo.KEY_MACHINE_NUM.value)
        totalJOBS = dc.get(CacheInfo.KEY_MACHINE_NUM.value)
        payload = {
            "systemStatus": online,
            "activeAGVs": activeAGVs,
            "activeMachines": activeMACHINES,
            "totalJobs": totalJOBS,
            "throughput": online,
        }
        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(2)  # 每2秒推送一次


async def event_generator():
    """不断推送监控数据"""
    while True:
        # 从缓存获取数据
        agv_data = get_agv_indicator({})
        machine_data = get_machine_indicator({})
        job_data = get_job_indicator({})
        system_data = get_system_indicator({})

        # === 格式化给前端的数据 ===
        payload = {
            "systemStatus": {
                "text": system_data.get("status", "Offline"),
                "type": "success" if system_data.get("status") == "running" else "danger"
            },
            "activeAGVs": len(agv_data) if agv_data else 0,
            "completedJobs": job_data.get("completed", 0),
            "throughput": system_data.get("throughput", 0),

            # 图表数据（这里要根据缓存格式调整）
            "machine": [m.get("utilization", 0) for m in machine_data.values()] if isinstance(machine_data,
                                                                                              dict) else [],
            "agv": [a["value"]["transport_count"] for a in agv_data.values()] if isinstance(agv_data, dict) else [],
            "job": [j.get("latency", 0) for j in job_data.get("list", [])] if isinstance(job_data, dict) else [],
            "throughputSeries": system_data.get("throughput_series", [0, 0, 0, 0, 0]),

            # 日志数据
            "logs": system_data.get("logs", [
                "[INFO] Monitor heartbeat {}".format(time.strftime("%H:%M:%S"))
            ])
        }

        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(2)  # 每2秒推送一次


if __name__ == "__main__":
    # 写入的测试代码在dc_test中
    print(get_agv_indicator())  # {'active': 5, 'idle': 2}
    print(get_machine_indicator())  # {'running': 8, 'idle': 3}
    print(get_job_indicator())  # {'completed': 120, 'pending': 15}
    print(get_system_indicator())  # {'status': 'running', 'throughput': 32}
