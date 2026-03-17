'''
@Project ：SkyEngine 
@File    ：__init__.py.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 21:37
'''

# | 功能模块 | 说明                                    |
# | ---- | ------------------------------------- |
# | 输入   | 一组 AGV 路由请求：`[(start, goal), ...]`    |
# | 后端   | 使用 Pogema 环境进行路径规划与仿真                 |
# | 输出   | 每个 AGV 的路径轨迹、执行时间、冲突统计                |
# | 指标   | 平均路径长度、总路径长度、平均延迟、碰撞率等                |
# | 可扩展性 | 支持切换策略（A*、ORCA、Pogema 内部 policy、RL 等） |

# | 来源                  | 字段                            | 类型                     | 含义                    |
# | ------------------- | ----------------------------- | ---------------------- | --------------------- |
# | `obs`               | `'agent_observation'`         | List[dict or np.array] | Pogema 各 AGV 的局部视野或状态 |
# | `obs`               | `'global_time'`               | float                  | 当前全局时间                |
# | `obs`               | `'positions'`                 | List[Tuple[int, int]]  | 各 AGV 当前坐标（可选）        |
# | `transfer_requests` | `job_id`                      | int                    | 任务归属                  |
# | `transfer_requests` | `from_machine` / `to_machine` | int                    | 起止机器编号（映射为坐标）         |
# | `transfer_requests` | `ready_time`                  | float                  | 任务可开始搬运的时间            |


# RouteSolver/__init__.py
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
