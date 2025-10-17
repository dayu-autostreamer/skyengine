'''
@Project ：SkyEngine 
@File    ：env_const.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/9 20:46
'''
from enum import Enum


class ObsType(Enum):
    DEFAULT = 'default'  # 默认的array
    MAPF = 'MAPF'  # 全局观察
    POMAPF = 'POMAPF'  # 局部观察


class OnTargetType(Enum):
    RESTART = "restart"
    NOTHING = "nothing"
    FINISH = "finish"


class CollisionSystem(Enum):
    BLOCK = "block_both"
    PRIORITY = "priority"
    SOFT = "soft"


class ActionType(Enum):
    WAIT = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4
