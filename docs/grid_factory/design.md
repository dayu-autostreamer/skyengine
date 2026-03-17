
---
  Joint Simulation 环境迁移与打包设计方案

  1. 项目概述

  1.1 目标

将现有的 grid_factory 强化学习环境迁移到 joint_sim 目录下，实现:

  1. io 模块: 读取 JSON 配置文件，将配置注入强化学习环境
  2. proxy 模块: 实现服务器代理,提供与渲染器通信的接口

  1.2 现有结构

  joint_sim/
  ├── component/           # 已迁移的组件
  │   ├── Assigner/       # 任务分配器
  │   ├── JobSolver/      # 作业调度器
  │   ├── RouteSolver/    # 路由求解器
  │   └── Coordinator/    # 协调器
  ├── assign_env.py       # PogemaLifeLongWithAssign 环境
  ├── grid_factory_env.py # GridFactoryEnv 封装
  ├── grid_factory.py     # 核心逻辑
  ├── io/                 # [待实现] 配置加载模块
  ├── proxy/              # [待实现] 服务器代理模块
  └── grid_factory.json   # 配置文件示例

  ---

  1. IO 模块设计

  2.1 核心类

  config_models.py - Pydantic 配置模型

  from pydantic import BaseModel, Field
  from typing import List, Dict, Optional, Tuple
  from enum import Enum

  class MachineStatus(str, Enum):
      IDLE = "IDLE"
      WORKING = "WORKING"
      BROKEN = "BROKEN"
      MAINTENANCE = "MAINTENANCE"

  class MachineConfigModel(BaseModel):
      id: str
      name: str = ""
      location: List[int] = Field(..., min_length=2, max_length=2)  # [强制规约]
   必须是长度2的列表
      size: List[int] = Field(default=[1, 1], min_length=2, max_length=2)
      status: MachineStatus = Field(default=MachineStatus.IDLE)

  class AGVConfigModel(BaseModel):
      id: int
      name: str = ""
      initialLocation: List[int] = Field(..., min_length=2, max_length=2)  # [强制规约]
   必须是长度2的列表
      velocity: float = Field(default=1.0, gt=0)
      capacity: int = Field(default=100, ge=1)
      status: str = Field(default="IDLE")

  class OperationConfigModel(BaseModel):
      machine_id: int = Field(..., description="目标机器索引")  # [强制规约] 必须是有效索引
      duration: int = Field(..., ge=1, description="加工时长")  # [强制规约] 必须 >= 1
      name: str = ""

  class JobConfigModel(BaseModel):
      job_id: int = Field(..., ge=0)  # [强制规约] 必须 >= 0
      name: str = ""
      operations: List[OperationConfigModel]
      arrival_time: int = Field(default=0, ge=0)  # [强制规约] 必须 >= 0
      due_time: int = Field(default=-1)  # -1 表示无交期
      priority: int = Field(default=1, ge=1)  # [强制规约] 必须 >= 1

  config_converter.py - 数据格式强制规约核心

  class ConfigConverter:
      """
      ====== 数据格式强制规约 ======
      1. location 必须从 List[int] 转换为 Tuple[int, int]
      2. machine_id 在 JSON 中是索引，在内部必须映射为 Machine.id
      3. 所有时间单位统一为 "步" (step)
      4. 位置坐标必须是非负整数
      5. JSON 中的 machine_id 映射关系必须与 machines 字典顺序一致
      """

      @staticmethod
      def to_machines(config: FactoryJSONConfig) -> List[Machine]:
          machines = []
          for idx, (key, m) in enumerate(config.topology.machines.items()):
              machine = Machine(
                  machine_id=idx,  # [强制规约] 按顺序从0开始分配ID
                  location=tuple(m.location),  # [强制规约] List -> Tuple
              )
              machines.append(machine)
          return machines

      @staticmethod
      def to_jobs(config: FactoryJSONConfig) -> List[Job]:
          job_list = config.jobs.get("job_list", [])
          jobs = []
          for job_data in job_list:
              ops = []
              for op_idx, op_data in enumerate(job_data.operations):
                  op = Operation(
                      job_id=job_data.job_id,
                      op_id=op_idx,  # [强制规约] 使用索引
                      machine_options=[op_data.machine_id],  # [强制规约] 单机器列表
                      proc_time=op_data.duration,  # [强制规约] 直接映射
                      release=job_data.arrival_time,  # [强制规约] arrival_time -> release
                      due=job_data.due_time if job_data.due_time > 0 else None,  # [强制规约] -1 -> None
                  )
                  ops.append(op)
              job = Job(job_id=job_data.job_id, ops=ops, ...)
              jobs.append(job)
          return jobs

  ---

  1. Proxy 模块设计

  3.1 执行状态枚举

  class ExecutionStatus(str, Enum):
      IDLE = "idle"           # 未初始化
      READY = "ready"         # 已初始化，未启动
      RUNNING = "running"     # 正在运行
      PAUSED = "paused"       # 已暂停
      STOPPED = "stopped"     # 已停止
      ERROR = "error"         # 错误状态
      COMPLETED = "completed" # 任务全部完成

  3.2 GridFactoryProxy - 状态快照输出格式规约

  async def get_state_snapshot(self) -> dict:
      """
      ====== 输出格式强制规约 ======
      - positions: List[List[int]] - 每个元素长度必须为 2
      - targets: List[List[int]] - 每个元素长度必须为 2
      - machines[*].location: List[int] - 长度必须为 2
      - machines[*].status: str - 必须是枚举值 (IDLE/WORKING/WAITING)
      - jobs[*].ops[*].status: str - 必须是枚举值 (PENDING/PROCESSING/FINISHED)
      - agvs[*].pos: List[int] - 长度必须为 2
      """
      return {
          "step": self._current_step,
          "status": self._status.value,
          "positions": [list(pos) for pos in pogema.grid.positions_xy],  # [强制规约] Tuple -> List
          "targets": [list(pos) for pos in pogema.grid.finishes_xy],  # [强制规约] Tuple -> List
          "machines": [
              {
                  "id": m.id,
                  "location": list(m.location),  # [强制规约] Tuple -> List[int]
                  "status": "IDLE" | "WORKING" | "WAITING",  # [强制规约] 枚举值
              }
              for m in pogema.machines
          ],
          "jobs": [...],
          "agvs": [
              {
                  "id": idx,
                  "pos": list(agv.pos),  # [强制规约] Tuple -> List[int]
                  "status": "IDLE" | "MOVING" | "LOADING",
              }
              for idx, agv in enumerate(pogema.get_agv_info())
          ],
      }

  ---

  1. 数据格式强制规约汇总表

  4.1 输入格式 (JSON -> Python)

  ┌──────────────────────────┬───────────┬─────────────────┬──────────────────────────┐
  │           字段           │ JSON 类型 │   Python 类型   │         转换规则         │
  ├──────────────────────────┼───────────┼─────────────────┼──────────────────────────┤
  │ machines.*.location      │ List[int] │ Tuple[int, int] │ tuple(location)          │
  ├──────────────────────────┼───────────┼─────────────────┼──────────────────────────┤
  │ agvs[*].initialLocation  │ List[int] │ Tuple[int, int] │ tuple(initialLocation)   │
  ├──────────────────────────┼───────────┼─────────────────┼──────────────────────────┤
  │ operations[*].duration   │ int       │ int             │ 直接映射, 必须 >= 1      │
  ├──────────────────────────┼───────────┼─────────────────┼──────────────────────────┤
  │ operations[*].machine_id │ int       │ int             │ 直接映射, 必须是有效索引 │
  ├──────────────────────────┼───────────┼─────────────────┼──────────────────────────┤
  │ jobs[*].arrival_time     │ int       │ int             │ 映射为 release           │
  ├──────────────────────────┼───────────┼─────────────────┼──────────────────────────┤
  │ jobs[*].due_time         │ int       │ Optional[int]   │ -1 -> None, 其他直接映射 │
  └──────────────────────────┴───────────┴─────────────────┴──────────────────────────┘

  4.2 输出格式 (Python -> JSON/快照)

  ┌──────────────────┬─────────────────┬───────────┬──────────────────┐
  │       字段       │   Python 类型   │ 输出类型  │     转换规则     │
  ├──────────────────┼─────────────────┼───────────┼──────────────────┤
  │ Machine.location │ Tuple[int, int] │ List[int] │ list(location)   │
  ├──────────────────┼─────────────────┼───────────┼──────────────────┤
  │ AGV.pos          │ Tuple[int, int] │ List[int] │ list(pos)        │
  ├──────────────────┼─────────────────┼───────────┼──────────────────┤
  │ Machine.status   │ 内部状态        │ str       │ 映射为枚举字符串 │
  ├──────────────────┼─────────────────┼───────────┼──────────────────┤
  │ Operation.status │ 内部状态        │ str       │ 映射为枚举字符串 │
  └──────────────────┴─────────────────┴───────────┴──────────────────┘

  ---

  1. 测试代码结构

  joint_sim/test_proxy/
  ├── __init__.py
  ├── test_config_loader.py    # 配置加载测试
  ├── test_config_converter.py # 配置转换测试
  ├── test_proxy.py            # 代理功能测试
  └── test_integration.py      # 集成测试

  核心测试验证点:

  1. 位置类型转换: 验证 List[int] <-> Tuple[int, int] 转换
  2. ID 映射: 验证 machine_id 正确映射
  3. 状态枚举: 验证所有状态值在允许范围内
  4. 边界条件: 验证空列表、负数、超限值的处理
  5. 快照格式: 验证输出快照符合规范
  6. 异步流程: 验证 start/pause/stop/reset 流程
  7. 错误处理: 验证异常情况的处理

  ---

