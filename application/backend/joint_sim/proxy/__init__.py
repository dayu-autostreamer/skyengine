"""
Proxy 模块 - 环境代理

此模块提供环境代理功能，用于管理与渲染器的通信。

====== 主要组件 ======
1. ExecutionStatus - 执行状态枚举
2. GridFactoryProxy - GridFactory 环境代理实现
3. ALGORITHM_PRESETS - 预设算法配置列表

====== 使用示例 ======
from joint_sim.proxy import GridFactoryProxy, ExecutionStatus

# 创建代理
proxy = GridFactoryProxy()
proxy.set_config({"path": "config.json"})
proxy.set_algorithm("greedy+astar+nearest")

# 初始化
await proxy.initialize()

# 启动
await proxy.start()

# 获取状态
snapshot = await proxy.get_state_snapshot()

# 暂停
await proxy.pause()

# 重置
await proxy.reset()

# 停止
await proxy.stop()
"""

from joint_sim.proxy.grid_factory_proxy import (
    ExecutionStatus,
    GridFactoryProxy,
    ALGORITHM_PRESETS,
)

__all__ = [
    "ExecutionStatus",
    "GridFactoryProxy",
    "ALGORITHM_PRESETS",
]
