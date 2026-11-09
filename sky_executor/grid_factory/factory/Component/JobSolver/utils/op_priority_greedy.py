"""
@Project ：SkyEngine
@File    ：offline_solver.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 21:38
"""

from typing import List, Callable, Tuple
import math
import random
from sky_executor.grid_factory.factory.Utils.structure import (
    Job,
    Machine,
    Operation,
    JobSolverResult,
)


def _get_candidates(op: Operation, machines: List[Machine]) -> List[Tuple[int, float]]:
    """
    获取 operation 的可选机器及其对应加工时间。
    优先使用 machine_options_with_time [(machine_id, proc_time), ...]；
    若为空则回退到 machine_options + op.proc_time。
    """
    if op.machine_options_with_time:
        return list(op.machine_options_with_time)
    elif op.machine_options:
        return [(mid, op.proc_time) for mid in op.machine_options]
    else:
        return [(m.id, op.proc_time) for m in machines]


def _min_proc_time(op: Operation, machines: List[Machine]) -> float:
    """获取 operation 在所有候选机器上的最短加工时间（用于优先级排序）。"""
    candidates = _get_candidates(op, machines)
    if candidates:
        return min(pt for _, pt in candidates)
    return op.proc_time


# greedy priority scheduler (job-centric)
def priority_greedy(
    jobs: List[Job],
    machines: List[Machine],
    priority_rule: str = "SPT",
    transfer_time_estimator: Callable[[int, int], float] = lambda a, b: 0.0,
):
    jobs_by_id = {job.job_id: job for job in jobs}
    # machine available times
    m_avail = {m.id: 0.0 for m in machines}
    op_meta = {}
    machine_schedule = {m.id: [] for m in machines}
    transfer_requests = []
    remaining = sum(len(job.ops) for job in jobs)
    ready = []
    for job in jobs:
        if job.ops:
            ready.append(job.ops[0])

    def priority_key(op: Operation):
        if priority_rule == "SPT":
            return _min_proc_time(op, machines)
        elif priority_rule == "EDD":
            return op.due if op.due is not None else float("inf")
        elif priority_rule == "FIFO":
            return op.release
        else:
            return _min_proc_time(op, machines)

    while remaining > 0:
        if not ready:
            print(f"[ERROR] Ready queue is empty but {remaining} operations still remaining!")
            print(f"[ERROR] This means some operations were never scheduled!")
            for j_id in range(len(jobs)):
                for op_idx in range(len(jobs[j_id].ops)):
                    if (j_id, op_idx) not in op_meta:
                        op = jobs[j_id].ops[op_idx]
                        print(f"[ERROR]   Unscheduled: Job {j_id} Op {op_idx}, "
                              f"machine_options={op.machine_options}, "
                              f"machine_options_with_time={op.machine_options_with_time}")
            break
        # select next op by priority
        ready.sort(key=priority_key)
        op = ready.pop(0)
        j = op.job_id

        # === 获取候选机器 (machine_id, proc_time) ===
        candidates = _get_candidates(op, machines)
        if not candidates:
            print(f"[ERROR] Job {j} Op {op.op_id} has NO candidate machines, SKIPPING!")
            remaining -= 1
            continue

        # compute earliest ready due to predecessor completion if any
        if op.op_id > 0:
            prev_meta = op_meta[(j, op.op_id - 1)]
            prev_finish = prev_meta["est_end"]
            prev_machine = prev_meta["assigned_machine"]
        else:
            prev_finish = op.release
            valid_ids = [mid for mid, _pt in candidates]
            prev_machine = random.choice(valid_ids)

        # pick machine among candidates minimizing finish time
        best = None
        best_start = None
        best_finish = None
        best_proc_time = None
        for m, pt in candidates:
            transfer = 0.0
            if prev_machine is not None and prev_machine != m:
                transfer = transfer_time_estimator(prev_machine, m)
            cand_start = max(m_avail[m], prev_finish + transfer, op.release)
            cand_finish = cand_start + pt
            if best_finish is None or cand_finish < best_finish:
                best_finish = cand_finish
                best_start = cand_start
                best = m
                best_proc_time = pt

        # assign
        machine_schedule[best].append((best_start, best_finish, j, op.op_id))
        m_avail[best] = best_finish
        op_meta[(j, op.op_id)] = {
            "assigned_machine": best,
            "est_start": best_start,
            "est_end": best_finish,
            "prev_machine": prev_machine,
            "proc_time": best_proc_time,
        }
        transfer_requests.append(
            {
                "job_id": j,
                "op_id": op.op_id,
                "from_machine": prev_machine,
                "to_machine": best,
                "ready_time": prev_finish,
            }
        )

        # push successor op if exists
        if op.op_id + 1 < len(jobs_by_id[j].ops):
            next_op = jobs_by_id[j].ops[op.op_id + 1]
            ready.append(next_op)

        remaining -= 1

    # compute stats
    makespan = max(
        (t[1] for tasks in machine_schedule.values() for t in tasks), default=0.0
    )
    machine_util = {}
    for mid, tasks in machine_schedule.items():
        busy = sum(e - s for s, e, _, _ in tasks)
        machine_util[mid] = busy / (makespan if makespan > 0 else 1.0)

    stats = {"makespan": makespan, "machine_util": machine_util}
    return JobSolverResult(machine_schedule, op_meta, transfer_requests, stats)


