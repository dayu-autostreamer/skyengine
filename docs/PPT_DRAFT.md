# 天工：仿真-调度一体化的柔性制造算法平台

> SkyEngine: A Simulation-Scheduling Integrated FMS Platform

---

## 目录

1. [研究背景与动机](#1-研究背景与动机)
2. [系统架构设计](#2-系统架构设计)
3. [仿真环境 A：GridFactory](#3-仿真环境-agridfactory)
4. [仿真环境 B：PacketFactory](#4-仿真环境-bpacketfactory)
5. [两种环境的对比分析](#5-两种环境的对比分析)
6. [总结与展望](#6-总结与展望)

---

## 1. 研究背景与动机（1页）

### 1.1 传统调度系统的结构性问题

| 问题类型 | 具体表现 | 影响 |
|---------|---------|------|
| **算法与业务强耦合** | 调度算法嵌入业务逻辑，难以替换、对比与复现 | 算法迭代成本高 |
| **多目标与动态性不足** | 难以同时处理工期、负载、路径、异常等多目标约束 | 实际落地困难 |
| **仿真与真实执行割裂** | 调度结果无法在高一致性仿真中验证 | "纸面最优"的算法幻觉 |
| **算法研究难以工程化** | 学术算法缺乏运行环境与接口标准 | 研究成果转化率低 |

### 1.2 核心思想

> **通过"算法环境层 × 服务层"两层架构，将调度算法工程化、平台化。**

**目标定位**：

- 以高保真仿真为验证闭环
- 将调度算法从"离线求解器"提升为"可落地的生产决策系统"
- 面向智能制造、调度算法研究、数字孪生验证等场景

---

## 2. 系统架构设计 （2页）

### 2.1 两层解耦架构

```
┌─────────────────────────────────────────────────────────────┐
│                      服务层 (Service Layer)                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  前端 (Vue3 + Element Plus + ECharts)               │   │
│  │  · 实时可视化    · 控制面板    · 状态监控            │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↕ HTTP/SSE                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  后端 (FastAPI)                                      │   │
│  │  · REST API    · SSE 流式推送    · 生命周期管理      │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↕ FactoryProxy                   │
└─────────────────────────────────────────────────────────────┘
                             ↕
┌─────────────────────────────────────────────────────────────┐
│                    算法/执行器层 (Algorithm Layer)           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  调度组件 (Scheduling Components)                    │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────────────┐ │   │
│  │  │ JobSolver │ │ Assigner  │ │   Coordinator     │ │   │
│  │  │ 工序调度   │ │ 任务分配   │ │   多决策协同      │ │   │
│  │  └───────────┘ └───────────┘ └───────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  路径组件 (Routing Components)                       │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────────────┐ │   │
│  │  │   A*      │ │  Greedy   │ │    MAPF-GPT       │ │   │
│  │  │  路由求解  │ │  路由求解  │ │    深度学习       │ │   │
│  │  └───────────┘ └───────────┘ └───────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  仿真环境 (Simulation Environments)                  │   │
│  │  ┌─────────────────┐   ┌─────────────────────────┐ │   │
│  │  │  GridFactory    │   │    PacketFactory        │ │   │
│  │  │  网格环境        │   │    非网格环境           │ │   │
│  │  └─────────────────┘   └─────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 关键设计原则

| 原则 | 说明 |
|------|------|
| **服务层不关心算法实现** | 算法层完全独立，可自由替换 |
| **算法层不依赖具体业务接口** | 通过稳定的 Factory/Proxy 接口交互 |
| **环境即组件** | 所有算法环境遵循统一接口，可并行对比、快速替换 |
| **仿真即验证** | 所有调度策略必须在仿真中运行，支持异常注入、动态扰动 |

### 2.3 FactoryProxy 统一接口

所有工厂实现通过 `FactoryProxyProtocol` 暴露统一接口：

```python
class FactoryProxyProtocol:
    # 生命周期控制
    async def initialize()    # 初始化环境
    async def start()         # 启动仿真
    async def pause()         # 暂停仿真
    async def reset()         # 重置环境
    async def stop()          # 停止仿真

    # 状态获取
    async def get_state_snapshot() -> dict    # 状态快照
    async def get_metrics_snapshot() -> dict  # 指标快照
    async def get_state_events() -> list      # SSE 事件流
```

---

## 3. 仿真环境 A：GridFactory （1页）

### 3.1 环境定位

> **GridFactory 是面向 JSSP + MAPF 联合优化问题的网格仿真环境**

**适用场景**：

- 多智能体路径规划 (MAPF) 研究
- 作业车间调度 (JSSP) 研究
- 强化学习算法训练
- 学术基准测试

### 3.2 空间表示：离散网格

```
GridFactory 使用 Pogema 作为底层网格引擎

┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
│   │   │   │   │   │   │   │   │   │   │  y=0
├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
│   │   │ █ │   │   │   │   │ █ │   │   │  y=1  (█ = 障碍物)
├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
│   │ A │   │   │ M │   │   │   │   │   │  y=2  (A = AGV, M = Machine)
├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤
│   │   │   │   │   │   │   │   │   │   │  y=3
└───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
  x=0 x=1 x=2 x=3 x=4 x=5 x=6 x=7 x=8 x=9
```

**特点**：

- 空间是**均匀离散化**的
- AGV 移动是**网格步进**（上下左右四方向）
- 路径规划基于**网格可达性**

### 3.3 核心配置

```python
# 网格配置
GridConfig(
    size=20,              # 网格尺寸 20×20
    num_agents=4,         # AGV 数量
    density=0.1,          # 障碍物密度 10%
    obs_radius=5,         # AGV 感知半径
    max_episode_steps=256 # 最大步数
)

# 机器配置
MachineConfig(
    num_machines=4,
    strategy="custom",
    custom_positions=[(10,6), (10,9), (16,6), (16,9)]  # 网格坐标
)

# 任务配置
JobConfig(
    num_jobs=5,
    min_ops_per_job=2,    # 每个Job最少工序数
    max_ops_per_job=4     # 每个Job最多工序数
)
```

### 3.4 数据流与状态快照

```json
{
  "step": 42,
  "status": "running",
  "positions": [[5, 2], [3, 4], [10, 6], [8, 9]],   // AGV 坐标
  "targets": [[10, 6], [10, 9], [16, 6], [16, 9]],  // 目标坐标
  "machines": [
    {"id": 0, "location": [10, 6], "status": "WORKING"},
    {"id": 1, "location": [10, 9], "status": "IDLE"}
  ],
  "jobs": [
    {"job_id": 0, "status": "PROCESSING", "progress": 0.6}
  ],
  "agvs": [
    {"id": 0, "pos": [5, 2], "status": "MOVING", "current_task": {...}}
  ]
}
```

### 3.5 先验知识

| 知识类型 | 具体内容 |
|---------|---------|
| **空间先验** | 网格尺寸、障碍物分布、边界约束 |
| **机器先验** | 网格坐标位置、加工能力 |
| **任务先验** | 工序数量、工序顺序、机器约束 |
| **AGV先验** | 初始位置、感知半径、移动能力 |

### 3.6 环境接口

```python
from joint_sim import GridFactoryEnv, Coordinator

# 创建环境
env = GridFactoryEnv(
    grid_config=GridConfig(size=20, num_agents=4),
    machine_config=MachineConfig(num_machines=4),
    job_config=JobConfig(num_jobs=5)
)

# 创建协调器
coordinator = Coordinator(
    job_solver="greedy",
    route_solver="astar",
    assigner="nearest"
)

# 运行仿真
obs, info = env.reset()
for step in range(100):
    actions = coordinator.decide(obs)
    obs, rewards, terminated, truncated, info = env.step(actions)
    if terminated:
        break

# 保存动画
env.pogema_env.save_animation("simulation.svg")
```

---

## 4. 仿真环境 B：PacketFactory （1页）

### 4.1 环境定位

> **PacketFactory 是面向真实柔性产线仿真的非网格环境，支持复杂事件注入**

**适用场景**：

- 柔性制造系统 (FMS) 仿真
- 动态扰动与异常处理研究
- 数字孪生验证
- 产线配置优化

### 4.2 空间表示：图结构

```
PacketFactory 使用拓扑图表示空间

          [Point 1] ─────── [Point 2] ─────── [Point 3]
              │               │                   │
              │               │                   │
          [Point 4]       [Machine 0]         [Point 5]
              │                                   │
              │                                   │
          [Point 6] ─────── [Point 7] ─────── [Machine 1]

节点 (Point): 空间位置
边 (Link): 可通行路径（带权重）
机器 (Machine): 绑定到特定点位
```

**特点**：

- 空间是**拓扑图**，非均匀
- AGV 移动是**沿边跳转**
- 路径规划基于**图上最短路径**（Dijkstra）

### 4.3 配置文件体系

PacketFactory 采用三文件配置体系：

```
config_set/
├── map_config.yaml      # 地图布局、点位、连接关系
├── job_config.yaml      # Job 定义、工序、机器能力矩阵
└── event_config.yaml    # 事件类型声明、时间线
```

#### map_config.yaml - 地图配置

```yaml
config:
  points:              # 点位定义
    - point: {id: 1, coordinate: [1, 0]}
    - point: {id: 2, coordinate: [0, 1]}

  links:               # 连接关系（无向图）
    - link: {id: 1, begin: 1, end: 2}

  machines:            # 机器定义
    - machine: {id: 0, type: packet_factory.Machine, point_id: 2}

  agvs:                # AGV 定义
    - agv: {id: 1, point_id: 2, velocity: 1, capacity: 42}
```

#### job_config.yaml - 任务配置

```yaml
config:
  jobs:
    - job:
        id: 0
        operations:
          - operation:
              id: 0
              machines:              # 柔性加工：多机器可选
                - {id: 0, time: 5}   # 机器0需要5单位时间
                - {id: 2, time: 4}   # 机器2需要4单位时间（更快）
          - operation:
              id: 1
              machines:
                - {id: 4, time: 3}
                - {id: 2, time: 5}
                - {id: 1, time: 1}
```

**关键概念**：

- **Flexible Routing**: 同一工序可在多台机器上执行，时间不同
- **Precedence**: 工序按顺序执行，前一道完成后才能开始下一道

#### event_config.yaml - 事件配置

```yaml
config:
  event_type:          # 支持的事件类型
    - packet_factory.JUST_TEST
    - packet_factory.ENV_PAUSED
    - packet_factory.AGV_FAIL           # AGV 故障
    - packet_factory.MACHINE_FAIL       # Machine 故障
    - packet_factory.JOB_ADD            # 动态加单
    - packet_factory.ENV_RECOVER        # 环境恢复
```

### 4.4 回调系统架构

```
CallbackManager
├── MapLoader          # 从 YAML 加载地图和任务配置
├── Visualizer         # Pygame 实时渲染（支持截图推送）
├── EventQueue         # 基于最小堆的事件调度
└── BackendBridge      # 与后端服务通信
```

### 4.5 事件驱动机制

```python
# 事件基类
class BaseEvent:
    def trigger(self):
        """触发事件逻辑"""
        pass

    def recover(self):
        """恢复事件逻辑"""
        pass

# 示例：机器故障事件
class EventMachineFail(BaseEvent):
    def trigger(self):
        target_machine = self.env.hash_index['machines'][self.payload['id']]
        target_machine.set_status(MachineStatus.FAILED)

    def recover(self):
        target_machine.set_status(MachineStatus.READY)
```

### 4.6 Agent 插件化架构

```python
from executor.packet_factory.registry import register_component

@register_component("packet_factory.MyAgent")
class MyCustomAgent(BaseAgent):
    def sample(self, agvs, machines, jobs):
        # 自定义调度算法
        decisions = []
        for job in jobs:
            if not job.is_finished():
                op, agv, machine = self.decide(job, agvs, machines)
                decisions.append((op, agv, machine))
        return decisions, step_time
```

### 4.7 先验知识

| 知识类型 | 具体内容 |
|---------|---------|
| **空间先验** | 图拓扑结构、点位连接关系、边权重 |
| **机器先验** | 绑定点位、加工能力矩阵（多机器可选） |
| **任务先验** | 工序顺序、柔性加工时间、交期约束 |
| **事件先验** | 可注入事件类型、时间线编排 |

---

### 5. 不同仿真引擎和系统本身的交互统一性 （1页）

TODO：不应该凸显差异性，而是强调统一的接口和交互方式，说明未来还能够轻松扩展其他环境。

### 5.1 系统核心价值

| 价值维度 | 说明 |
|---------|------|
| **算法工程化** | 将调度算法从"离线求解器"提升为"可落地的生产决策系统" |
| **仿真验证闭环** | 避免纸面最优，所有策略必须在仿真中验证 |
| **环境可插拔** | GridFactory / PacketFactory 统一接口，自由切换 |
| **组件可替换** | JobSolver / RouteSolver / Assigner 工厂模式创建 |

### 5.2 技术亮点

1. **两层解耦架构**：服务层与算法层完全分离
2. **FactoryProxy 统一接口**：所有环境暴露相同 API
3. **Coordinator 协调器**：三层决策（调度/分配/路径）统一协同
4. **双环境支持**：网格环境 + 图结构环境，覆盖不同研究需求
5. **事件驱动机制**：支持故障注入、动态扰动、异常恢复

### 5.3 未来扩展方向

- 更多调度算法集成（强化学习、遗传算法等）
- 更多仿真环境支持（流水车间、装配线等）
- 数字孪生实时数据对接
- 多工厂协同调度


### 5.5 选择指南

| 研究目标 | 推荐环境 | 理由 |
|---------|---------|------|
| **MAPF 算法研究** | GridFactory | Pogema 提供成熟基准 |
| **强化学习训练** | GridFactory | 网格环境更适合 RL |
| **柔性产线仿真** | PacketFactory | 支持复杂配置和事件 |
| **动态扰动研究** | PacketFactory | 完整事件系统 |
| **数字孪生验证** | PacketFactory | 接近真实产线 |
| **学术基准测试** | GridFactory | 标准化环境 |


---

## 6. 实际系统演示（1页）

说明如何演示





---

## 附录

### A. 项目信息

- **项目名称**：SkyEngine（天工）
- **许可证**：Apache 2.0
- **GitHub**：<https://github.com/dayu-autostreamer/skyengine>

### B. 联系方式

- 谢磊：<lxie@nju.edu.cn>
- 吴昊：<wuhao@smail.nju.edu.cn>

---

> 本文档为 PPT 初稿，可直接导入到 PowerPoint / Keynote / Google Slides 等工具中生成演示文稿。
