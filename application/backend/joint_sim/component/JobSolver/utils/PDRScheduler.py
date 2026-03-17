"""
@Project ：SkyEngine
@File    ：PDRScheduler.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/26 21:03
"""

"""
@Class   : PDRScheduler
@Desc    : A unified heuristic solver supporting multiple priority dispatching rules.
@Rules   : SPT, LPT, EDD, FIFO, MWKR, MOPNR, FDD/MWKR
"""

from enum import Enum
from joint_sim.utils.structure import (
    Machine,
    Job,
    JobSolverResult,
    DispatchRule,
)
from typing import List, Callable


class PDRScheduler:
    def __init__(self, jobs: List[Job], machines: List[Machine]):
        self.jobs = jobs
        self.machines = machines
        self.job_map = {j.job_id: j for j in jobs}
        self.remaining_work = {}
        self.remaining_ops = {}

    def _reset_state(self):
        self.remaining_work = {
            j.job_id: sum(o.proc_time for o in j.ops) for j in self.jobs
        }
        self.remaining_ops = {j.job_id: len(j.ops) for j in self.jobs}

    def solve(
        self,
        rule: str = DispatchRule.MWKR.value,
        transfer_estimator: Callable[[int, int], float] = lambda a, b: 0.0,
    ) -> JobSolverResult:
        self._reset_state()
        m_avail = {m.id: 0.0 for m in self.machines}
        machine_schedule = {m.id: [] for m in self.machines}
        op_meta = {}
        transfer_requests = []

        ready_ops = []
        for job in self.jobs:
            if job.ops:
                ready_ops.append(job.ops[0])

        total_ops = sum(len(j.ops) for j in self.jobs)
        ops_processed = 0

        while ops_processed < total_ops:
            if not ready_ops:
                break

            # 根据规则排序 Ready List
            ready_ops.sort(key=lambda op: self._calculate_priority(op, rule, op_meta))

            best_op = ready_ops.pop(0)
            jid = best_op.job_id

            # 前序约束
            prev_finish = 0.0
            prev_machine = None
            if best_op.op_id > 0:
                prev_info = op_meta[(jid, best_op.op_id - 1)]
                prev_finish = prev_info["est_end"]
                prev_machine = prev_info["assigned_machine"]
            else:
                prev_finish = best_op.release

            # 机器选择 (Greedy)
            best_m, best_s, best_e = None, None, float("inf")
            candidates = (
                best_op.machine_options
                if best_op.machine_options
                else [m.id for m in self.machines]
            )

            for mid in candidates:
                start = max(m_avail[mid], prev_finish, best_op.release)
                end = start + best_op.proc_time
                if end < best_e:
                    best_e = end
                    best_s = start
                    best_m = mid

            # 更新状态
            machine_schedule[best_m].append((best_s, best_e, jid, best_op.op_id))
            m_avail[best_m] = best_e
            op_meta[(jid, best_op.op_id)] = {
                "assigned_machine": best_m,
                "est_end": best_e,
                "prev_machine": prev_machine,
            }

            if prev_machine is not None and prev_machine != best_m:
                transfer_requests.append(
                    {
                        "job_id": jid,
                        "op_id": best_op.op_id,
                        "from": prev_machine,
                        "to": best_m,
                        "time": prev_finish,
                    }
                )

            self.remaining_work[jid] -= best_op.proc_time
            self.remaining_ops[jid] -= 1
            ops_processed += 1

            if best_op.op_id + 1 < len(self.jobs[jid].ops):
                ready_ops.append(self.jobs[jid].ops[best_op.op_id + 1])

        makespan = max(
            (t[1] for tasks in machine_schedule.values() for t in tasks), default=0.0
        )
        return JobSolverResult(
            machine_schedule,
            op_meta,
            transfer_requests,
            {"makespan": makespan, "rule": rule},
        )

    def _calculate_priority(self, op, rule, op_meta):
        jid = op.job_id
        # 若没有 due_date 属性，默认为无穷大
        due = getattr(self.job_map[jid], "due", 9999) or 9999

        # 估算当前时刻 t (用于 FDD)
        t_now = op.release
        if op.op_id > 0:
            t_now = op_meta[(jid, op.op_id - 1)]["est_end"]

        if rule == "SPT":
            return op.proc_time
        if rule == "LPT":
            return -op.proc_time
        if rule == "EDD":
            return due
        if rule == "FIFO":
            return op.release
        if rule == "MWKR":
            return -self.remaining_work[jid]
        if rule == "MOPNR":
            return -self.remaining_ops[jid]
        if rule == "FDD/MWKR":
            # (交期 - 当前时间) / 剩余工作量
            rem_work = (
                self.remaining_work[jid] if self.remaining_work[jid] > 1e-6 else 1e-6
            )
            return (due - t_now) / rem_work
        return op.release


if __name__ == "__main__":
    # 假设已经有了 jobs 和 machines 列表
    scheduler = PDRScheduler(jobs, machines)

    # 1. 运行 FDD/MWKR
    result_fdd = scheduler.solve(rule="FDD/MWKR")
    print(f"FDD/MWKR Makespan: {result_fdd.stats['makespan']}")

    # 2. 运行 MOPNR
    result_mopnr = scheduler.solve(rule="MOPNR")
    print(f"MOPNR Makespan: {result_mopnr.stats['makespan']}")

    # 3. 运行经典 SPT
    result_spt = scheduler.solve(rule="SPT")
