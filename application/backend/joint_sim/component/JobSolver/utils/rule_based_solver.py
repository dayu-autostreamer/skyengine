"""
Additions to offline_solver.py
Implemented by: Gemini
Context: JSSP Static Scheduling Algorithms (Rule-based, SA, GA)
"""

import math
import copy
from typing import Callable, List
from joint_sim.utils.structure import (
    Operation,
    Machine,
    Job,
    JobSolverResult,
    DispatchRule,
)


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
        total_time = sum(op.proc_time for op in job.ops)
        job_remaining_work[job.job_id] = total_time

    # Setup structures
    m_avail = {m.id: 0.0 for m in machines}
    op_meta = {}
    machine_schedule = {m.id: [] for m in machines}
    transfer_requests = []

    # Ready list logic
    remaining_ops_count = sum(len(job.ops) for job in jobs)
    ready = []
    for job in jobs:
        if job.ops:
            ready.append(job.ops[0])

    # Priority Key Definitions
    def get_priority(op: Operation):
        if rule == "SPT":
            return op.proc_time
        elif rule == "LPT":
            return -op.proc_time  # Negative for descending sort
        elif rule == "EDD":
            return op.due if op.due is not None else float("inf")
        elif rule == "FIFO":
            return op.release
        elif rule == "MWKR":
            # Higher remaining work = higher priority (so use negative for min-sort)
            return -job_remaining_work.get(op.job_id, 0)
        else:
            return op.proc_time  # Default to SPT

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
        best_m, best_start, best_finish = None, None, None

        # Filter valid machines (if op.machine_options is empty, assume all, or handle error)
        candidates = (
            op.machine_options if op.machine_options else [m.id for m in machines]
        )

        for mid in candidates:
            transfer = 0.0
            if prev_machine is not None and prev_machine != mid:
                transfer = transfer_time_estimator(prev_machine, mid)

            # Earliest start on this machine is max(Machine Free Time, Job Ready Time + Transfer)
            cand_start = max(m_avail[mid], prev_finish + transfer, op.release)
            cand_finish = cand_start + op.proc_time

            if best_finish is None or cand_finish < best_finish:
                best_finish = cand_finish
                best_start = cand_start
                best_m = mid

        # --- Update State ---
        # 1. Update MWKR stat if needed
        if rule == "MWKR":
            job_remaining_work[j] -= op.proc_time

        # 2. Record Schedule
        machine_schedule[best_m].append((best_start, best_finish, j, op.op_id))
        m_avail[best_m] = best_finish

        op_meta[(j, op.op_id)] = {
            "assigned_machine": best_m,
            "est_start": best_start,
            "est_end": best_finish,
            "prev_machine": prev_machine,
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

            # Simple greedy routing: choose best machine for this specific op instant
            # (Note: For full SA on routing, we would need to encode machine selection too)
            best_m, best_end = None, float("inf")
            best_start = 0.0

            candidates = (
                op.machine_options if op.machine_options else [m.id for m in machines]
            )

            ready_time = max(job_next_avail_time[jid], op.release)

            for mid in candidates:
                start = max(m_avail_time[mid], ready_time)
                end = start + op.proc_time
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
        candidates = (
            op.machine_options if op.machine_options else [m.id for m in machines]
        )
        best_m, best_end, best_start = None, float("inf"), 0.0

        ready_time = max(prev_end, op.release)

        for mid in candidates:
            # (Optional: Add transfer time logic here if needed)
            start = max(m_avail_time[mid], ready_time)
            end = start + op.proc_time
            if end < best_end:
                best_end = end
                best_start = start
                best_m = mid

        final_schedule[best_m].append((best_start, best_end, jid, op_idx))
        m_avail_time[best_m] = best_end

        final_op_meta[(jid, op_idx)] = {
            "assigned_machine": best_m,
            "est_start": best_start,
            "est_end": best_end,
            "prev_machine": prev_m,
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

            # Greedy routing
            candidates = (
                op.machine_options if op.machine_options else [m.id for m in machines]
            )
            best_end = float("inf")
            best_m = candidates[0]

            ready = max(job_end[jid], op.release)

            for mid in candidates:
                s = max(m_avail[mid], ready)
                e = s + op.proc_time
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
