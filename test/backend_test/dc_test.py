'''
@Project ：tiangong 
@File    ：dc_test.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/20 23:16 
'''
from tiangong_logs.dc_helper import DiskCacheHelper
import config


def test_logs():
    dc = DiskCacheHelper(config.CACHE_DIR, expire=60)
    # 写入
    dc.set("agv_indicator", {"active": 5, "idle": 2})
    dc.set("machine_indicator", {"running": 8, "idle": 3})
    dc.set("job_indicator", {"completed": 120, "pending": 15})
    dc.set("system_indicator", {"status": "running", "throughput": 32})


if __name__ == "__main__":
    test_logs()
    # dc = DiskCacheHelper(config.CACHE_DIR, expire=60)
    #
    # # 写入
    # dc.set("agv_status", {"id": 1, "pos": (10, 20)})
    #
    # # 读取
    # print(dc.get("agv_status"))
    #
    # # 判断存在
    # print(dc.exists("agv_status"))
    #
    # # 获取所有 key
    # print(dc.keys())
    #
    # # 删除
    # dc.delete("agv_status")
    #
    # # 清空
    # dc.clear()
    #
    # dc.close()
