"""
@Project ：SkyEngine
@File    : run.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2026/4/26

SkyEngine 标准运行入口
===========================
标准流程:
    1. 解析 ENV 参数 — 环境规模、调度器、数据集、Monitor 等
    2. 将数据集输入转换为统一运行配置并创建共享会话
    3. 运行 Episode — reset -> step loop -> job_all_done / truncated 终止
    4. 收集 & 保存结果 — JSON 输出到 sky_logs/results/

    # 默认配置快速运行
    python run.py
"""

import json
import os
from pathlib import Path
import yaml

from sky_executor.grid_factory.factory.Utils.pic_drawer import (
    draw_svg_with_machines_and_targets,
)
from sky_executor.grid_factory.factory.Utils.transfer_estimator import (
    TransferTimeEstimator,
)
from sky_executor.grid_factory.factory.grid_factory_env import GridFactoryEnv
from sky_executor.session import SimulationSession, create_env_from_config
from sky_logs.logger import LOGGER


def parse_fjsp_instance(path) -> tuple[list, int]:
    """从 JSON 加载实例，返回 (jobs, num_machines).

    jobs[job_id][task_id] = [(processing_time, machine_id), ...]
    """
    with open(path, "r") as f:
        data = json.load(f)

    num_machines = data["machines"]
    jobs = []
    for job in data["jobs"]:
        job_tasks = []
        for op in job:
            alternatives = [(alt["processing"], alt["machine"]) for alt in op]
            job_tasks.append(alternatives)
        jobs.append(job_tasks)

    return {"jobs": jobs, "machine_number": num_machines}


def parse_mapf_instance(path, instance_name):
    # 1.获得配置文件中的所有地图名称
    with open(path, "r") as f:
        maps = yaml.safe_load(f)
    # 2. 查看所有地图
    map_instance = maps[instance_name or sorted(maps)[0]]
    # 注意：Grid 类要求 agents_xy 和 targets_xy 同时存在才会使用配置的位置
    # 否则会走到 else 分支随机生成位置，导致 initialLocation 被覆盖
    # 在 LifeLong 模式下，初始目标可以和起始位置相同（后续会被实际任务目标覆盖）
    return {"map": map_instance}


