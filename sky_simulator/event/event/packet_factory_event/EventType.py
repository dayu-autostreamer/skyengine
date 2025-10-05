# 统计配置使用,表示系统当前支持的所有事件

from enum import Enum


# 定义一个枚举类
class EventType(Enum):
    BASE_EVENT = -1

    JUST_TEST = 0

    ENV_RESTART = 1
    ENV_PAUSED = 2
    ENV_RECOVER = 3

    JOB_FINISH = 100
    JOB_ADD = 101
    JOB_CANCEL = 102

    MACHINE_FAIL = 200

    AGV_REFRESH = 300
    AGV_FAIL = 301
    AGV_BLOCK = 302

    OPERATION_DELAY = 400
