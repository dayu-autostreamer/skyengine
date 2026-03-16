# PacketFactory 快速入门指南

## 📋 目录

- [系统概述](#系统概述)
- [架构设计](#架构设计)
- [核心功能说明](#核心功能说明)
- [配置文件详解](#配置文件详解)
- [API 接口文档](#API接口文档)
- [前端组件说明](#前端组件说明)
- [常见问题](#常见问题)
- [进阶使用](#进阶使用)
- [技术支持](#技术支持)

---

## 系统概述

**PacketFactory（包裹工厂）** 是 skyengine 系统中的核心柔性制造仿真模块，提供：

- ✅ **多 AGV 协同调度** - 支持多智能体路径规划（MAPF）
- ✅ **工序级任务调度** - JobShop 问题建模与求解
- ✅ **实时可视化仿真** - Pygame 渲染 + 前端动态展示
- ✅ **事件驱动机制** - 支持故障注入、异常恢复等动态扰动
- ✅ **插件化架构** - 智能体、回调、事件均可热插拔

### 核心特性

| 特性 | 说明 |
|------|------|
| 两层解耦 | 服务层（API）与环境层（仿真）完全分离 |
| 统一接口 | 通过 Proxy 模式提供标准化 API |
| 实时推送 | SSE 流式输出仿真状态 |
| 配置热切换 | 支持运行时动态更换工厂配置 |

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────┐
│         前端 (Vue3 + Element Plus)   │
│  ┌─────────────────────────────┐    │
│  │ PacketFactoryManage.vue     │    │
│  │ - 左侧控制面板              │    │
│  │ - 中间地图显示区            │    │
│  │ - 右侧日志与进度区          │    │
│  └──────────────┬──────────────┘    │
└─────────────────┼───────────────────┘
                  │ HTTP/SSE
┌─────────────────▼───────────────────┐
│         后端服务层 (FastAPI)         │
│  ┌─────────────────────────────┐    │
│  │ PacketFactoryProxy          │    │
│  │ - 路由注册与管理            │    │
│  │ - 生命周期控制              │    │
│  └──────────────┬──────────────┘    │
│                 │                   │
│  ┌──────────────▼──────────────┐    │
│  │ BackendCore / APIHandler    │    │
│  │ - API 路由处理               │    │
│  │ - 业务逻辑封装              │    │
│  └──────────────┬──────────────┘    │
└─────────────────┼───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│        环境算法层 (PettingZoo)       │
│  ┌─────────────────────────────┐    │
│  │ PacketFactoryEnv            │    │
│  │ - 仿真环境核心              │    │
│  │ - AGV/Machine/Job 管理       │    │
│  └──────────────┬──────────────┘    │
│                 │                   │
│  ┌──────────────▼──────────────┐    │
│  │ 回调系统 (CallbackManager)  │    │
│  │ - MapLoader: 地图加载       │    │
│  │ - Visualizer: 可视化渲染    │    │
│  │ - EventQueue: 事件队列      │    │
│  └──────────────┬──────────────┘    │
│                 │                   │
│  ┌──────────────▼──────────────┐    │
│  │ Agent (智能体)              │    │
│  │ - RandomAgent: 随机策略     │    │
│  │ - GreedyAgent: 贪婪策略     │    │
│  │ - LifecycleAgent: 生命周期  │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

### 核心组件说明

#### 1. 前端组件 (`application/frontend/src/views/factory/`)

- **PacketFactoryManage.vue**: 主管理界面
  - 左侧：工厂控制、AGV 控制、Machine 控制、Job 控制
  - 中间：地图实时显示
  - 右侧：配置上传、日志下载、Job 进度

#### 2. 后端代理 (`application/backend/core/`)

- **PacketFactoryProxy.py**: 工厂代理类
  - 继承 `BaseFactoryProxy`
  - 持有 `BackendCore` 和 `APIHandler` 实例
  - 自动注册所有后端路由到 `RouteRegistry`

#### 3. 后端服务 (`application/backend/packet_factory/`)

- **backend_server.py**: API 路由定义
  - `APIHandler` 类包含所有路由处理函数
  - 使用 `NetworkAPIPath` 统一管理路由常量
  
- **backend_core.py**: 核心业务逻辑
  - `BackendCore` 类管理仿真环境生命周期
  - 线程池管理仿真运行

#### 4. 环境层 (`executor/packet_factory/`)

- **packet_factory_env.py**: PettingZoo 并行环境
  - 管理 Jobs、Machines、AGVs、Graph
  - 提供标准 Gym 接口：`reset()`, `step()`, `render()`

- **回调系统**:
  - `MapLoader`: 从 YAML 加载地图和任务配置
  - `Visualizer`: Pygame 实时渲染（支持截图推送到前端）
  - `EventQueue`: 基于最小堆的事件调度

- **Agent 系统**:
  - `BaseAgent`: 智能体基类
  - `RandomAgent`: 随机分配策略
  - `GreedyAgent`: 贪婪优化策略
  - `LifecycleAgent`: 完整生命周期管理

---

## 核心功能说明

### 1. 工厂生命周期管理

#### 操作流程

1. **选择工厂配置**
   - 在下拉框中选择已上传的配置集（如 `template_config_set` 示例）

2. **Render（渲染）**
   - 点击 "Render" 按钮加载地图
   - 后端启动仿真环境线程
   - 前端开始轮询地图图片更新

3. **Start（启动）**
   - 点击 "Start" 启动仿真运行
   - AGV 和 Machine 开始工作
   - 地图实时更新状态

4. **Pause（暂停）**
   - 暂停当前仿真
   - 所有 AGV/Machine 停止动作

5. **Reset（重置）**
   - 重置环境到初始状态
   - 清空所有 Job 进度

#### 速度调节

使用滑块调整仿真速度等级（1-10）：

- Level 1: 最慢（适合调试）
- Level 5: 正常速度
- Level 10: 最快

### 2. AGV 控制

#### 查看 AGV 列表

下拉框显示所有可用 AGV（从 `/api/agvs` 获取）

#### 暂停/恢复单个 AGV

1. 选择目标 AGV
2. 点击 "Pause" 暂停该 AGV
3. 点击 "Go" 恢复运行

**底层逻辑**:

- 暂停：将 AGV 加入 `agv_pause_queue`
- 恢复：将 AGV 加入 `agv_resume_queue`
- Visualizer 在下一帧处理队列

### 3. Machine 控制

与 AGV 控制类似：

1. 选择目标 Machine
2. 点击 "Pause" 暂停加工
3. 点击 "Go" 恢复加工

**注意**: Machine 暂停后，正在加工的工件会停留在当前进度

### 4. Job 管理

#### 添加 Job

1. 从下拉框选择 Job 模板
2. 点击 "Add" 添加到生产队列
3. 右侧面板显示 Job 进度

#### Job 进度跟踪

右侧面板实时显示：

- Job ID
- 状态：Processing... / Finished
- 进度条：0-100%

### 5. 配置文件管理

#### 上传配置集

一个完整的配置集应包含 3 个文件：

- `map_config.yaml` - 地图布局、点位、连接关系
- `job_config.yaml` - Job 定义、工序、机器能力
- `event_config.yaml` - 事件类型声明、时间线

**操作步骤**:

1. 输入配置集名称（如 `my_custom_factory`）
2. 拖拽或点击上传 3 个 YAML 文件
3. 点击 "Upload" 提交

**保存位置**:

```
application/backend/packet_factory/config_set/<config_name>/
```

#### 获取标准配置

点击 "Get Standard" 下载 `template_config_set.zip`，包含：

- 标准地图配置（10 个点位、6 台机器、4 台 AGV）
- 10 个 Job 模板（每个 5-6 道工序）
- 基础事件类型定义

### 6. 日志下载

#### Backend Log

- 记录后端 API 调用、仿真状态变化
- 位置：`executor/packet_factory/logger/backend_logs/`

#### System Log

- 记录系统级事件、错误信息
- 位置：`executor/packet_factory/logger/system_logs/`

---

## 配置文件详解

### map_config.yaml - 地图配置

```yaml
config:
  width: 20          # 地图宽度（预留字段）
  height: 30         # 地图高度（预留字段）
  
  blocks:            # 障碍物区域（预留字段）
    - zone:
        id: 1
        zone: [1, 2, 10, 12]
  
  points:            # 关键点位
    - point:
        id: 1
        coordinate: [1, 0]
    - point:
        id: 2
        coordinate: [0, 1]
    # ... 更多点位
  
  machines:          # 机器定义
    - machine:
        id: 0        # 机器 ID（从 0 开始）
        type: packet_factory.Machine
        point_id: 2  # 关联的点位 ID
  
  links:             # 点位连接关系（无向图）
    - link:
        id: 1
        begin: 1
        end: 2
    # ... 更多连接
  
  agvs:              # AGV 定义
    - agv:
        id: 1
        type: packet_factory.Agv
        point_id: 2   # 初始位置
        velocity: 1   # 移动速度
        capacity: 42  # 载货容量（预留字段）
```

### job_config.yaml - 任务配置

```yaml
config:
  jobs:
    - job:
        id: 0        # Job ID
        operations:  # 工序列表
          - operation:
              id: 0
              machines:           # 可执行的机器及时间
                - { id: 0, time: 5 }   # 机器 0 需要 5 单位时间
                - { id: 2, time: 4 }   # 机器 2 需要 4 单位时间
          - operation:
              id: 1
              machines:
                - { id: 4, time: 3 }
                - { id: 2, time: 5 }
                - { id: 1, time: 1 }
          # ... 更多工序
```

**关键概念**:

- **Operation（工序）**: Job 的基本组成单元
- **Flexible Routing**: 同一工序可在多台机器上执行，时间不同
- **Precedence**: 工序按顺序执行，前一道完成后才能开始下一道

### event_config.yaml - 事件配置

```yaml
config:
  event_type:        # 声明支持的事件类型
    - packet_factory.JUST_TEST          # 测试事件
    - packet_factory.ENV_PAUSED         # 环境暂停
    - packet_factory.ENV_RECOVER        # 环境恢复
    - packet_factory.ENV_RESTART        # 环境重启
    - packet_factory.AGV_FAIL           # AGV 故障
    - packet_factory.MACHINE_FAIL       # Machine 故障
    - packet_factory.JOB_ADD            # Job 添加

  # event_timeline:  # 预定义事件时间线（可选）
  #   - event:
  #       timestamp: 1
  #       type: packet_factory.JUST_TEST
  #       args: ['trigger', {'data': 233}]
```

**事件机制**:

- 所有事件继承自 `BaseEvent`
- 必须实现 `trigger()` 和 `recover()` 方法
- 通过 `EventManager` 统一管理
- 支持事件注入和时间线编排

---

## API接口文档

### 工厂控制接口

#### GET `/api/factory/alive`

检查工厂是否存活

**响应示例**:

```json
{
  "is_alive": true
}
```

#### POST `/api/factory/start`

启动工厂仿真

**响应示例**:

```json
{
  "action": "start"
}
```

#### POST `/api/factory/pause`

暂停工厂仿真

#### POST `/api/factory/reset`

重置工厂到初始状态

#### POST `/api/factory/speed`

调整仿真速度

**请求体**:

```json
{
  "speedLevel": 5
}
```

### AGV 控制接口

#### GET `/api/agvs`

获取所有 AGV 列表

**响应示例**:

```json
{
  "agvs": [
    {"id": 1},
    {"id": 2},
    {"id": 3},
    {"id": 4}
  ]
}
```

#### POST `/api/agv/pause/{agvId}`

暂停指定 AGV

#### POST `/api/agv/resume/{agvId}`

恢复指定 AGV

### Machine 控制接口

#### GET `/api/machines`

获取所有 Machine 列表

#### POST `/api/machine/pause/{machineId}`

暂停指定 Machine

#### POST `/api/machine/resume/{machineId}`

恢复指定 Machine

### Job 控制接口

#### GET `/api/jobs`

获取 Job 模板列表

#### POST `/api/job/add/{jobId}`

添加 Job 到生产队列

#### GET `/api/jobs/progress`

获取所有 Job 的进度

**响应示例**:

```json
{
  "jobs": [
    {"id": 0, "status": "PROCESSING", "progress": 45.5},
    {"id": 1, "status": "FINISHED", "progress": 100.0},
    {"id": 2, "status": "PROCESSING", "progress": 23.8}
  ]
}
```

### 地图与配置接口

#### GET `/api/map/update`

获取当前地图图片（PNG 格式）

**说明**: 前端每秒调用 4 次（250ms 间隔）实现动画效果

#### POST `/api/map/render`

渲染指定工厂配置的地图

**请求体**:

```json
{
  "target_factory": "template_config_set"
}
```

#### GET `/api/factory/list`

获取所有可用的工厂配置列表

**响应示例**:

```json
{
  "factory_list": [
    {"id": "template_config_set"},
    {"id": "pipeline_config_set"},
    {"id": "my_custom_factory"}
  ],
  "success": true
}
```

#### POST `/{config_name}/yaml/upload`

上传新的配置集

**Content-Type**: `multipart/form-data`

**参数**:

- `config_name`: 配置集名称
- `file`: UploadFile（支持多文件）

#### GET `/api/standard/get`

下载标准配置模板（ZIP 压缩包）

### 日志接口

#### POST `/api/log/download`

下载日志文件

**请求体**:

```json
{
  "file_type": "backend"  // 或 "system"
}
```

**返回**: FileResponse（直接下载）

---

## 前端组件说明

### PacketFactoryManage.vue 结构

```vue
<template>
  <div class="factory-manage-container">
    <!-- 左侧面板 -->
    <div class="left-panel">
      <el-card>Control Panel</el-card>      <!-- 工厂总控 -->
      <el-card>AGV Control</el-card>        <!-- AGV 控制 -->
      <el-card>Machine Control</el-card>    <!-- Machine 控制 -->
      <el-card>Job Control</el-card>        <!-- Job 控制 -->
    </div>
    
    <!-- 中间面板 -->
    <div class="middle-panel">
      <el-image :src="map_src" />           <!-- 地图显示 -->
    </div>
    
    <!-- 右侧面板 -->
    <div class="right-side-panel">
      <div class="config-section">          <!-- 配置上传 -->
        <el-upload />
      </div>
      <el-card>Log Download</el-card>       <!-- 日志下载 -->
      <el-card>Job Process</el-card>        <!-- Job 进度 -->
    </div>
  </div>
</template>
```

---

## 常见问题

### Q1: 地图图片无法加载

**可能原因**:

1. 未点击 "Render" 按钮初始化环境
2. 后端线程未启动成功
3. 配置文件路径错误

### Q2: AGV/Machine 控制无响应

**原因**: 仿真未启动或已暂停

**解决方案**:

1. 确保已点击 "Start" 启动仿真
2. 检查 Factory 状态是否为 "运行中"
3. 刷新页面重新连接

### Q3: 上传配置文件失败

**要求**:

- 必须包含 3 个 YAML 文件
- 文件名必须为：`map_config.yaml`, `job_config.yaml`, `event_config.yaml`
- 配置集名称不能包含特殊字符

**正确示例**:

```
my_factory/
├── map_config.yaml
├── job_config.yaml
└── event_config.yaml
```

### Q4: Job 进度一直为 0

**检查项**:

1. 确认已添加 Job 到生产队列
2. 检查 AGV 是否正常运输
3. 验证 Machine 是否有空闲产能

---

## 进阶使用

### 自定义 Agent 开发

1. 继承 `BaseAgent` 类
2. 实现 `sample()` 方法（核心决策逻辑）
3. 使用 `@register_component` 装饰器注册

```python
from executor.packet_factory.packet_factory.Agent.BaseAgent import BaseAgent
from executor.packet_factory.registry import register_component

@register_component("packet_factory.MyCustomAgent")
class MyCustomAgent(BaseAgent):
    def sample(self, agvs, machines, jobs):
        # 自定义调度算法
        actions = []
        for job in jobs:
            if not job.is_finished():
                # 智能决策逻辑
                op, agv, machine = self.decide(job, agvs, machines)
                actions.append((op, agv, machine))
        return actions
```

### 自定义事件开发

1. 继承 `BaseEvent` 类
2. 实现 `trigger()` 和 `recover()` 方法
3. 使用 `@register_event` 装饰器注册

```python
from executor.packet_factory.event.event.BaseEvent import BaseEvent
from executor.packet_factory.registry import register_event

@register_event('packet_factory.CUSTOM_EVENT')
class EventCustom(BaseEvent):
    event_type = EventType.CUSTOM_EVENT
    
    def trigger(self):
        # 触发逻辑
        target_machine = self.env.hash_index['machines'][self.payload['id']]
        target_machine.set_status(MachineStatus.FAILED)
    
    def recover(self):
        # 恢复逻辑
        target_machine.set_status(MachineStatus.READY)
```

## 技术支持

- **项目仓库**: <https://github.com/your-org/skyengine>
- **问题反馈**: 提交 Issue 时请附上后端日志和配置文件
- **文档维护**: 更新后请同步修改 `QUICKSTART.md`

---

**祝您使用愉快！** 🚀

如有任何问题，欢迎随时联系开发团队。
