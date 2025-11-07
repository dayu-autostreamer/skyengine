'''
@Project ：SkyEngine 
@File    ：or_test.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 21:06
'''

from ortools.sat.python import cp_model
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# 这里探索基本的求解器对job相关问题的求解。

jobs_data = [
    [(1, 1), (2, 3), (3, 6), (4, 7), (5, 3), (0, 6)],
    [(2, 8), (3, 5), (4, 10), (5, 10), (0, 10), (1, 4)],
    [(3, 5), (4, 4), (5, 8), (0, 9), (1, 1), (2, 7)],
    [(4, 5), (5, 5), (0, 5), (1, 3), (2, 8), (3, 9)],
    [(5, 9), (0, 3), (1, 5), (2, 4), (3, 3), (4, 1)],
    [(0, 3), (1, 3), (2, 9), (3, 10), (4, 4), (5, 1)],
]

def solve_jobshop(jobs_data):
    num_jobs = len(jobs_data)
    num_machines = len(jobs_data[0])

    model = cp_model.CpModel()

    # 所有操作编号化
    all_tasks = {}
    machine_to_intervals = [[] for _ in range(num_machines)]
    horizon = sum(task[1] for job in jobs_data for task in job)

    # 变量定义
    for j, job in enumerate(jobs_data):
        for t, (m, p) in enumerate(job):
            suffix = f'_{j}_{t}'
            start = model.NewIntVar(0, horizon, 'start' + suffix)
            end = model.NewIntVar(0, horizon, 'end' + suffix)
            interval = model.NewIntervalVar(start, p, end, 'interval' + suffix)
            all_tasks[(j, t)] = (start, end, interval, m)
            machine_to_intervals[m].append(interval)

    # 每台机器不可重叠
    for m in range(num_machines):
        model.AddNoOverlap(machine_to_intervals[m])

    # 每个 job 内部顺序约束
    for j, job in enumerate(jobs_data):
        for t in range(len(job) - 1):
            model.Add(all_tasks[(j, t + 1)][0] >= all_tasks[(j, t)][1])

    # 定义目标 makespan
    makespan = model.NewIntVar(0, horizon, 'makespan')
    model.AddMaxEquality(
        makespan,
        [all_tasks[(j, len(job) - 1)][1] for j, job in enumerate(jobs_data)]
    )
    model.Minimize(makespan)

    # 求解
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    solver.parameters.num_search_workers = 8
    result_status = solver.Solve(model)

    if result_status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f'Makespan = {solver.Value(makespan)}')
        print('-' * 40)
        for j, job in enumerate(jobs_data):
            print(f'Job {j}:')
            for t, (m, p) in enumerate(job):
                s = solver.Value(all_tasks[(j, t)][0])
                e = solver.Value(all_tasks[(j, t)][1])
                print(f'  Task {t} on M{m} [{s}, {e}) dur={p}')
        print('-' * 40)
    else:
        print('No solution found.')


def plot_schedule(jobs_data, solver, all_tasks):
    colors = plt.cm.tab10.colors
    fig, ax = plt.subplots(figsize=(10,4))
    for (j, t), (svar, evar, _, m) in all_tasks.items():
        s = solver.Value(svar)
        e = solver.Value(evar)
        ax.barh(m, e-s, left=s, color=colors[j % len(colors)], edgecolor='black')
        ax.text(s + (e-s)/2, m, f'J{j}', va='center', ha='center', color='white')
    ax.set_xlabel('Time')
    ax.set_ylabel('Machine')
    ax.set_title('Job Shop Schedule (FT06)')
    plt.show()


solve_jobshop(jobs_data)
plot_schedule(jobs_data, solver, all_tasks)


