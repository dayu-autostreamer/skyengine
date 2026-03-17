"""
@Project ：SkyEngine
@File    ：ORScheduler_Fixed.py
@Description: 修正后的 OR-Tools JSSP+AGV 最优求解器，用于 Benchmark 验证
"""

from typing import List, Callable
from ortools.sat.python import cp_model
from joint_sim.utils.structure import (
    Job,
    Machine,
    JobSolverResult,
)

class OptimalORToolsSolver:
    def __init__(
        self, 
        jobs: List[Job], 
        machines: List[Machine],
        consider_agv_delay: bool = False,
        agv_delay_estimator: Callable[[int, int], float] = None,
        n_agvs: int = None
    ):
        self.jobs = jobs
        self.machines = machines
        self.consider_agv_delay = consider_agv_delay
        self.n_agvs = n_agvs
        
        if agv_delay_estimator is None:
            machine_positions = {m.id: m.location for m in machines}
            def default_estimator(from_id: int, to_id: int) -> float:
                if from_id == to_id: return 0.0
                from_pos = machine_positions.get(from_id, (0, 0))
                to_pos = machine_positions.get(to_id, (0, 0))
                return float(abs(from_pos[0] - to_pos[0]) + abs(from_pos[1] - to_pos[1]))
            self.agv_delay_estimator = default_estimator
        else:
            self.agv_delay_estimator = agv_delay_estimator

    def solve(self) -> JobSolverResult:
        model = cp_model.CpModel()

        # ------------------------------
        # 1. Horizon 修正：增加运输时间的余量
        # ------------------------------
        total_proc_time = sum(o.proc_time for j in self.jobs for o in j.ops)
        # 估算一个宽松的运输时间总和 (比如总工序数 * 最大地图直径)
        estimated_transport_slack = len([o for j in self.jobs for o in j.ops]) * 100 
        horizon = total_proc_time + estimated_transport_slack

        # ------------------------------
        # 变量存储
        # ------------------------------
        start_vars = {}
        end_vars = {}
        interval_vars = {}
        machine_choice = {} # (jid, oid) -> {mid: literal}
        machine_to_intervals = {m.id: [] for m in self.machines}
        
        # 存储转运 Interval 用于 Cumulative 约束
        transfer_intervals_list = []
        # 存储转运的元数据以便结果重构
        transfer_vars_map = {} # (jid, oid, from_m, to_m) -> (start_var, end_var, literal)

        # ------------------------------
        # 2. 创建工序变量 (Operation Variables)
        # ------------------------------
        for job in self.jobs:
            for op in job.ops:
                jid, oid = op.job_id, op.op_id
                machine_choice[(jid, oid)] = {}
                choice_literals = []

                for mid in op.machine_options:
                    s = model.NewIntVar(0, horizon, f"s_{jid}_{oid}_m{mid}")
                    e = model.NewIntVar(0, horizon, f"e_{jid}_{oid}_m{mid}")
                    lit = model.NewBoolVar(f"choose_{jid}_{oid}_m{mid}")

                    interval = model.NewOptionalIntervalVar(
                        s, op.proc_time, e, lit, f"I_{jid}_{oid}_m{mid}"
                    )

                    start_vars[(jid, oid, mid)] = s
                    end_vars[(jid, oid, mid)] = e
                    interval_vars[(jid, oid, mid)] = interval
                    machine_choice[(jid, oid)][mid] = lit
                    machine_to_intervals[mid].append(interval)
                    choice_literals.append(lit)

                # 约束：每个工序必须选且只选一个机器
                model.Add(sum(choice_literals) == 1)

        # ------------------------------
        # 3. 前后工序约束与转运逻辑 (Core Logic)
        # ------------------------------
        for job in self.jobs:
            for op in job.ops:
                jid, oid = op.job_id, op.op_id
                if oid == 0:
                    continue

                prev_op = job.ops[oid - 1]

                for mid in op.machine_options:
                    for pmid in prev_op.machine_options:
                        # 只有当前后两个机器都被选中时，以下约束才生效
                        activation_lit = model.NewBoolVar(f"act_{jid}_{oid}_{pmid}_{mid}")
                        model.AddImplication(activation_lit, machine_choice[(jid, oid-1)][pmid])
                        model.AddImplication(activation_lit, machine_choice[(jid, oid)][mid])
                        # 反向约束：如果没被同时选中，activation_lit 为 False (Optional, 但有助于求解速度)
                        model.AddBoolOr([machine_choice[(jid, oid-1)][pmid].Not(), 
                                         machine_choice[(jid, oid)][mid].Not(), 
                                         activation_lit])

                        # 基础延时计算
                        dist_delay = 0
                        if self.consider_agv_delay:
                            dist_delay = int(self.agv_delay_estimator(pmid, mid))

                        # --- 核心修正开始 ---
                        
                        # 场景 A: 考虑 AGV 资源限制 或 显式建模转运过程
                        if self.consider_agv_delay:
                            # 创建转运变量
                            t_start = model.NewIntVar(0, horizon, f"t_s_{jid}_{oid}_{pmid}_{mid}")
                            t_end = model.NewIntVar(0, horizon, f"t_e_{jid}_{oid}_{pmid}_{mid}")
                            
                            # 1. 转运必须在上一道工序结束后开始 (允许等待，buffer allowed)
                            # t_start >= prev_end
                            model.Add(t_start >= end_vars[(jid, oid-1, pmid)]).OnlyEnforceIf(activation_lit)
                            
                            # 2. 转运持续时间
                            model.Add(t_end == t_start + dist_delay).OnlyEnforceIf(activation_lit)
                            
                            # 3. 下一道工序必须在转运结束后开始
                            # curr_start >= t_end
                            model.Add(start_vars[(jid, oid, mid)] >= t_end).OnlyEnforceIf(activation_lit)

                            # 4. 注册到 AGV 资源约束 (仅当距离 > 0 时占用 AGV)
                            if dist_delay > 0:
                                t_interval = model.NewOptionalIntervalVar(
                                    t_start, dist_delay, t_end, activation_lit, 
                                    f"T_I_{jid}_{oid}_{pmid}_{mid}"
                                )
                                transfer_intervals_list.append(t_interval)
                            
                            # 记录以便结果输出
                            transfer_vars_map[(jid, oid, pmid, mid)] = (t_start, t_end, activation_lit)

                        else:
                            # 场景 B: 简单 JSSP (瞬间传送 或 仅固定延迟)
                            # prev_end <= curr_start
                            model.Add(end_vars[(jid, oid-1, pmid)] <= start_vars[(jid, oid, mid)]).OnlyEnforceIf(activation_lit)
                        
                        # --- 核心修正结束 ---

        # ------------------------------
        # 4. 资源约束
        # ------------------------------
        # 机器不重叠
        for mid, intervals in machine_to_intervals.items():
            model.AddNoOverlap(intervals)

        # AGV 数量限制 (Cumulative)
        if self.n_agvs is not None and self.consider_agv_delay and transfer_intervals_list:
            # 只有当 n_agvs 有限制时才加
            demands = [1] * len(transfer_intervals_list)
            model.AddCumulative(transfer_intervals_list, demands, self.n_agvs)

        # ------------------------------
        # 5. 目标函数
        # ------------------------------
        makespan = model.NewIntVar(0, horizon, "makespan")
        all_ends = [end_vars[k] for k in end_vars]
        model.AddMaxEquality(makespan, all_ends)
        model.Minimize(makespan)

        # ------------------------------
        # 6. 求解
        # ------------------------------
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 300.0 # 稍微增加一点时间
        solver.parameters.num_search_workers = 8
        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
             raise RuntimeError(f"No feasible solution found. Status: {status}")

        # ------------------------------
        # 7. 结果构造 (保持原有结构)
        # ------------------------------
        machine_schedule = {m.id: [] for m in self.machines}
        op_meta = {}
        transfers = []

        for job in self.jobs:
            prev_machine = None
            prev_end_val = 0.0
            
            for op in job.ops:
                jid, oid = op.job_id, op.op_id
                
                # 找到被选中的机器
                chosen_mid = None
                for mid, lit in machine_choice[(jid, oid)].items():
                    if solver.BooleanValue(lit):
                        chosen_mid = mid
                        break
                
                s_val = solver.Value(start_vars[(jid, oid, chosen_mid)])
                e_val = solver.Value(end_vars[(jid, oid, chosen_mid)])
                
                machine_schedule[chosen_mid].append((s_val, e_val, jid, oid))
                op_meta[(jid, oid)] = {
                    "assigned_machine": chosen_mid,
                    "est_start": s_val,
                    "est_end": e_val
                }

                # 构造 Transfer 数据
                if prev_machine is not None:
                    # 尝试从 transfer_vars_map 获取精确的转运时间
                    t_key = (jid, oid, prev_machine, chosen_mid)
                    
                    if self.consider_agv_delay and t_key in transfer_vars_map:
                        t_s_var, t_e_var, _ = transfer_vars_map[t_key]
                        actual_transfer_start = solver.Value(t_s_var)
                        actual_transfer_end = solver.Value(t_e_var)
                        # 注意：如果距离为0，solver可能会给任意值，但start必须>=prev_end
                        # 这里的 ready_time 指的是“工件什么时候可以开始运” (prev_end)
                        # 但实际运输是在 actual_transfer_start 开始
                        transfers.append({
                            "job_id": jid, "op_id": oid,
                            "from_machine": prev_machine, "to_machine": chosen_mid,
                            "ready_time": prev_end_val, # 工件就绪时间
                            "start_transfer": actual_transfer_start, # AGV提取时间
                            "end_transfer": actual_transfer_end # 到达时间
                        })
                    else:
                        # 兼容旧逻辑
                        transfers.append({
                            "job_id": jid, "op_id": oid,
                            "from_machine": prev_machine, "to_machine": chosen_mid,
                            "ready_time": prev_end_val,
                            "start_transfer": prev_end_val,
                            "end_transfer": s_val # 此时就是无缝衔接
                        })
                else:
                    # 第一道工序
                    transfers.append({
                        "job_id": jid, "op_id": oid,
                        "from_machine": chosen_mid, "to_machine": chosen_mid,
                        "ready_time": 0.0,
                        "start_transfer": 0.0,
                        "end_transfer": 0.0
                    })

                prev_machine = chosen_mid
                prev_end_val = e_val

        for mid in machine_schedule:
            machine_schedule[mid].sort(key=lambda x: x[0])

        return JobSolverResult(
            machine_schedule,
            op_meta,
            transfers,
            {
                "makespan": solver.Value(makespan),
                "rule": "ORTOOLS_OPTIMAL_FIXED",
                "n_agvs": self.n_agvs
            }
        )