# EventQueue与EventGenerator集成使用文档

## 概述

EventQueue现在集成了EventGenerator，提供了智能的事件生成和队列管理功能。这个集成版本支持自动事件生成、时间同步、统计监控等高级功能。

## 主要特性

1. **自动事件生成**: 集成EventGenerator，按配置自动生成事件
2. **时间同步**: EventGenerator的时间与EventQueue的时间保持同步
3. **智能队列管理**: 基于时间戳的优先级队列，支持事件调度
4. **统计监控**: 集成事件生成和处理统计信息
5. **灵活配置**: 支持配置文件或代码配置

## 基本使用

### 1. 创建集成的EventQueue

```python
from sky_simulator.event.event_manager.EventManager import EventManager
from sky_simulator.call_back.base_callback.EventQueue import EventQueue

# 创建事件管理器
event_manager = EventManager()
event_manager.add_event('packet_factory.AGV_FAIL')
event_manager.add_event('packet_factory.MACHINE_FAIL')

# 创建集成的EventQueue
event_queue = EventQueue(
    event_manager=event_manager,
    auto_generation=True  # 启用自动生成
)
```

### 2. 配置事件生成

```python
from sky_simulator.event.event_manager.EventGenerator import EventGenerationStrategy

# 添加事件生成配置
event_queue.add_event_config(
    event_type='packet_factory.AGV_FAIL',
    probability=0.1,
    strategy=EventGenerationStrategy.UNIFORM
)

# 设置生成间隔
event_queue.set_generation_interval(1.0)  # 1秒间隔
```

### 3. 使用EventQueue

```python
# 设置环境
event_queue.set_env(environment)

# 在仿真循环中调用
while simulation_running:
    ready_events = event_queue()  # 自动生成并处理事件
    
    if ready_events:
        print(f"处理了 {len(ready_events)} 个事件")
        for event in ready_events:
            print(f"  - {event}")
```

## 配置文件使用

### 1. 从配置文件创建

```python
# 从配置文件创建EventQueue
event_queue = EventQueue(
    event_manager=event_manager,
    auto_generation=True,
    generation_config_path='config/event_generator_config.yaml'
)
```

### 2. 配置文件格式

```yaml
event_generation:
  time_step: 0.1
  
  events:
    packet_factory.AGV_FAIL:
      probability: 0.05
      strategy: "uniform"
      min_interval: 2.0
      max_interval: 10.0
      burst_probability: 0.02
      burst_multiplier: 3
```

## 高级功能

### 1. 手动控制事件生成

```python
# 创建时禁用自动生成
event_queue = EventQueue(
    event_manager=event_manager,
    auto_generation=False
)

# 手动启用
event_queue.enable_auto_generation()

# 手动禁用
event_queue.disable_auto_generation()
```

### 2. 统计信息获取

```python
# 获取详细统计信息
stats = event_queue.get_generation_stats()

print(f"总处理事件数: {stats['total_events_processed']}")
print(f"总生成事件数: {stats['total_events_generated']}")
print(f"队列大小: {stats['queue_size']}")
print(f"按类型统计: {stats['events_by_type']}")
print(f"自动生成状态: {stats['auto_generation_enabled']}")

# 获取EventGenerator统计
if 'generator_stats' in stats:
    gen_stats = stats['generator_stats']
    print(f"生成器统计: {gen_stats}")
```

### 3. 队列管理

```python
# 检查队列状态
print(f"队列大小: {len(event_queue)}")
print(f"下一个事件时间: {event_queue.peek_next_event()}")

# 清空队列
event_queue.clear_queue()

# 重置统计
event_queue.reset_stats()
```

### 4. 动态配置

```python
# 动态添加事件配置
event_queue.add_event_config(
    event_type='packet_factory.JOB_ADD',
    probability=0.2,
    strategy=EventGenerationStrategy.EXPONENTIAL,
    min_interval=1.0,
    max_interval=5.0
)

# 调整生成间隔
event_queue.set_generation_interval(0.5)  # 0.5秒间隔
```

## 集成架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EventQueue    │    │  EventGenerator  │    │  EventManager   │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │ Time Queue  │ │    │ │ Auto Generate │ │    │ │ Event Types │ │
│ │ (Priority)  │ │◄───┤ │ (Probability) │ │    │ │ (Registry)  │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │ Statistics  │ │    │ │ Config Load  │ │    │ │ Event Exec  │ │
│ │ (Monitor)   │ │    │ │ (YAML/Code)  │ │    │ │ (Trigger)   │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 最佳实践

### 1. 合理设置生成参数

```python
# 避免过高的生成概率
event_queue.add_event_config(
    event_type='packet_factory.AGV_FAIL',
    probability=0.05,  # 5%概率，避免事件过多
    strategy=EventGenerationStrategy.UNIFORM
)

# 设置合理的生成间隔
event_queue.set_generation_interval(1.0)  # 1秒间隔
```

### 2. 监控队列状态

```python
# 定期检查队列大小
stats = event_queue.get_generation_stats()
if stats['queue_size'] > 1000:  # 队列过大
    print("警告：事件队列过大，考虑调整生成参数")
```

### 3. 使用配置文件

```python
# 对于复杂配置，使用YAML文件
event_queue = EventQueue(
    event_manager=event_manager,
    auto_generation=True,
    generation_config_path='config/event_generator_config.yaml'
)
```

### 4. 错误处理

```python
try:
    ready_events = event_queue()
    # 处理事件...
except Exception as e:
    print(f"事件处理错误: {e}")
    # 错误恢复逻辑...
```

## 性能优化

### 1. 调整生成间隔

```python
# 根据系统性能调整
event_queue.set_generation_interval(0.1)  # 高频生成
# 或
event_queue.set_generation_interval(1.0)  # 低频生成
```

### 2. 批量处理事件

```python
# EventQueue自动批量处理，无需手动优化
ready_events = event_queue()  # 自动获取所有就绪事件
```

### 3. 内存管理

```python
# 定期清理队列
if len(event_queue) > 10000:
    event_queue.clear_queue()
    print("清理事件队列")
```

## 故障排除

### 常见问题

1. **事件生成器未启动**
   ```python
   # 检查自动生成状态
   stats = event_queue.get_generation_stats()
   if not stats['auto_generation_enabled']:
       event_queue.enable_auto_generation()
   ```

2. **队列溢出**
   ```python
   # 检查队列大小
   if len(event_queue) > 1000:
       event_queue.clear_queue()
       # 调整生成参数
   ```

3. **配置文件加载失败**
   ```python
   # 使用默认配置
   event_queue = EventQueue(
       event_manager=event_manager,
       auto_generation=True  # 不使用配置文件
   )
   ```

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查队列状态
print(f"队列大小: {len(event_queue)}")
print(f"下一个事件: {event_queue.peek_next_event()}")
print(f"所有事件: {event_queue.list_all_events()}")
```

## 示例代码

完整的使用示例请参考 `test/event_test/test_eventqueue_integration.py` 文件。

## 迁移指南

### 从旧版本EventQueue迁移

```python
# 旧版本
old_queue = EventQueue(event_manager)

# 新版本（向后兼容）
new_queue = EventQueue(event_manager, auto_generation=False)

# 新版本（启用自动生成）
new_queue = EventQueue(event_manager, auto_generation=True)
```

### 从独立EventGenerator迁移

```python
# 旧版本
generator = EventGenerator(event_manager)
queue = EventQueue(event_manager)

# 新版本（集成）
queue = EventQueue(event_manager, auto_generation=True)
```

这个集成版本提供了更简单、更强大的事件管理功能，同时保持了向后兼容性。