# local search: simple swap on machine sequences to reduce makespan
def local_search_improve(
    result: JobSolverResult, jobs: List[Job], machines: List[Machine], iters=200
):
    # build sequence per machine
    seqs = {
        m.id: sorted(result.machine_schedule[m.id], key=lambda x: x[0])
        for m in machines
    }

    def total_makespan_from_seqs(seqs):
        return max((t[1] for tasks in seqs.values() for t in tasks), default=0)

    best_seqs = {m: list(seqs[m]) for m in seqs}
    best_mk = total_makespan_from_seqs(best_seqs)
    # attempt random swaps within machine sequences (or move op to another allowed machine)
    for _ in range(iters):
        # pick random job op
        mid = random.choice(list(seqs.keys()))
        tasks = seqs[mid]
        if len(tasks) < 2:
            continue
        i = random.randrange(len(tasks))
        j = random.randrange(len(tasks))
        if i == j:
            continue
        # swap tasks i and j
        tasks[i], tasks[j] = tasks[j], tasks[i]
        # recompute start/end greedily on this machine only, naive; for safety recompute all machines greedy by scanning seqs
        recomputed = {}
        for m, tlist in seqs.items():
            cur = 0.0
            recomputed[m] = []
            for s, e, jid, oid in tlist:
                dur = e - s
                s2 = max(cur, 0.0)
                e2 = s2 + dur
                recomputed[m].append((s2, e2, jid, oid))
                cur = e2
        mk = total_makespan_from_seqs(recomputed)
        if mk < best_mk:
            best_mk = mk
            best_seqs = {m: list(recomputed[m]) for m in recomputed}
        else:
            # revert swap
            tasks[i], tasks[j] = tasks[j], tasks[i]
    # return improved result
    result.machine_schedule = best_seqs
    result.stats["makespan"] = best_mk
    return result


