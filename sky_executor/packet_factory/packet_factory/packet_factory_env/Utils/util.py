from enum import Enum


class OperationStatus(Enum):
    # 前序任务未满足
    WAITING = 0
    # 可以参与此次调度
    READY = 1
    # 在AGV上移动
    MOVING = 2
    # 开始执行
    WORKING = 3
    # 该任务执行就绪
    FINISHED = 4

    # 意外状态
    EXCEPTION = 99


class AGVStatus(Enum):
    # AGV可以运送Operation
    READY = 0
    # AGV正在运行(不含Operation)
    ASSIGNED = 1
    # AGV正在运行(含Operation)
    LOADED = 2

    # 意外状态
    EXCEPTION = 99


class MachineStatus(Enum):
    # todo: 由于无限缓冲池，当前机器可以在任意时间接收Operation

    # 当前机器不在运行Operation
    READY = 0
    # 当前机器正在运行Operation
    WORKING = 1
    # 当前机器宕机
    FAILED = 3

    # 意外状态
    EXCEPTION = 99


class JobStatus(Enum):
    # 该Job未开始
    B4START = 0
    # 该Job是否已经开始
    STARTED = 1
    # 该Job是否已经结束
    FINISHED = 2

    # 意外状态
    EXCEPTION = 99


class EnvStatus(Enum):
    # 环境暂停
    PAUSED = 0
    # 环境在运行
    RUNNING = 1
    # 环境需要一次重启
    RESTART = 2

    # 环境正常结束
    FINISHED = 3
    # 环境等待后续指令
    WAITING = 4
    # 意外状态
    EXCEPTION = 99


class AgentStatus(Enum):
    # 决策暂停
    INFER_PAUSED = 0
    # 决策在运行
    INFER_RUNNING = 1
    # 决策需要一次重启
    INFER_RESTART = 2

    # 决策正在训练
    TRAIN_PAUSED = 3
    # 训练暂停
    TRAIN_RUNNING = 4

    # 意外状态
    EXCEPTION = 99
