# Pogema 使用指南

Pogema是一个用于多智能体路径规划（Multi-Agent Path Finding, MAPF）的环境框架。本文档基于测试文件总结了Pogema的常见用法，帮助您快速上手和使用。

这份文档基于对测试文件的分析，总结了Pogema的常见用法，包括：

1. 
   环境初始化与配置 - 如何创建和配置Pogema环境
2. 
   环境交互 - 如何与环境进行交互，包括动作空间和采样
3. 
   观察空间类型 - 不同类型的观察空间及其特点
4. 
   可视化与监控 - 如何使用AnimationMonitor进行可视化
5. 
   性能评估指标 - 如何获取和理解性能指标
6. 
   高级功能 - 包括环境持久化、回放和与Gymnasium的集成
7. 
   常见使用模式 - 如何运行完整回合和进行性能测试
8. 
   错误处理与边界情况 - 常见错误和处理方法

## 1. 环境初始化与配置

### 1.1 基本环境创建

```python
from pogema import pogema_v0, GridConfig

# 创建基本环境
env = pogema_v0(GridConfig(num_agents=2, size=6, obs_radius=2, density=0.3, seed=42))
```

### 1.2 GridConfig 配置参数

GridConfig是Pogema环境的核心配置类，支持以下主要参数：

- `num_agents`: 智能体数量
- `size`: 网格大小
- `obs_radius`: 观察半径
- `density`: 障碍物密度
- `seed`: 随机种子，用于生成确定性环境
- `max_episode_steps`: 最大步数
- `on_target`: 智能体到达目标后的行为，可选值：
  - `'finish'`: 到达目标后结束（默认）
  - `'nothing'`: 到达目标后不消失
  - `'restart'`: 到达目标后重新分配新目标（持续任务）

### 1.3 自定义地图和位置

#### 使用字符串定义地图

```python
grid_map = """
    .a...#.....
    .....#.....
    ..C.....b..
    .....#.....
    .....#.....
    #.####.....
    .....###.##
    .....#.....
    .c...#.....
    .B.......A.
    .....#.....
"""
env = pogema_v0(GridConfig(obs_radius=2, map=grid_map))
```

地图符号说明：
- `.`: 空地
- `#`: 障碍物
- 小写字母(a,b,c...): 智能体起始位置
- 大写字母(A,B,C...): 对应智能体的目标位置

#### 自定义起始和目标位置

```python
agents_xy = [(0, 0), (0, 1), (0, 2)]  # 智能体起始坐标
targets_xy = [(5, 5), (5, 6), (5, 7)]  # 目标坐标

grid_config = GridConfig(
    size=10, 
    num_agents=3,
    agents_xy=agents_xy,
    targets_xy=targets_xy
)
env = pogema_v0(grid_config=grid_config)
```

## 2. 环境交互

### 2.1 基本交互流程

```python
# 重置环境
obs, info = env.reset()

# 执行动作
actions = [0, 1]  # 对应两个智能体的动作
obs, reward, terminated, truncated, info = env.step(actions)

# 判断是否结束
if all(terminated) or all(truncated):
    # 环境结束
    pass
```

### 2.2 动作空间

Pogema默认使用以下动作映射：
- `0`: 不动 (noop)
- `1`: 向上 (up)
- `2`: 向下 (down)
- `3`: 向左 (left)
- `4`: 向右 (right)

### 2.3 随机采样动作

```python
# 随机采样动作
actions = env.sample_actions()
# 或
actions = env.action_space.sample()
```

## 3. 观察空间类型

Pogema支持不同类型的观察空间：

### 3.1 默认观察空间

默认观察空间返回网格状态的数值表示。

### 3.2 POMAPF观察空间

部分可观察的多智能体路径规划观察空间：

```python
env = pogema_v0(GridConfig(
    num_agents=2, 
    size=6, 
    obs_radius=2, 
    density=0.3, 
    seed=42, 
    observation_type='POMAPF'
))
```

