'''
@Project ：SkyEngine 
@File    ：offline_solver.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 21:38
'''

from typing import List, Callable
import random
from sky_executor.grid_factory.factory.grid_factory_env.Utils.structure import Job, Machine, Operation, JobSolverResult


# greedy priority scheduler (job-centric)
def priority_greedy(jobs: List[Job],
                    machines: List[Machine],
                    priority_rule: str = "SPT",
                    transfer_time_estimator: Callable[[int, int], float] = lambda a, b: 0.0):
    # machine available times
    m_avail = {m.id: 0.0 for m in machines}
    op_meta = {}
    machine_schedule = {m.id: [] for m in machines}
    transfer_requests = []
    # flatten ops with job precedence maintained: we will use a ready-list approach
    # maintain next_op_index per job
    next_idx = {job.job_id: 0 for job in jobs}
    # maintain a global time for releasing new ops, but we'll use an event-driven loop until all done
    remaining = sum(len(job.ops) for job in jobs)
    # ready list contains (job_id, op) whose predecessors are done
    ready = []
    # initially push first ops
    for job in jobs:
        if job.ops:
            ready.append(job.ops[0])

    def priority_key(op: Operation):
        if priority_rule == "SPT":
            return op.proc_time
        elif priority_rule == "EDD":
            return op.due if op.due is not None else float('inf')
        elif priority_rule == "FIFO":
            return op.release
        else:
            return op.proc_time

    while remaining > 0:
        if not ready:
            # no ready ops (shouldn't normally happen unless releases), break to avoid infinite loop
            break
        # select next op by priority
        ready.sort(key=priority_key)
        op = ready.pop(0)
        j = op.job_id
        # compute earliest ready due to predecessor completion if any
        prev_finish = 0.0
        if op.op_id > 0:
            prev_meta = op_meta[(j, op.op_id - 1)]
            prev_finish = prev_meta['est_end']
            prev_machine = prev_meta['assigned_machine']
        else:
            prev_finish = op.release
            prev_machine = None

        # pick machine among options minimizing finish time (consider m_avail + transfer estimator if prev_machine != candidate)
        best = None
        best_start = None
        best_finish = None
        for m in op.machine_options:
            transfer = 0.0
            if prev_machine is not None and prev_machine != m:
                transfer = transfer_time_estimator(prev_machine, m)
            cand_start = max(m_avail[m], prev_finish + transfer, op.release)
            cand_finish = cand_start + op.proc_time
            if best_finish is None or cand_finish < best_finish:
                best_finish = cand_finish;
                best_start = cand_start;
                best = m

        # assign
        machine_schedule[best].append((best_start, best_finish, j, op.op_id))
        m_avail[best] = best_finish
        # op metadata
        op_meta[(j, op.op_id)] = {
            'assigned_machine': best,
            'est_start': best_start,
            'est_end': best_finish,
            'prev_machine': prev_machine,
            'needs_transfer': (prev_machine is not None and prev_machine != best)
        }
        if op_meta[(j, op.op_id)]['needs_transfer']:
            transfer_requests.append({
                'job_id': j, 'op_id': op.op_id,
                'from_machine': prev_machine, 'to_machine': best,
                'ready_time': prev_finish
            })

        # push successor op if exists
        if op.op_id + 1 < len(jobs[j].ops):
            next_op = jobs[j].ops[op.op_id + 1]
            ready.append(next_op)

        remaining -= 1

    # compute stats
    makespan = max((t[1] for tasks in machine_schedule.values() for t in tasks), default=0.0)
    machine_util = {}
    for mid, tasks in machine_schedule.items():
        busy = sum(e - s for s, e, _, _ in tasks)
        machine_util[mid] = busy / (makespan if makespan > 0 else 1.0)

    stats = {"makespan": makespan, "machine_util": machine_util}
    return JobSolverResult(machine_schedule, op_meta, transfer_requests, stats)


# local search: simple swap on machine sequences to reduce makespan
def local_search_improve(result: JobSolverResult, jobs: List[Job], machines: List[Machine], iters=200):
    # build sequence per machine
    seqs = {m.id: sorted(result.machine_schedule[m.id], key=lambda x: x[0]) for m in machines}

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
        if i == j: continue
        # swap tasks i and j
        tasks[i], tasks[j] = tasks[j], tasks[i]
        # recompute start/end greedily on this machine only, naive; for safety recompute all machines greedy by scanning seqs
        recomputed = {}
        for m, tlist in seqs.items():
            cur = 0.0
            recomputed[m] = []
            for (s, e, jid, oid) in tlist:
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
    result.stats['makespan'] = best_mk
    return result


