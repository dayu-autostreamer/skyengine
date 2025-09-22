'''
@Project ：tiangong 
@File    ：all_field_const.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/22 13:02 
'''

from enum import Enum

class CacheInfo(Enum):
    CACHE_EXPIRE = 60 * 60


    MONITOR_AGV="MONITOR_AGV"
    MONITOR_MACHINE="MONITOR_MACHINE"
    MONITOR_JOB="MONITOR_JOB"
    KEY_AGV_NUM = 'KEY_AGV_NUM'
    KEY_MACHINE_NUM = 'KEY_MACHINE_NUM'
    KEY_JOB_NUM = 'KEY_JOB_NUM'
    KEY_THROUGHPUT_NUM = 'KEY_THROUGHPUT_NUM'