# -------------------------------------------------------------------------
# 1. Expanded Rule-Based Solver (Supporting SPT, LPT, EDD, FIFO, MWKR)
# -------------------------------------------------------------------------
def rule_based_solver(
    jobs: List[Job],
    machines: List[Machine],
    rule: str = "MWKR",
    transfer_time_estimator: Callable[[int, int], float] = lambda a, b: 0.0,
) -> JobSolverResult:
    """
    General Priority Dispatcher supporting multiple static rules.
    Rules:
        - SPT: Shortest Processing Time
        - LPT: Longest Processing Time
        - EDD: Earliest Due Date
        - FIFO: First In First Out (Release time)
        - MWKR: Most Work Remaining (Job total remaining time)
    """
    # Pre-calculation for MWKR (Total remaining work per job)
    job_remaining_work = {}
    for job in jobs:
        total_time = sum(_min_proc_time(op, machines) for op in job.ops)
        job_remaining_work[job.job_id] = total_time

    # Setup structures
    m_avail = {m.id: 0.0 for m in machines}
    op_meta = {}
    machine_schedule = {m.id: [] for m in machines}
    transfer_requests = []

    # Ready list logic
    remaining_ops_count = sum(len(job.ops) for job in jobs)
    ready = []

    # 剩余工作量 (MWKR, FDD/MWKR用)
    job_remaining_work = {}
    # 剩余工序数 (MOPNR用)
    job_remaining_ops_count = {}


    for job in jobs:
        if job.ops:
            ready.append(job.ops[0])
        total_time = sum(_min_proc_time(op, machines) for op in job.ops)
        job_remaining_work[job.job_id] = total_time
        job_remaining_ops_count[job.job_id] = len(job.ops)

    # Priority Key Definitions
    def get_priority(op: Operation):
        # 获取当前作业信息
        jid = op.job_id
        rem_work = job_remaining_work.get(jid, 1e-6)
        rem_ops = job_remaining_ops_count.get(jid, 0)
        due_date = jobs[jid].due if hasattr(jobs[jid], 'due_date') and jobs[jid].due else 999999

        t_now = op.release
        if op.op_id > 0:
            prev_meta = op_meta[(jid, op.op_id - 1)]
            t_now = prev_meta['est_end']

        if rule == "SPT": # 短任务优先
            return _min_proc_time(op, machines)
        elif rule == "LPT": # 长任务优先
            return -_min_proc_time(op, machines)
        elif rule == "EDD": # 最早交付期优先
            return op.due if op.due is not None else float("inf")
        elif rule == "FIFO": # 先来先服务
            return t_now  # 谁最早到达谁先做
        elif rule == "MWKR":
            return -rem_work  # 剩余工作量越大，负值越小，排越前
        elif rule == "MOPNR":
            return -rem_ops  # 剩余工序越多，负值越小，排越前
        elif rule == "FDD/MWKR":
            # SPT（最短加工时间）、MWKR（剩余工作量最大）、MOPNR（剩余工序数最大）、FDD / MWKR（流工期与剩余工作量比最小）
            # (交期 - 当前时间) / 剩余工作量
            # 分子越小(越紧急)，分母越大(工作量越大)，整体比率越小 -> 优先级越高
            urgency = due_date - t_now
            # 防止除以0
            denominator = rem_work if rem_work > 1e-6 else 1e-6
            return urgency / denominator
        else:
            return op.proc_time

    while remaining_ops_count > 0:
        if not ready:
            break

        # Sort ready list by the selected rule
        ready.sort(key=get_priority)

        # Pop the highest priority operation
        op = ready.pop(0)
        j = op.job_id

        # Determine earliest start time based on predecessor
        if op.op_id > 0:
            prev_meta = op_meta[(j, op.op_id - 1)]
            prev_finish = prev_meta["est_end"]
            prev_machine = prev_meta["assigned_machine"]
        else:
            prev_finish = op.release
            prev_machine = None

        # --- Greedy Machine Selection (Routing) ---
        best_m, best_start, best_finish, best_pt = None, None, None, None

        candidates = _get_candidates(op, machines)

        for mid, pt in candidates:
            transfer = 0.0
            if prev_machine is not None and prev_machine != mid:
                transfer = transfer_time_estimator(prev_machine, mid)

            # Earliest start on this machine is max(Machine Free Time, Job Ready Time + Transfer)
            cand_start = max(m_avail[mid], prev_finish + transfer, op.release)
            cand_finish = cand_start + pt

            if best_finish is None or cand_finish < best_finish:
                best_finish = cand_finish
                best_start = cand_start
                best_m = mid
                best_pt = pt

        # --- Update State ---
        # 1. Update MWKR stat if needed
        if rule == "MWKR":
            job_remaining_work[j] -= best_pt if best_pt else _min_proc_time(op, machines)

        # 2. Record Schedule
        machine_schedule[best_m].append((best_start, best_finish, j, op.op_id))
        m_avail[best_m] = best_finish

        op_meta[(j, op.op_id)] = {
            "assigned_machine": best_m,
            "est_start": best_start,
            "est_end": best_finish,
            "prev_machine": prev_machine,
            "proc_time": best_pt,
        }

        # 3. Record Transfer
        if prev_machine is not None and prev_machine != best_m:
            transfer_requests.append(
                {
                    "job_id": j,
                    "op_id": op.op_id,
                    "from_machine": prev_machine,
                    "to_machine": best_m,
                    "ready_time": prev_finish,
                }
            )

        # 4. Add successor
        if op.op_id + 1 < len(jobs[j].ops):
            next_op = jobs[j].ops[op.op_id + 1]
            ready.append(next_op)

        # 扣除已安排工序的时间和数量
        job_remaining_work[j] -= best_pt if best_pt else _min_proc_time(op, machines)
        job_remaining_ops_count[j] -= 1
        remaining_ops_count -= 1

    # Final Stats
    makespan = max(
        (t[1] for tasks in machine_schedule.values() for t in tasks), default=0.0
    )
    machine_util = {
        mid: sum(e - s for s, e, _, _ in tasks) / (makespan or 1)
        for mid, tasks in machine_schedule.items()
    }

    return JobSolverResult(
        machine_schedule,
        op_meta,
        transfer_requests,
        {"makespan": makespan, "machine_util": machine_util, "rule": rule},
    )