POMAPF观察空间包含：
- `agents`: 智能体位置
- `obstacles`: 障碍物位置
- `xy`: 当前坐标
- `target_xy`: 目标坐标

### 3.3 MAPF观察空间

完全可观察的多智能体路径规划观察空间：

```python
env = pogema_v0(GridConfig(
    num_agents=2, 
    size=6, 
    obs_radius=2, 
    density=0.3, 
    seed=42, 
    observation_type='MAPF'
))
```

MAPF观察空间包含：
- `global_obstacles`: 全局障碍物位置
- `global_xy`: 全局坐标
- `global_target_xy`: 全局目标坐标

## 4. 可视化与监控

### 4.1 使用AnimationMonitor

```python
from pogema import AnimationMonitor

env = pogema_v0(GridConfig(num_agents=2, size=6, obs_radius=2, density=0.3))
env = AnimationMonitor(env)  # 包装环境以支持可视化

# 正常使用环境
env.reset()
while True:
    _, _, terminated, truncated, _ = env.step(env.action_space.sample())
    if all(terminated) or all(truncated):
        break
```

## 5. 性能评估指标

Pogema提供了多种评估指标，可以通过info字典访问：

```python
obs, reward, terminated, truncated, info = env.step(actions)
metrics = info[0]['metrics']
```

主要指标包括：
- `CSR` (Completion Success Rate): 完成率，所有智能体成功到达目标的比例
- `ISR` (Individual Success Rate): 个体成功率，单个智能体成功到达目标的比例

## 6. 高级功能

### 6.1 持久化环境与回放

Pogema支持环境状态的持久化和回放：

```python
env = pogema_v0(
    grid_config=GridConfig(
        on_target='finish', 
        seed=42, 
        num_agents=8, 
        density=0.132, 
        size=8, 
        obs_radius=2,
        persistent=True  # 启用持久化
    )
)

# 正常使用环境
env.reset()
for _ in range(steps):
    actions = action_sampler.sample_actions(dim=env.get_num_agents())
    obs, reward, terminated, truncated, info = env.step(actions)
    
# 回放：回到初始状态
while env.step_back():
    pass

# 重新执行相同的动作序列
# ...
```

### 6.2 与Gymnasium集成

Pogema可以与Gymnasium框架集成使用：

```python
import gymnasium

env = gymnasium.make('Pogema-v0',
                     grid_config=GridConfig(
                         num_agents=2, 
                         size=6, 
                         obs_radius=2, 
                         density=0.3, 
                         seed=42
                     ))
```

## 7. 常见使用模式

### 7.1 运行完整的回合

```python
def run_episode(grid_config=None, env=None):
    if env is None:
        env = pogema_v0(grid_config)
    env.reset()

    obs, rewards, terminated, truncated, infos = env.reset(), [None], [False], [False], [None]

    results = [[obs, rewards, terminated, truncated, infos]]
    while True:
        results.append(env.step(env.sample_actions()))
        terminated, truncated = results[-1][2], results[-1][3]
        if all(terminated) or all(truncated):
            break
    return results
```

### 7.2 性能测试

```python
import time

start_time = time.monotonic()
run_episode(grid_config=gc)
end_time = time.monotonic()
steps_per_second = gc.max_episode_steps / (end_time - start_time)
```

## 8. 错误处理与边界情况

- 当无法生成有效的环境时（例如，障碍物密度过高或智能体数量过多），会抛出`OverflowError`
- 当配置参数无效时（例如，网格大小过小或智能体数量为0），会抛出`ValidationError`
- 当自定义位置超出边界时，会抛出`IndexError`

## 9. 总结

Pogema是一个灵活且功能丰富的多智能体路径规划环境，支持：
- 自定义地图和智能体配置
- 不同类型的观察空间
- 可视化和监控
- 性能评估指标
- 环境状态的持久化和回放
- 与Gymnasium框架的集成

通过本文档的指南，您应该能够开始使用Pogema进行多智能体路径规划的研究和实验。