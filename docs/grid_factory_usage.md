# 基于Pogema的网格工厂环境使用指南

## 概述

`GridFactoryEnv` 是一个基于Pogema的网格工厂环境，支持多智能体路径规划和工厂任务调度。它集成了事件系统、回调机制和可视化功能。

## 主要特性

### 1. Pogema集成
- 使用Pogema作为底层网格环境
- 支持多智能体路径规划
- 可配置的网格大小、智能体数量、障碍物密度等

### 2. 工厂组件支持
- AGV（自动导引车）管理
- 机器设备管理
- 作业任务调度
- 图结构表示

### 3. 事件系统
- 集成事件队列和事件管理器
- 支持异步事件处理
- 可视化事件触发

### 4. 回调机制
- 灵活的回调管理器
- 支持多种回调类型
- 可扩展的组件系统

## 基本使用

### 1. 创建环境

```python
from pogema import GridConfig
from sky_executor.grid_factory.factory.grid_factory_env.grid_factory_env import GridFactoryEnv

# 创建网格配置
grid_config = GridConfig(
    num_agents=4,  # 智能体数量
    size=20,  # 网格大小 (20x20)
    density=0.3,  # 障碍物密度
    seed=42,  # 随机种子
    max_episode_steps=256,  # 最大步数
    obs_radius=5,  # 观察半径
    collision_system='priority',  # 碰撞系统
    observation_type='POMAPF',  # 观察类型
    on_target='restart'  # 到达目标后的行为
)

# 创建环境
env = GridFactoryEnv(
    grid_config=grid_config,
    use_pogema=True,
    env_config={'enable_logging': True}
)
```

### 2. 环境操作

```python
# 重置环境
obs, info = env.reset(seed=42)

# 环境步进
actions = {'decisions': [], 'step_time': 1.0}
obs, rewards, terminations, truncations, infos = env.step(actions)

# 获取环境信息
positions = env.get_agent_positions()
targets = env.get_agent_targets()
agents_info = env.get_agents_info()
```

### 3. 状态管理

```python
# 设置环境时间线
env.set_env_timeline(100.0)

# 获取当前时间
current_time = env.get_env_timeline()

# 检查环境状态
is_finished = env.env_is_finished()
```

## 高级功能

### 1. 回调管理器集成

```python
from sky_executor.grid_factory.grid_factory_callback.callback_manager import CallbackManager

# 创建回调管理器
callback_manager = CallbackManager()

# 设置回调管理器
env.set_callback_manager(callback_manager)

# 刷新环境状态
env.refresh_status()
```

### 2. 可视化支持

```python
# 渲染观察信息
env.render_observation()

# 渲染环境
env.render()
```

### 3. 事件处理

```python
# 处理事件
event_happened = env.deal_event()

# 检查任务完成
job_finished = env.check_job_finished()
```

## 配置选项

### GridConfig 参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| num_agents | int | 4 | 智能体数量 |
| size | int | 20 | 网格大小 |
| density | float | 0.3 | 障碍物密度 (0-1) |
| seed | int | 42 | 随机种子 |
| max_episode_steps | int | 256 | 最大步数 |
| obs_radius | int | 5 | 观察半径 |
| collision_system | str | 'priority' | 碰撞系统 |
| observation_type | str | 'POMAPF' | 观察类型 |
| on_target | str | 'restart' | 到达目标后的行为 |

### 环境配置

```python
env_config = {
    'enable_logging': True,      # 启用日志记录
    'enable_animation': False,   # 启用动画
    'debug_mode': False         # 调试模式
}
```

## 示例代码

### 完整示例

```python
import numpy as np
from pogema import GridConfig
from sky_executor.grid_factory.factory.grid_factory_env.grid_factory_env import GridFactoryEnv


def run_simulation():
    # 创建配置
    config = GridConfig(
        num_agents=6,
        size=15,
        density=0.2,
        seed=123,
        max_episode_steps=200
    )

    # 创建环境
    env = GridFactoryEnv(grid_config=config)

    # 重置环境
    obs, info = env.reset(seed=123)

    # 运行仿真
    for step in range(100):
        # 生成随机动作
        actions = np.random.randint(0, 5, size=config.num_agents).tolist()

        # 执行步进
        obs, rewards, terminations, truncations, infos = env.step({
            'decisions': [],
            'step_time': 1.0
        })

        # 打印状态
        if step % 10 == 0:
            print(f"Step {step}: Positions {env.get_agent_positions()}")

        # 检查终止条件
        if any(terminations.values()):
            print("Episode finished!")
            break

    return True


if __name__ == '__main__':
    run_simulation()
```

## 故障排除

### 常见问题

1. **Pogema导入错误**
   ```bash
   pip install sky_pogema
   ```

2. **环境初始化失败**
   - 检查GridConfig参数是否有效
   - 确保智能体数量不超过网格大小

3. **回调管理器错误**
   - 确保CallbackManager正确初始化
   - 检查回调函数是否正确注册

### 调试模式

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 创建调试环境
env = GridFactoryEnv(
    grid_config=config,
    env_config={'debug_mode': True}
)
```

## 性能优化

### 1. 减少观察半径
```python
config.obs_radius = 3  # 默认5
```

### 2. 限制智能体数量
```python
config.num_agents = 4  # 根据计算资源调整
```

### 3. 使用较小的网格
```python
config.size = 10  # 默认20
```

## 扩展功能

### 自定义智能体
```python
class CustomAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
    
    def sample(self, agvs, machines, jobs, timeline):
        # 自定义决策逻辑
        return [], 1.0

# 使用自定义智能体
env = GridFactoryEnv(agent=CustomAgent(1))
```

### 自定义事件处理
```python
def custom_event_handler(event, env):
    # 自定义事件处理逻辑
    pass

# 注册事件处理器
env.event_queue.event_manager.register_handler('custom_event', custom_event_handler)
```

## 总结

基于Pogema的网格工厂环境提供了强大的多智能体路径规划能力，同时保持了与原有工厂系统的兼容性。通过合理的配置和使用，可以实现高效的工厂仿真和优化。