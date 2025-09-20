"""
@Project ：tiangong
@File    ：monitor_service.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2025/9/20 22:52
"""
from typing import Any, Dict, Optional
from tiangong_logs.dc_helper import DiskCacheHelper
import config

# 初始化一个全局缓存对象
dc = DiskCacheHelper(config.CACHE_DIR, expire=60)


def get_agv_indicator(default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    获取 AGV 指标
    :param default: 缓存不存在时返回的默认值
    """
    return dc.get("agv_indicator", default or {})


def get_machine_indicator(default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    获取 Machine 指标
    """
    return dc.get("machine_indicator", default or {})


def get_job_indicator(default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    获取 Job 指标
    """
    return dc.get("job_indicator", default or {})


def get_system_indicator(default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    获取系统级别指标
    """
    return dc.get("system_indicator", default or {})


if __name__ == "__main__":
    # 写入的测试代码在dc_test中
    print(get_agv_indicator())  # {'active': 5, 'idle': 2}
    print(get_machine_indicator())  # {'running': 8, 'idle': 3}
    print(get_job_indicator())  # {'completed': 120, 'pending': 15}
    print(get_system_indicator())  # {'status': 'running', 'throughput': 32}
