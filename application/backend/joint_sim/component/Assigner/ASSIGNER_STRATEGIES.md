"""
AGV 任务分配器 (Assigner) 策略汇总

@Author: SkyEngine Team
@Date: 2025/12/06

===== 现有的 Assigner 策略 =====

1. Random Assigner (random)
   - 随机从待分配任务列表中选择一个任务
   - 适用于：基准测试、对比实验
   - 特点：无偏好，不考虑距离或负载
   - 使用：AssignerFactory.create("random")

2. Nearest Assigner (nearest) ⭐ 新增
   - 贪心距离优先策略
   - 选择距离 AGV 当前位置最近的任务源位置
   - 适用于：最小化路径长度
   - 特点：简单高效，易于理解
   - 使用：AssignerFactory.create("nearest")

3. Least Congestion Assigner (least_congestion) ⭐ 新增
   - 基于拥堵感知的任务分配
   - 综合考虑距离和路径上其他 AGV 的密度
   - 评分公式: score = distance + congestion_weight * congestion_count
   - 适用于：高负荷场景，需要避免碰撞
   - 特点：考虑全局拥堵情况
   - 使用：AssignerFactory.create("least_congestion")

4. Load Balance Assigner (load_balance) ⭐ 新增
   - 负载均衡策略
   - 优先为完成任务数较少的 AGV 分配任务
   - 适用于：确保 AGV 工作量均衡
   - 特点：避免某个 AGV 过载
   - 使用：AssignerFactory.create("load_balance")

5. Greedy Assigner (greedy)
   - 已定义但待实现的贪心策略
   - 可扩展为多种贪心标准

===== 使用示例 =====

from sky_executor.grid_factory.factory.Component.Coordinator.coordinator import Coordinator
from sky_executor.grid_factory.factory.Component.Assigner.assigner_factory import AssignerFactory

# 使用不同的 Assigner 创建 Coordinator
coord_random = Coordinator(assigner=AssignerFactory.create("random"))
coord_nearest = Coordinator(assigner=AssignerFactory.create("nearest"))
coord_congestion = Coordinator(assigner=AssignerFactory.create("least_congestion"))
coord_balanced = Coordinator(assigner=AssignerFactory.create("load_balance"))

===== Assigner 接口规范 =====

class Assigner(ABC):
    def plan(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        '''
        输入:
            obs: {
                "agents": List[AGV],                # AGV 列表，包含 id, pos, current_task, finished_tasks
                "machines": List[Machine],          # 机器列表，包含 id, location
                "pending_transfers": List[RoutingTask]  # 待分配任务列表
            }
        
        输出:
            {
                "assignments": Dict[agv_id, RoutingTask or None],  # 任务分配
                "pending_transfers": List[RoutingTask]              # 未分配的任务
            }
        '''
        pass

===== 性能对比预期 =====

场景: 5 jobs × 3 machines

| Assigner         | 平均 Makespan | 平均距离 | 拥堵事件 | 说明 |
|------------------|--------------|---------|--------|------|
| Random           | 基准值       | 基准值  | 高     | 无策略 |
| Nearest          | -5% ~ -10%   | 低      | 中     | 快速完成 |
| Least Congestion | -3% ~ -8%    | 中      | 低     | 避免碰撞 |
| Load Balance     | -2% ~ -6%    | 中      | 低     | 均匀分配 |

===== 扩展方向 =====

- Priority-based: 考虑任务优先级
- Machine Utilization: 平衡机器负载
- Energy Aware: 考虑能耗最优
- Deadlock Prevention: 主动避免死锁
- Hybrid: 多策略组合
"""
