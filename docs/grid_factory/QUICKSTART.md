# Joint Simulation (joint_sim) 快速入门指南

本文档说明如何集成、使用和二次开发 `joint_sim` 联合仿真库。该库提供 JobShop + MAPF 联合仿真系统，支持 JSSP 作业调度与 AGV 路径规划的联合优化。

## 目录

- [安装与集成](#安装与集成)
- [快速开始](#快速开始)
- [核心组件](#核心组件)
- [Gym 环境接口](#gym-环境接口)
- [Proxy 服务层](#proxy-服务层)
- [JSON 配置加载](#json-配置加载)
- [前端集成](#前端集成)
- [二次开发](#二次开发)

---

## 安装与集成

### 从 PyPI 安装

```bash
uv add joint-sim
```

> 如果搜索不到，请清理缓存：uv cache clean

或使用 pip：

```bash
pip install joint-sim
```

### 从源码安装

```bash
git clone https://github.com/skyrimforest/SkyEngine.git
cd SkyEngine
uv sync
```

> 注意，当你安装joint-sim库后，就可以使用grid_factory等相关配置了。
> 另外，推荐单独使用joint-sim强化学习库进行算法复现与研究。

---

## 快速开始

### 基本使用

```python
from joint_sim import GridFactoryEnv, create_env_from_config

# 方式1: 从配置文件创建环境
env = create_env_from_config("path/to/grid_factory.json")

# 方式2: 直接创建环境（使用默认配置）
env = GridFactoryEnv()

# 初始化环境
obs, info = env.reset()

# 运行仿真
for step in range(100):
    # 使用协调器决策（推荐）
    actions = coordinator.decide(obs)
    obs, rewards, terminated, truncated, info = env.step(actions)

    if terminated or truncated:
        break
```

### 使用配置文件

```python
from joint_sim.io import load_grid_factory_config, create_env_from_config

# 加载配置
config = load_grid_factory_config("grid_factory.json")

# 创建环境
env = create_env_from_config(config)

# 重置并运行
obs, info = env.reset()
```

---

## 核心组件

### 模块结构

```
joint_sim/
├── __init__.py              # 主入口，导出核心类
├── grid_factory_env.py      # Gymnasium 环境实现
├── io/                      # 配置加载模块
│   ├── use_io.py           # 配置解析函数
│   └── __init__.py
├── proxy/                   # 服务代理模块
│   ├── grid_factory_proxy.py
│   └── __init__.py
├── component/               # 算法组件
│   ├── Coordinator/        # 协调器
│   ├── JobSolver/          # 任务调度器
│   ├── RouteSolver/        # 路由求解器
│   └── Assigner/           # 分配器
└── utils/                   # 工具和数据结构
    ├── structure.py        # 核心数据类
    └── __init__.py
```

### 导入示例

```python
# 主入口
from joint_sim import GridFactoryEnv, GridFactoryProxy, create_env_from_config

# IO 模块
from joint_sim.io import (
    load_grid_factory_config,
    parse_grid_config,
    parse_machine_config,
    parse_job_config,
)

# 组件模块
from joint_sim.component import Coordinator, JobSolverFactory, RouteSolverFactory, AssignerFactory

# 数据结构
from joint_sim.utils import Operation, Job, Machine, RoutingTask, AGV
```

---

## Gym 环境接口

### GridFactoryEnv

`GridFactoryEnv` 是基于 PettingZoo ParallelEnv 的多智能体环境，兼容 Gymnasium 接口。

```python
from joint_sim import GridFactoryEnv
from pogema import GridConfig
from joint_sim.utils import MachineConfig, JobConfig

# 创建环境
env = GridFactoryEnv(
    grid_config=GridConfig(
        size=20,
        num_agents=4,
        density=0.0,
        max_episode_steps=256,
        obs_radius=5,
    ),
    machine_config=MachineConfig(
        num_machines=4,
        strategy="custom",
        custom_positions=[(10, 6), (10, 9), (16, 6), (16, 9)],
    ),
    job_config=JobConfig(
        num_jobs=5,
        min_ops_per_job=2,
        max_ops_per_job=4,
    ),
)

# 重置环境
obs, info = env.reset()

# 执行动作
# actions: Dict[agent_id, action] 或 List[action]
obs, rewards, terminated, truncated, info = env.step(actions)

# 环境属性
print(env.pogema_env)       # 底层 Pogema 环境
print(env.init_machines)    # 机器列表
print(env.init_jobs)        # 任务列表
```

### 环境方法

| 方法 | 说明 |
|------|------|
| `reset()` | 重置环境，返回 (obs, info) |
| `step(actions)` | 执行动作，返回 (obs, rewards, terminated, truncated, info) |
| `show_actions(actions)` | 打印动作信息 |
| `show_jobs()` | 打印任务信息 |
| `set_env_timeline(t)` | 设置环境时间线 |

---

## Proxy 服务层

### GridFactoryProxy

`GridFactoryProxy` 提供异步控制接口，适用于 Web 服务和前端集成。

```python
from joint_sim.proxy import GridFactoryProxy, ExecutionStatus

# 创建代理
proxy = GridFactoryProxy()

# 设置配置
proxy.set_config({"path": "grid_factory.json"})  # 或传入完整配置字典
proxy.set_algorithm("greedy+astar+nearest")

# 异步操作
async def run_simulation():
    # 初始化
    await proxy.initialize()

    # 启动
    await proxy.start()

    # 获取状态快照
    snapshot = await proxy.get_state_snapshot()
    print(f"Step: {snapshot['step']}, Status: {snapshot['status']}")

    # 获取事件流
    events = await proxy.get_state_events()

    # 暂停/恢复
    await proxy.pause()
    await proxy.start()

    # 重置
    await proxy.reset()

    # 停止
    await proxy.stop()
```

### ExecutionStatus

```python
from joint_sim.proxy import ExecutionStatus

class ExecutionStatus(str, Enum):
    IDLE = "idle"          # 空闲
    RUNNING = "running"    # 运行中
    PAUSED = "paused"      # 已暂停
    STOPPED = "stopped"    # 已停止
    ERROR = "error"        # 错误
```

### 代理方法

| 方法 | 说明 |
|------|------|
| `set_config(config)` | 设置配置 |
| `set_algorithm(algo)` | 设置算法 |
| `initialize()` | 初始化环境 |
| `start()` | 启动仿真 |
| `pause()` | 暂停仿真 |
| `reset()` | 重置环境 |
| `stop()` | 停止仿真 |
| `get_state_snapshot()` | 获取状态快照 |
| `get_state_events()` | 获取状态事件队列 |

---

## JSON 配置加载

### 配置文件结构

```json
{
    "id": "grid_factory",
    "name": "测试产线",
    "version": "1.2.0",
    "topology": {
        "gridWidth": 20,
        "gridHeight": 14,
        "machines": {
            "MACHINE_1_1": {
                "id": "TABLE_1_MACHINE_1",
                "name": "PLC 1-2",
                "location": [10, 6],
                "size": [1, 1],
                "status": "IDLE"
            }
        }
    },
    "agvs": [
        {
            "id": 0,
            "name": "AGV-01",
            "initialLocation": [5, 2],
            "velocity": 1.0,
            "capacity": 100,
            "status": "IDLE"
        }
    ],
    "jobs": {
        "job_list": [
            {
                "job_id": 0,
                "name": "电池模组-A01",
                "operations": [
                    {"machine_id": 0, "duration": 5, "name": "涂胶"},
                    {"machine_id": 1, "duration": 3, "name": "贴片"},
                    {"machine_id": 2, "duration": 4, "name": "焊接"}
                ],
                "arrival_time": 0,
                "due_time": 50,
                "priority": 1
            }
        ]
    }
}
```

### 配置解析

```python
from joint_sim.io import (
    load_grid_factory_config,
    parse_grid_config,
    parse_machine_config,
    parse_job_config,
    create_env_from_config,
)

# 加载配置
config = load_grid_factory_config("grid_factory.json")

# 解析各部分配置
grid_config = parse_grid_config(config)
machine_config, positions = parse_machine_config(config)
job_config = parse_job_config(config, machine_config.num_machines)

# 直接创建环境
env = create_env_from_config("grid_factory.json")
# 或使用字典
env = create_env_from_config(config)
```

---

## 算法配置

### 可用算法

| 类型 | 算法 | 说明 |
|------|------|------|
| JobSolver | `greedy` | 贪心调度 |
| JobSolver | `best` | 最优调度 (OR-Tools) |
| JobSolver | `priority` | 优先级调度 |
| RouteSolver | `astar` | A* 路由 |
| RouteSolver | `greedy` | 贪心路由 |
| RouteSolver | `instant` | 即时路由 |
| RouteSolver | `mapf_gpt` | GPT 路由 |
| Assigner | `nearest` | 最近分配 |
| Assigner | `random` | 随机分配 |
| Assigner | `load_balance` | 负载均衡 |
| Assigner | `greedy` | 贪心分配 |

### 使用 Coordinator

```python
from joint_sim.component import Coordinator

# 使用预设算法组合
coordinator = Coordinator(
    job_solver="greedy",
    route_solver="astar",
    assigner="nearest"
)

# 决策
actions = coordinator.decide(observation)
```

### 预设算法组合

```python
from joint_sim.proxy import ALGORITHM_PRESETS

# 可用预设
presets = [
    "greedy+astar+nearest",       # 贪心调度 + A*路由 + 最近分配
    "best+astar+load_balance",    # 最优调度 + A*路由 + 负载均衡
    "greedy+mapf_gpt+random",     # 贪心调度 + GPT路由 + 随机分配
]
```

---

## 前端集成

### FastAPI 集成示例

```python
from fastapi import FastAPI, WebSocket
from joint_sim.proxy import GridFactoryProxy

app = FastAPI()
proxy = GridFactoryProxy()

@app.post("/factory/control/reset")
async def reset_factory(config: dict):
    proxy.set_config(config)
    proxy.set_algorithm("greedy+astar+nearest")
    await proxy.initialize()
    return {"status": "initialized"}

@app.post("/factory/control/play")
async def play_factory():
    await proxy.start()
    return {"status": "running"}

@app.post("/factory/control/pause")
async def pause_factory():
    await proxy.pause()
    return {"status": "paused"}

@app.get("/stream/state")
async def stream_state():
    snapshot = await proxy.get_state_snapshot()
    events = await proxy.get_state_events()
    return {"snapshot": snapshot, "events": events}
```

### WebSocket 状态推送

```python
@app.websocket("/ws/state")
async def websocket_state(websocket: WebSocket):
    await websocket.accept()
    while True:
        events = await proxy.get_state_events()
        if events:
            await websocket.send_json(events)
        await asyncio.sleep(0.1)
```

---

## 二次开发

当前提供了多种内置算法，有些时候初次运行可能需要下载模型，请确保网络通畅

```bash 
# 下载模型中：
Xet Storage is enabled for this repo, but the 'hf_xet' package is not installed. Falling back to regular HTTP download. For better performance, install the package with: `pip install huggingface_hub[hf_xet]` or `pip install hf_xet`
model-6M.pt:  82%|███████████████████████████████████████████████████████████▉             | 62.9M/76.6M [00:14<00:05, 2.70MB/s] 

```

### 自定义 JobSolver

```python
from joint_sim.component.JobSolver.template_solver.job_solver import JobSolver

class MyJobSolver(JobSolver):
    def solve(self, jobs, machines, **kwargs):
        # 实现自定义调度逻辑
        schedule = {}
        for job in jobs:
            for op in job.ops:
                # 分配机器和时间
                machine_id = self._select_machine(op, machines)
                start_time = self._calc_start_time(machine_id)
                schedule[(job.job_id, op.op_id)] = (machine_id, start_time)
        return schedule

# 注册到工厂
from joint_sim.component import JobSolverFactory
JobSolverFactory.register("my_solver", MyJobSolver)
```

### 自定义 RouteSolver

```python
from joint_sim.component.RouteSolver.template_solver.route_solver import RouteSolver

class MyRouteSolver(RouteSolver):
    def solve(self, tasks, agents, grid, **kwargs):
        # 实现自定义路由逻辑
        actions = {}
        for agent_id, agent in enumerate(agents):
            if agent.current_task:
                actions[agent_id] = self._get_next_action(agent, grid)
        return actions
```

### 自定义 Assigner

```python
from joint_sim.component.Assigner.template_assigner.assigner import Assigner

class MyAssigner(Assigner):
    def assign(self, tasks, agents, machines, **kwargs):
        # 实现自定义分配逻辑
        assignments = {}
        for task in tasks:
            agent_id = self._select_agent(task, agents)
            assignments[task.task_id] = agent_id
        return assignments
```

---

## 数据结构

### 核心类

```python
from joint_sim.utils import Operation, Job, Machine, RoutingTask, AGV

# 工序
op = Operation(
    job_id=0,
    op_id=0,
    machine_options=[0, 1],
    proc_time=5.0,
    status="PENDING"
)

# 任务
job = Job(
    job_id=0,
    ops=[op1, op2, op3],
    release=0.0,
    due=50.0
)

# 机器
machine = Machine(
    machine_id=0,
    location=(10, 6)
)

# 路由任务
task = RoutingTask(
    task_id=0,
    job_id=0,
    op_id=0,
    source=(5, 2),
    destination=(10, 6),
    ready_time=0.0
)

# AGV
agv = AGV(
    id=0,
    pos=(5, 2),
    current_task=None,
    finished_tasks=[]
)
```

---

## 常见问题

### Q: 如何获取当前环境状态？

```python
# 通过环境
obs, info = env.reset()
machines = env.init_machines
jobs = env.init_jobs

# 通过代理
snapshot = await proxy.get_state_snapshot()
```

### Q: 如何保存仿真动画？

```python
env = GridFactoryEnv()
env.reset()

# 运行仿真...

# 保存动画
env.pogema_env.save_animation("simulation.svg")
```

### Q: 如何处理多智能体动作？

```python
# 方式1: 字典
actions = {0: 1, 1: 2, 2: 0, 3: 3}  # agent_id -> action

# 方式2: 列表
actions = [1, 2, 0, 3]  # 按顺序对应各智能体

obs, rewards, terminated, truncated, info = env.step(actions)
```

---

## 版本历史

- **0.1.2** - 添加 Proxy 服务层，完善 IO 模块
- **0.1.1** - 添加 JSON 配置加载
- **0.1.0** - 初始版本

---

## 联系方式

- **Author**: Skyrim Forestsea
- **Email**: <hitskyrim@qq.com>
- **GitHub**: <https://github.com/Skyrimforest/SkyEngine>