def create_env_from_instance(
    fjsp_instance: str | dict, mapf_instance: str | dict, random_target: bool = False,
    obs_type: str | None = None,
) -> GridFactoryEnv:
    """
    从配置文件创建 GridFactoryEnv 环境

    Args:
        fjsp_instance: 配置文件路径
        mapf_instance: 配置文件路径
        random_target: 是否使用随机目标
        obs_type: 观测格式覆盖 ("default" / "MAPF")，None 则读 OBS_TYPE 环境变量

    Returns:
        初始化后的 GridFactoryEnv 实例
    """
    # 1. 获得配置文件
    data_dir = os.getenv("DATA_DIR", "./dataset")
    # =========================
    # FJSP：单文件即实例
    # =========================
    fjsp_dir = Path(data_dir) / "fjsp"

    # 优先按用户传入的 fjsp_instance 解析
    if fjsp_instance:
        fjsp_path = fjsp_dir / fjsp_instance
    else:
        fjsp_path = None

    # 如果没传，或者传了但解析失败，则尝试读取 fjsp 目录下唯一文件
    if fjsp_path is None or not fjsp_path.exists():
        fjsp_candidates = [
            p for p in fjsp_dir.iterdir() if p.is_file() and not p.name.startswith(".")
        ]

        if len(fjsp_candidates) == 1:
            fjsp_path = fjsp_candidates[0]
        elif len(fjsp_candidates) == 0:
            raise FileNotFoundError(
                f"未指定 fjsp_instance，且 FJSP 目录下没有找到实例文件: {fjsp_dir}"
            )
        else:
            raise ValueError(
                f"未指定 fjsp_instance 或指定路径无效，但 FJSP 目录下存在多个候选文件，"
                f"请显式指定 fjsp_instance。候选文件: {[p.name for p in fjsp_candidates]}"
            )

    fjsp_path = str(fjsp_path)

    # =========================
    # MAPF：单文件中包含多个实例
    # 支持：
    #   mapf_instance = "map_name@xxx.yaml"
    #   mapf_instance = "xxx.yaml"
    #   mapf_instance = None / ""
    # =========================
    mapf_dir = Path(data_dir) / "mapf"

    if mapf_instance and "@" in mapf_instance:
        mapf_instance_name, mapf_instance_file = mapf_instance.split("@", 1)
    else:
        # 没写 @ 的时候：
        # - 如果传了 mapf_instance，就认为它是文件名
        # - 文件内部实例名后面默认取第一个
        mapf_instance_name = None
        mapf_instance_file = mapf_instance

    if mapf_instance_file:
        mapf_path = mapf_dir / mapf_instance_file
    else:
        mapf_path = None

    # 如果没传文件名，或者传了但解析失败，则尝试读取 mapf 目录下唯一文件
    if mapf_path is None or not mapf_path.exists():
        mapf_candidates = [
            p for p in mapf_dir.iterdir() if p.is_file() and not p.name.startswith(".")
        ]

        if len(mapf_candidates) == 1:
            mapf_path = mapf_candidates[0]
        elif len(mapf_candidates) == 0:
            raise FileNotFoundError(
                f"未指定 mapf_instance，且 MAPF 目录下没有找到地图文件: {mapf_dir}"
            )
        else:
            raise ValueError(
                f"未指定 mapf_instance 或指定路径无效，但 MAPF 目录下存在多个候选文件，"
                f"请显式指定 mapf_instance。候选文件: {[p.name for p in mapf_candidates]}"
            )

    mapf_path = str(mapf_path)

    # 2. 解析配置
    fjsp_cfg = parse_fjsp_instance(fjsp_path)
    mapf_cfg = parse_mapf_instance(mapf_path, mapf_instance_name)

    # 2.5 将数据集输入转换为共享会话使用的配置格式。
    jobs = fjsp_cfg["jobs"]
    machine_num = fjsp_cfg["machine_number"]
    map_text = mapf_cfg["map"]
    map_lines = str(map_text).splitlines()
    config = {
        "seed": int(os.getenv("SEED", 42)),
        "map": map_text,
        "gridWidth": max((len(line) for line in map_lines), default=20),
        "gridHeight": len(map_lines),
        "num_agents": int(os.getenv("NUM_AGV", 4)),
        "machine_count": machine_num,
        "machine_strategy": "random",
        "obs_radius": int(os.getenv("NUM_RADIUS", 5)),
        "simulation_control": {"max_steps": int(os.getenv("NUM_EPOCH", 256))},
        "jobs": {
            "job_list": [
                {
                    "operations": [
                        {
                            "machine_options_with_time": [
                                [machine_id, processing_time]
                                for processing_time, machine_id in alternatives
                            ]
                        }
                        for alternatives in job
                    ]
                }
                for job in jobs
            ]
        },
    }
    agent_observation_type: str = obs_type or os.getenv("OBS_TYPE", "default")
    return create_env_from_config(config, agent_observation_type=agent_observation_type)


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 进入容器后,挂载某一路径/
    # 数据：/dataset
    # FJSP问题实例：/data/fjsp/instance_name
    # MAPF问题实例：/data/mapf/instance_name
    FJSP_INSTANCE = os.getenv("FJSP_INSTANCE", "J20P10M10.json")
    MAPF_INSTANCE = os.getenv(
        "MAPF_INSTANCE", "medium-mazes-seed-0000@10-medium-mazes-part1.yaml"
    )

    # 从 MAPF_IMAGE 自动推断 observation_type: gpt → "MAPF", 其余 → "default"
    if os.getenv("SOLVER_ROUTE", "astar") == "http":
        mapf_image = os.getenv("MAPF_IMAGE", "")
        os.environ["OBS_TYPE"] = "MAPF" if "gpt" in mapf_image.lower() else "default"

    env = create_env_from_instance(FJSP_INSTANCE, MAPF_INSTANCE, random_target=False)
    # 运输时间预估器: 基于 BFS 最短路 + 历史反馈
    transfer_estimator = None
    transport_aware = os.getenv("TRANSPORT_AWARE", "1") == "1"
    if transport_aware and os.getenv("SOLVER_JOB", "greedy") == "greedy":
        try:
            import numpy as np
            obstacles = env.pogema_env.grid.get_obstacles()
            machines = env.pogema_env.machines
            transfer_estimator = TransferTimeEstimator(machines, obstacles, use_feedback=True)
            LOGGER.info(f"[Run] 运输感知已启用: {len(machines)} 台机器, BFS距离矩阵已预计算")
            stats = transfer_estimator.get_stats()
            LOGGER.info(f"[Run] Estimator stats: avg_base_dist={stats['avg_base_distance']:.1f}")
        except Exception as e:
            LOGGER.warning(f"[Run] 运输感知初始化失败，回退到无感知: {e}")
            transfer_estimator = None

    session = SimulationSession.from_environment(
        env,
        job_solver=os.getenv("SOLVER_JOB", "greedy"),
        route_solver=os.getenv("SOLVER_ROUTE", "astar"),
        assigner=os.getenv("SOLVER_ASSIGN", "random"),
        transfer_time_estimator=transfer_estimator,
    )

    try:
        # --- HTTP Solver 热身：等待微服务就绪 ---
        import requests as _req
        import time as _time

        def _wait_for_service(name, url, max_wait=120):
            """轮询直到服务返回 200，或超时报错"""
            health_url = url.rstrip("/") + "/health"
            deadline = _time.time() + max_wait
            while _time.time() < deadline:
                try:
                    resp = _req.get(health_url, timeout=5)
                    if resp.status_code == 200:
                        print(f"[Warmup] {name} is ready ({url})")
                        return True
                except Exception:
                    pass
                remaining = int(deadline - _time.time())
                print(f"[Warmup] Waiting for {name} ({url})... {remaining}s remaining")
                _time.sleep(2)
            print(f"[Warmup] WARNING: {name} ({url}) did not become ready within {max_wait}s")
            return False

        if os.getenv("SOLVER_JOB", "greedy") == "http":
            _wait_for_service("FJSP", os.getenv("FJSP_SERVICE_URL", "http://fjsp:8002"))
        if os.getenv("SOLVER_ROUTE", "astar") == "http":
            _wait_for_service("MAPF", os.getenv("MAPF_SERVICE_URL", "http://mapf:8001"))

        # 测试多次步进
        num_steps = int(os.getenv("NUM_STEPS", 1000))
        print_interval = int(os.getenv("PRINT_INTERVAL", 50))  # 每 N 步打印一次指标

        for i in range(num_steps):
            obs, rewards, terminations, truncations, infos = session.step()

            # --- 运输感知反馈更新 ---
            if transfer_estimator is not None:
                for agent in obs.get("task_observation", {}).get("agents", []):
                    if agent.finished_tasks:
                        for task in agent.finished_tasks:
                            transfer_estimator.update_from_task(task)

            # --- 指标打印 ---
            if (i + 1) % print_interval == 0 or terminations["job_done"]:
                m = infos.get('metrics', {})
                print(
                    f"[Step {i+1:>4d}]  "
                    f"machine_util={m.get('machine_utilization', 0):.3f}  "
                    f"op_queue_wait={m.get('operation_queue_waiting_time_mean', 0):.1f}  "
                    f"stationary={m.get('tasked_stationary_count', 0)}  "
                    f"swap_conflict={m.get('swap_conflict_count', 0)}  "
                    f"agv_loaded={m.get('agv_loaded_utilization', 0):.3f}  "
                    f"agv_busy={m.get('agv_busy_utilization', 0):.3f}  "
                    f"delay_ratio={m.get('transport_delay_ratio', 0):.3f}  "
                    f"inbound_wait={m.get('machine_waiting_for_inbound_transfer_ratio', 0):.3f}  "
                    f"reward={infos.get('metrics_reward', 0):.4f}"
                )

            if terminations["job_done"]:
                # 打印 episode 汇总
                summary = env.metrics_hub.get_episode_summary()
                print("\n===== Episode Summary =====")
                for k, v in summary.items():
                    print(f"  {k}: {v}")
                print("===========================\n")
                break

            res = draw_svg_with_machines_and_targets(env.pogema_env, env.env_timeline)

            # SVG 输出到 sky_logs/svg/
            svg_dir = os.path.join(os.getenv("SKY_LOG_DIR", "./sky_logs"), "svg")
            os.makedirs(svg_dir, exist_ok=True)
            with open(f"{svg_dir}/{env.env_timeline}.svg", "w") as f:
                f.write(res)
        else:
            # 没有 break（达到 max_steps 但未完成）
            summary = env.metrics_hub.get_episode_summary()
            print(f"\n===== Episode ended at max_steps={num_steps} =====")
            for k, v in summary.items():
                print(f"  {k}: {v}")

    finally:
        session.close()
