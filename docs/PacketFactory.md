
## 4. 仿真环境 B：PacketFactory （1-2页）

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

### 4.8 当前支持的调度算法等


---
