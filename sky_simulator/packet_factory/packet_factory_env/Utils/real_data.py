# 1. agv的那个current_task是什么，按照代码里的，我可能希望知道agv上已经发布的所有未完成的指令+当前装载的packet
# 2. Operation类里的当前已经执行的时间process_time，以及Operation的状态status，这两个应该肯定需要。剩下的next_operation和durations可能也需要？

from typing import List, Tuple, Optional, Dict


# 建议创建新的数据模型类
class MachineData:
    def __init__(self):
        self.machine_id: int
        self.position: Tuple[float, float]  # 机器的 (x, y)坐标
        self.status: str  # 运行状态
        self.current_operation: Optional[str]  # 机器的当前操作
        self.current_operation_process: float  # 当前操作处理进度
        self.current_operation_status: str  # 当前操作状态
        # 缓存的Operation
        self.input_queue: List[str] = []  # 入口缓存的物料
        self.output_queue: List[str] = []  # 出口缓存的物料
        self.available: bool  # 机器是否在线等可用信息


class AGVData:
    def __init__(self):
        self.agv_id: int
        self.position: Tuple[float, float]  # (x, y)坐标
        self.velocity: float  # 速度
        self.status: str  # 运行状态
        self.current_packet: Optional[str]  # 当前物料
        self.command_buffer: List[str]  # 指令缓冲池 当前有两种指令:load 和unload


class EnvironmentData:
    def __init__(self):
        self.jobs: List[Dict[str, str]]  # 当前环境内任务的详情 或者可以用开局单独的初始化阶段获取一些全局信息 避免每次都传Jobs列表
        self.machines: List[MachineData]  # 当前环境内机器的详情
        self.agvs: List[AGVData]  # 当前环境内AGV的详情
        self.events: List[str]  # 系统事件


class AgvActionData:
    def __init__(self):
        self.Command: List[(str, str, str)]

# 当前不知道Machine是否也需要指定Operation等操作,暂时认为实际工厂内一台Machine通常情况下均为一个Operation运行。
