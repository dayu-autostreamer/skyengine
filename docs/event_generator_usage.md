# EventGenerator 使用文档

## 概述

EventGenerator 是一个强大的事件生成器，用于在仿真系统中按时间片和概率生成各种事件。它支持多种概率分布、突发事件模拟、事件队列管理等功能。

## 主要特性

1. **多种概率分布支持**
   - 均匀分布 (Uniform)
   - 泊松分布 (Poisson)
   - 指数分布 (Exponential)
   - 自定义分布 (Custom)

2. **事件生成策略**
   - 可配置的生成概率
   - 最小/最大生成间隔
   - 突发事件模拟
   - 自定义payload生成器

3. **事件队列管理**
   - 线程安全的事件队列
   - 批量事件获取
   - 队列大小监控

4. **统计和监控**
   - 事件生成统计
   - 按类型分类统计
   - 生成时间记录

## 基本使用

### 1. 创建EventGenerator

```python
from sky_executor.utils.event.event_manager.EventManager import EventManager
from sky_executor.utils.event import EventGenerator

# 创建事件管理器
event_manager = EventManager()

# 添加支持的事件类型
event_manager.add_event('packet_factory.AGV_FAIL')
event_manager.add_event('packet_factory.MACHINE_FAIL')

# 创建事件生成器
generator = EventGenerator(event_manager)
```

### 2. 配置事件生成

```python
from sky_executor.utils.event import EventGenerationStrategy

# 添加事件配置
generator.add_event_config(
    event_type='packet_factory.AGV_FAIL',
    probability=0.1,  # 10% 生成概率
    strategy=EventGenerationStrategy.UNIFORM,
    min_interval=1.0,
    max_interval=10.0,
    burst_probability=0.05,  # 5% 突发事件概率
    burst_multiplier=3
)
```

### 3. 开始和停止事件生成

```python
# 开始生成事件
generator.start_generation(time_step=0.5)

# 运行一段时间...
time.sleep(10)

# 获取生成的事件
events = generator.get_next_events(max_count=10)

# 停止生成
generator.stop_generation()
```

## 配置文件使用

### 1. 创建配置文件

创建 `config/event_generator_config.yaml`:

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
    
    packet_factory.MACHINE_FAIL:
      probability: 0.03
      strategy: "poisson"
      min_interval: 5.0
      max_interval: 20.0
      burst_probability: 0.01
      burst_multiplier: 2
```

### 2. 从配置文件加载

```python
# 从配置文件创建事件生成器
generator = EventGenerator(event_manager, 'config/event_generator_config.yaml')
```

## 高级功能

### 1. 自定义Payload生成器

```python
def custom_job_payload():
    return {
        'job': {
            'id': f"JOB_{int(time.time())}",
            'priority': random.randint(1, 5),
            'deadline': time.time() + 300
        }
    }

generator.add_event_config(
    event_type='packet_factory.JOB_ADD',
    probability=0.2,
    payload_generator=custom_job_payload
)
```

### 2. 事件生成条件

```python
# 添加生成条件
generator.add_event_config(
    event_type='packet_factory.AGV_FAIL',
    probability=0.1,
    conditions={
        'time_of_day': 'working_hours',
        'system_load': 'high'
    }
)
```

### 3. 统计信息获取

```python
# 获取生成统计
stats = generator.get_generation_stats()
print(f"总事件数: {stats['total_events']}")
print(f"按类型统计: {stats['events_by_type']}")
print(f"队列大小: {stats['queue_size']}")
```

## 事件类型支持

EventGenerator 支持以下事件类型：

- `packet_factory.AGV_FAIL` - AGV故障事件
- `packet_factory.MACHINE_FAIL` - 机器故障事件
- `packet_factory.JOB_ADD` - 作业添加事件
- `packet_factory.ENV_PAUSED` - 环境暂停事件
- `packet_factory.ENV_RECOVER` - 环境恢复事件
- `packet_factory.ENV_RESTART` - 环境重启事件

## 最佳实践

1. **合理设置概率**: 避免设置过高的生成概率，以免造成事件队列溢出
2. **使用配置文件**: 对于复杂的配置，建议使用YAML配置文件
3. **监控队列大小**: 定期检查队列大小，避免内存溢出
4. **合理设置时间步长**: 根据系统性能调整时间步长
5. **使用统计信息**: 利用统计信息监控事件生成情况

## 故障排除

### 常见问题

1. **事件生成器无法启动**
   - 检查事件管理器是否正确初始化
   - 确认事件类型已正确注册

2. **事件队列溢出**
   - 降低事件生成概率
   - 增加事件处理频率
   - 检查事件处理逻辑

3. **配置文件加载失败**
   - 检查文件路径是否正确
   - 确认YAML格式是否正确
   - 查看日志中的错误信息

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查生成器状态
print(f"生成器运行状态: {generator.is_running}")
print(f"当前时间: {generator.current_time}")
print(f"队列大小: {len(generator.event_queue)}")
```

## 示例代码

完整的使用示例请参考 `test/event_test/test_event_generator.py` 文件。
