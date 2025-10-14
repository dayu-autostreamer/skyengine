'''
@Project ：SkyEngine 
@File    ：env_const.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/9 20:46
'''
from enum import Enum

class ObsType(Enum):
    DEFAULT = 0 #默认的array
    MAPF= 1 # 全局观察
    POMAPF = 2 # 局部观察

class ActionType(Enum):
    WAIT = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4



