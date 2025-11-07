# Agent基本设计与构思

针对柔性工厂仿真环境中AGV任务分配的三元组（AGV、Machine、Operation），以下是不同策略Agent的规约设计。每种策略关注不同的优化目标，适用于不同的生产场景：

```
0. 操作员策略 (Real Operator)

目标：预留外界与环境交流的接口,便于手动调整

决策逻辑：等待网络发送的策略,如果超时则使用默认策略
```

```
1. 随机策略 (Random Agent)

目标：基线策略，用于验证环境逻辑

决策逻辑：从空闲AGV集合中随机选择一个AGV, 从待处理Operation集合中随机选择一个Operation, 
为该Operation随机分配一个兼容的Machine（需满足工艺约束）

触发条件：当存在空闲AGV且有待处理Operation时
```

```
2. 最短加工时间优先 (SPT Agent)

目标：最小化机器平均等待时间

决策逻辑：遍历所有待处理Operation，计算其在兼容机器上的预估加工时间,
选择加工时间最短的Operation,选择可使该Operation加工时间最短的Machine,
分配距离该Machine最近的空闲AGV（减少运输时间）

优先级公式：Priority = 1 / (min_processing_time(op, machine))
```

```
3.机器负载均衡 (Load Balancing Agent)

目标：均衡各机器利用率，避免瓶颈

决策逻辑：计算每台机器的当前负载率（正在处理的任务数 + 排队任务数）选择负载率最低的机器,
从该机器兼容的Operation中选择最早释放的任务, 分配当前空闲的AGV（无需最近，因负载已平衡）
```
