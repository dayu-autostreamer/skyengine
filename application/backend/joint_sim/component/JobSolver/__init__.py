'''
@Project ：SkyEngine 
@File    ：__init__.py.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 21:38
'''

# job相关求解器的基本实现要求：输入job、machine、优先级规则、AGV转移时间估计函数，返回JobSolverResult，这个结构包含transfer_requests，
#                         交给AGV后续执行，而AGV 返回具体 transfer_complete_time 后，主仿真可以将 op.est_start 由 est_start 校正为 max(m_avail, transfer_complete_time, release) 并推进仿真（或重新调用 solver 做后续衔接）。
# def priority_greedy(jobs: List[Job],
#                     machines: List[Machine],
#                     priority_rule: str = "SPT",
#                     transfer_time_estimator: Callable[[int, int], float] = lambda a, b: 0.0):
# 上层 RL（或调度器）发出 job 策略 → job-solver 分配 machine/sequence → 生成 transfer_requests → AGV 模块调度 transport → 把 transfer 完成时间反馈 → 仿真推进 / 生成 reward。
#
# 后续实现时，请注意Job求解器基本的规范与要求


# | 类型                        | 示例字段                                                           | 含义              |
# | ------------------------- | -------------------------------------------------------------- | --------------- |
# | `time`                    | `env.current_time`                                             | 当前全局时间步         |
# | `machines`                | `[{"id":0,"status":"idle","occupied_until":t}, ...]`           | 各机器的使用状态        |
# | `jobs`                    | `[{"id":j,"status":"running/ready/finished","ops":[...]},...]` | 每个 Job 的整体状态    |
# | `ready_ops`               | `[(job_id, op_id, op_obj)]`                                    | 已经满足前序依赖、可分配的操作 |
# | `transfers_done`          | `[(job_id, op_id, from_machine, to_machine)]`                  | 已经完成的搬运任务       |
# | `transfer_time_estimator` | 函数句柄                                                           | 可计算机器间传输时间      |


# 这里其实就是从job(operation)中，获得对应的执行逻辑，根据不同的策略生成路由任务即可。

# JobSolver/__init__.py
import pkgutil
import importlib

def recursive_import(package):
    for _, name, ispkg in pkgutil.iter_modules(package.__path__):
        full_name = f"{package.__name__}.{name}"
        module = importlib.import_module(full_name)
        if ispkg:
            recursive_import(module)

def auto_import_solvers():
    import sys
    current_module = sys.modules[__name__]
    recursive_import(current_module)

auto_import_solvers()

