"""
预实验框架改进总结
===== 更新内容 =====

### 1️⃣ 新增 Assigner 策略 (4个)

#### Nearest Assigner (nearest)
- 🎯 目标: 最小化 AGV 到任务源的距离
- 📊 评分标准: Manhattan distance to source machine
- 💡 使用场景: 最优路径长度，低延迟
- ⚙️ 复杂度: O(n*m)，n=AGV数，m=任务数

#### Least Congestion Assigner (least_congestion)
- 🎯 目标: 避免高拥堵区域，减少碰撞
- 📊 评分标准: distance + 2 * nearby_agv_count
- 💡 使用场景: 高负荷环境，多AGV协调
- 🔴 防碰撞: 在分配前检查路径拥堵程度

#### Load Balance Assigner (load_balance)
- 🎯 目标: 均衡 AGV 工作负载
- 📊 分配策略: 优先分配给已完成任务最少的 AGV
- 💡 使用场景: 提高整体资源利用率
- ⚖️ 负载均衡: 避免个别 AGV 过载

#### Random Assigner (random) - 既有
- 🎯 基准策略，用于对比
- 📊 选择: 完全随机
- 💡 使用场景: 性能基准测试

---

### 2️⃣ CongestionHeatmapMonitor 修复

#### 问题修复清单:
1. ✅ **环境包装处理**
   - 修复: 递归查找原始环境的 grid_config
   - 处理: Wrapper 嵌套导致的属性丢失

2. ✅ **位置追踪初始化**
   - 修复: 使用 defaultdict 防止 KeyError
   - 改进: 安全的位置历史记录

3. ✅ **pogema_env 获取**
   - 修复: 处理多层 Wrapper 嵌套
   - 改进: 递归查找最内层真实环境

4. ✅ **拥堵指标计算**
   - 修复: 正确识别 AGV 空闲状态
   - 改进: 独立统计等待和冲突
   - 防止: 双重计数

5. ✅ **冲突检测**
   - 修复: 使用 defaultdict 避免字典键错误
   - 改进: 清晰的多 AGV 同位置检测

---

### 3️⃣ Metrics 框架整合

#### 可用的 Metrics Monitors:
- `job_time_monitor`: 任务完成时间指标 (makespan, flow_time)
- `stats_save_monitor`: 状态快照保存
- `congestion_heatmap_monitor`: 拥堵热力图 (新)

#### 热力图输出:
```
output_dir/
├── congestion_heatmap.png      # 4个子热力图
│   ├── Overall Congestion      # 总体拥堵 (加权)
│   ├── AGV Idle Locations      # 空闲位置
│   ├── AGV Waiting Locations   # 等待位置
│   └── AGV Conflict Locations  # 冲突位置
└── congestion_data.json        # 原始数据
```

---

### 4️⃣ 使用示例

#### 方式 1: 创建不同 Assigner 的 Coordinator
```python
from sky_executor.grid_factory.factory.Component.Coordinator.coordinator import Coordinator
from sky_executor.grid_factory.factory.Component.Assigner.assigner_factory import AssignerFactory

# 创建多个 Coordinator 用不同的 Assigner
coordinators = {
    "random": Coordinator(assigner=AssignerFactory.create("random")),
    "nearest": Coordinator(assigner=AssignerFactory.create("nearest")),
    "congestion": Coordinator(assigner=AssignerFactory.create("least_congestion")),
    "balanced": Coordinator(assigner=AssignerFactory.create("load_balance")),
}

for name, coord in coordinators.items():
    env = GridFactoryEnv(...)
    obs, info = env.reset()
    
    for step in range(max_steps):
        actions = coord.decide(obs)
        obs, rewards, term, trunc, info = env.step(actions)
```

#### 方式 2: 使用 Metrics Monitor
```python
from sky_executor.grid_factory.factory.Metrics.MetricsMonitorFactory import MetricsMonitorFactory

# 包装环境以收集指标
env = GridFactoryEnv(...)
env = MetricsMonitorFactory.create("congestion_heatmap_monitor")(env)

# 运行实验...
for step in range(max_steps):
    actions = coord.decide(obs)
    obs, _, _, _, _ = env.step(actions)

# 生成热力图
env.generate_heatmap()
stats = env.get_congestion_stats()
print(f"Total idle time: {stats['total_idle_time']}")
print(f"Total conflicts: {stats['total_conflicts']}")
```

---

### 5️⃣ 性能预测

基于多 Assigner 的对比实验预期结果:

| Metric           | Random | Nearest | L-Cong | L-Bal |
|------------------|--------|---------|--------|-------|
| Makespan (基准)  | 100.0  | 92-95   | 95-98  | 96-99 |
| Avg Distance     | 高     | **低**  | 中     | 中    |
| Conflict Events  | 多     | 中      | **少** | 少    |
| Load Balance     | 差     | 差      | 中     | **优** |

---

### 6️⃣ 文件清单

#### 新增文件:
- `Assigner/nearest_assigner/assigner.py` - 最近距离分配器
- `Assigner/least_congestion_assigner/assigner.py` - 拥堵感知分配器
- `Assigner/load_balance_assigner/assigner.py` - 负载均衡分配器
- `Assigner/ASSIGNER_STRATEGIES.md` - 策略文档
- `test/test_assigners.py` - 单元测试

#### 修复文件:
- `Metrics/CongestionHeatmapMonitor.py` - 修复 5 处问题

---

### 7️⃣ 下一步建议

1. 运行对比实验: `experiment/pre_experiment/run_preexperiment.py`
2. 分析热力图输出，识别瓶颈区域
3. 根据拥堵模式优化 Assigner 策略
4. 考虑混合策略 (e.g., 动态切换)

"""