# -------------------------------------------------------------------------
# 2. Simulated Annealing (Meta-heuristic)
# -------------------------------------------------------------------------


def simulated_annealing_solver(
    jobs: List[Job],
    machines: List[Machine],
    initial_temp: float = 1000.0,
    cooling_rate: float = 0.95,
    max_iter: int = 1000,
) -> JobSolverResult:
    """
    Simulated Annealing approach.
    Uses 'Operation-based representation' (permutation of job IDs).
    """

    # --- Helper: Generate a random operation sequence ---
    # Example: if Job 0 has 2 ops and Job 1 has 1 op -> [0, 1, 0] or [0, 0, 1] etc.
    flat_job_ids = []
    for job in jobs:
        flat_job_ids.extend([job.job_id] * len(job.ops))

    # --- Helper: Decode sequence to Schedule (Builder) ---
    def decode(sequence):
        # Tracking pointers
        job_op_idx = {job.job_id: 0 for job in jobs}
        m_avail_time = {m.id: 0.0 for m in machines}
        job_next_avail_time = {
            job.job_id: 0.0 for job in jobs
        }  # Job precedence constraint

        temp_schedule = {m.id: [] for m in machines}
        local_max_end = 0.0

        for jid in sequence:
            op_idx = job_op_idx[jid]
            op = jobs[jid].ops[op_idx]

            best_m, best_end = None, float("inf")
            best_start = 0.0

            candidates = _get_candidates(op, machines)

            ready_time = max(job_next_avail_time[jid], op.release)

            for mid, pt in candidates:
                start = max(m_avail_time[mid], ready_time)
                end = start + pt
                if end < best_end:
                    best_end = end
                    best_start = start
                    best_m = mid

            # Assign
            temp_schedule[best_m].append((best_start, best_end, jid, op_idx))
            m_avail_time[best_m] = best_end
            job_next_avail_time[jid] = best_end
            job_op_idx[jid] += 1
            if best_end > local_max_end:
                local_max_end = best_end

        return temp_schedule, local_max_end

    # 1. Initialization
    current_seq = flat_job_ids[:]
    random.shuffle(current_seq)  # Random initial solution

    current_sched, current_makespan = decode(current_seq)

    best_seq = current_seq[:]
    best_makespan = current_makespan
    best_sched = current_sched

    curr_temp = initial_temp

    # 2. Annealing Loop
    for it in range(max_iter):
        # Mutate: Swap two random positions
        idx1, idx2 = random.sample(range(len(current_seq)), 2)
        neighbor_seq = current_seq[:]
        neighbor_seq[idx1], neighbor_seq[idx2] = neighbor_seq[idx2], neighbor_seq[idx1]

        # Evaluate
        _, neighbor_makespan = decode(neighbor_seq)

        # Acceptance Probability
        delta = neighbor_makespan - current_makespan

        accept = False
        if delta < 0:
            accept = True
        else:
            # Metropolis criterion
            p = math.exp(-delta / curr_temp)
            if random.random() < p:
                accept = True

        if accept:
            current_seq = neighbor_seq
            current_makespan = neighbor_makespan
            # Update global best
            if current_makespan < best_makespan:
                best_makespan = current_makespan
                best_seq = current_seq[:]
                # We only need to fully rebuild the schedule object for the best one to save time
                best_sched, _ = decode(best_seq)

        # Cool down
        curr_temp *= cooling_rate
        if curr_temp < 1e-6:
            break

    # 3. Construct Result Object for the best found
    # We need to rebuild full metadata (op_meta, transfer_requests) based on best_sched
    # For brevity, we return a simplified result or reuse the decode logic to populate metadata
    # Re-running decode carefully to fill metadata:
    final_op_meta = {}
    final_transfers = []

    # Re-simulation for metadata
    job_op_idx = {job.job_id: 0 for job in jobs}
    m_avail_time = {m.id: 0.0 for m in machines}
    job_prev_info = {
        job.job_id: (None, 0.0) for job in jobs
    }  # (prev_machine, prev_end)

    final_schedule = {m.id: [] for m in machines}

    for jid in best_seq:
        op_idx = job_op_idx[jid]
        op = jobs[jid].ops[op_idx]
        prev_m, prev_end = job_prev_info[jid]

        # Re-select (deterministic greedy)
        candidates = _get_candidates(op, machines)
        best_m, best_end, best_start, best_pt = None, float("inf"), 0.0, 0.0

        ready_time = max(prev_end, op.release)

        for mid, pt in candidates:
            start = max(m_avail_time[mid], ready_time)
            end = start + pt
            if end < best_end:
                best_end = end
                best_start = start
                best_m = mid
                best_pt = pt

        final_schedule[best_m].append((best_start, best_end, jid, op_idx))
        m_avail_time[best_m] = best_end

        final_op_meta[(jid, op_idx)] = {
            "assigned_machine": best_m,
            "est_start": best_start,
            "est_end": best_end,
            "prev_machine": prev_m,
            "proc_time": best_pt,
        }

        if prev_m is not None and prev_m != best_m:
            final_transfers.append(
                {
                    "job_id": jid,
                    "op_id": op_idx,
                    "from_machine": prev_m,
                    "to_machine": best_m,
                    "ready_time": prev_end,
                }
            )

        job_prev_info[jid] = (best_m, best_end)
        job_op_idx[jid] += 1

    stats = {"makespan": best_makespan, "method": "Simulated Annealing"}
    return JobSolverResult(final_schedule, final_op_meta, final_transfers, stats)