## 6. 实现优先级

### P0 - 核心功能

  1. `io/config_models.py`
  2. `io/json_loader.py`
  3. `io/config_converter.py`
  4. `proxy/execution_status.py`
  5. `proxy/base_proxy.py`
  6. `proxy/grid_factory_proxy.py`
  7. `io/__init__.py`, `proxy/__init__.py`

### P1 - 测试代码

  1. `test_proxy/test_config_converter.py`
  2. `test_proxy/test_proxy.py`

### P2 - 集成测试

  1. `test_proxy/test_integration.py`

  ---

## 7. 注意事项

  1. __类型一致性__: 内部使用 Tuple， 输出使用 List, 駱换时需要显式转换
  2. __ID 连续性__: Machine.id 必须从 0 开始连续
  3. __时间单位__: 所有时间相关字段统一使用 "步" (step)
  4. __空值处理__: due_time = -1 需要转换为 None
  5. __状态同步__: 快照中机器/AGV 状态必须与内部状态一致

  6. __并发安全__: 异步操作需要考虑线程安全

  7. __错误传播__: 异常需要正确记录到 control_events 中

  这个设计方案完整覆盖了你要求的所有内容，特别强调了 数据格式强制规约:

- JSON 输入时 location 必须是 List[int] (长度=2)
- Python 内部使用 Tuple[int, int]
- 输出快照时转回 List[int]
- machine_id 必须按顺序映射
- 时间字段有明确的映射规则
- 状态值必须是预定义的枚举值

  需要我开始实现代码吗?