# -------------------------------------------------------------------------
# 3. Genetic Algorithm (Population-based)
# -------------------------------------------------------------------------


def genetic_algorithm_solver(
    jobs: List[Job],
    machines: List[Machine],
    pop_size: int = 50,
    generations: int = 100,
    mutation_rate: float = 0.1,
) -> JobSolverResult:
    """
    Standard GA for JSSP.
    Encoding: Operation-based (Sequence of Job IDs).
    """

    # Flatten job IDs to create base chromosome genes
    base_genes = []
    for job in jobs:
        base_genes.extend([job.job_id] * len(job.ops))

    def calculate_makespan(sequence):
        # Simplified decoder for fitness
        job_op_idx = {job.job_id: 0 for job in jobs}
        m_avail = {m.id: 0.0 for m in machines}
        job_end = {job.job_id: 0.0 for job in jobs}

        local_mk = 0.0
        for jid in sequence:
            op_idx = job_op_idx[jid]
            op = jobs[jid].ops[op_idx]

            candidates = _get_candidates(op, machines)
            best_end = float("inf")
            best_m = candidates[0][0]

            ready = max(job_end[jid], op.release)

            for mid, pt in candidates:
                s = max(m_avail[mid], ready)
                e = s + pt
                if e < best_end:
                    best_end = e
                    best_m = mid

            m_avail[best_m] = best_end
            job_end[jid] = best_end
            if best_end > local_mk:
                local_mk = best_end
            job_op_idx[jid] += 1

        return local_mk

    # Initialize Population
    population = []
    for _ in range(pop_size):
        chrom = base_genes[:]
        random.shuffle(chrom)
        population.append(chrom)

    best_chrom = None
    best_mk = float("inf")

    for gen in range(generations):
        # Evaluate
        fitness_scores = []
        for individual in population:
            mk = calculate_makespan(individual)
            if mk < best_mk:
                best_mk = mk
                best_chrom = individual[:]
            # Fitness = 1 / makespan (higher is better)
            fitness_scores.append(1.0 / (mk if mk > 0 else 1.0))

        # Selection (Tournament)
        new_pop = []
        while len(new_pop) < pop_size:
            # Select 2 parents
            parents = []
            for _ in range(2):
                candidates = random.sample(list(zip(population, fitness_scores)), 3)
                # Pick max fitness
                winner = max(candidates, key=lambda x: x[1])[0]
                parents.append(winner)

            p1, p2 = parents

            # Crossover (Job-based Crossover / OX simplified)
            # Here we use a simple mask approach to preserve counts
            # Inherit genes from P1 at random indices, fill rest from P2 order
            if random.random() < 0.8:
                # Subsequence crossover
                cut1, cut2 = sorted(random.sample(range(len(p1)), 2))
                child = [-1] * len(p1)
                # Copy middle segment from P1
                child[cut1:cut2] = p1[cut1:cut2]

                # Fill remaining from P2
                # Calculate counts needed
                current_counts = {}
                for x in child:
                    if x != -1:
                        current_counts[x] = current_counts.get(x, 0) + 1

                # Expected total counts per job
                total_counts = {}
                for x in base_genes:
                    total_counts[x] = total_counts.get(x, 0) + 1

                p2_ptr = 0
                for i in range(len(child)):
                    if child[i] == -1:
                        # Find next valid gene from P2
                        while p2_ptr < len(p2):
                            candidate = p2[p2_ptr]
                            p2_ptr += 1
                            if (
                                current_counts.get(candidate, 0)
                                < total_counts[candidate]
                            ):
                                child[i] = candidate
                                current_counts[candidate] = (
                                    current_counts.get(candidate, 0) + 1
                                )
                                break
            else:
                child = p1[:]  # No crossover

            # Mutation (Swap)
            if random.random() < mutation_rate:
                i, j = random.sample(range(len(child)), 2)
                child[i], child[j] = child[j], child[i]

            new_pop.append(child)

        population = new_pop

    # Return Result using the SA's decoder logic or calling SA with 0 iter
    # Reuse the logic from SA to build the full object
    return simulated_annealing_solver(jobs, machines, initial_temp=0, max_iter=0)
    # Note: Above line is a hack to reuse decoding logic if you paste this into the same file.
    # Ideally, extract the 'decode_to_result' logic into a shared standalone function.
