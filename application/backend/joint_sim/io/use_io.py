"""
@Project ：SkyEngine
@File    ：use_io.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2026/3/16
"""

import json
from os import makedirs
from pathlib import Path
from typing import Dict, Any, List, Tuple

from pogema import GridConfig

from joint_sim.utils.structure import MachineConfig, JobConfig
from joint_sim.grid_factory_env import GridFactoryEnv


def load_grid_factory_config(config_path: str) -> Dict[str, Any]:
    """
    读取 grid_factory.json 配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        解析后的配置字典
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    return config


def parse_grid_config(config: Dict[str, Any]) -> GridConfig:
    """
    从 JSON 配置解析 GridConfig

    Args:
        config: 完整的配置字典

    Returns:
        GridConfig 实例
    """
    topology = config.get("topology", {})
    agvs = config.get("agvs", [])

    grid_width = topology.get("gridWidth", 20)
    grid_height = topology.get("gridHeight", 20)
    
    if grid_width != grid_height:
        raise ValueError("gridWidth 和 gridHeight 必须相等")
    
    num_agents = len(agvs)

    # 获取 AGV 初始位置
    agents_start_xy = [tuple(agv["initialLocation"]) for agv in agvs]

    # 注意：Grid 类要求 agents_xy 和 targets_xy 同时存在才会使用配置的位置
    # 否则会走到 else 分支随机生成位置，导致 initialLocation 被覆盖
    # 在 LifeLong 模式下，初始目标可以和起始位置相同（后续会被实际任务目标覆盖）
    return GridConfig(
        size=max(grid_width, grid_height),
        num_agents=num_agents,
        density=0.0,  # 无随机障碍物
        seed=42,
        max_episode_steps=256,
        obs_radius=5,
        on_target="restart",
        agents_xy=agents_start_xy if agents_start_xy else None,
        targets_xy=agents_start_xy if agents_start_xy else None,  # 初始目标和起始位置相同
    )


def parse_machine_config(
    config: Dict[str, Any],
) -> Tuple[MachineConfig, List[Tuple[int, int]]]:
    topology = config.get("topology", {})
    machines = topology.get("machines", {})

    machine_positions = []
    for machine_key, machine_info in machines.items():
        location = tuple(machine_info["location"])
        machine_positions.append(location)

    machine_config = MachineConfig(
        num_machines=len(machines),
        strategy="custom",  # 改为 custom
        custom_positions=machine_positions,  # 传入自定义位置
        seed=42,
    )

    return machine_config, machine_positions


def parse_job_config(config: Dict[str, Any], num_machines: int) -> JobConfig:
    """
    从 JSON 配置解析 JobConfig

    Args:
        config: 完整的配置字典
        num_machines: 机器总数

    Returns:
        JobConfig 实例
    """
    jobs = config.get("jobs", {})
    job_list = jobs.get("job_list", [])

    if not job_list:
        # 如果没有任务，使用默认配置
        return JobConfig(
            num_jobs=1,
            min_ops_per_job=0,
            max_ops_per_job=0,
            min_proc_time=1,
            max_proc_time=1,
            machine_choices=1,
            total_machines=num_machines,
            seed=42,
        )

    # 计算工序数量的范围
    ops_counts = [len(job.get("operations", [])) for job in job_list]
    min_ops = min(ops_counts) if ops_counts else 1
    max_ops = max(ops_counts) if ops_counts else 1

    # 计算处理时间的范围
    all_durations = []
    for job in job_list:
        for op in job.get("operations", []):
            all_durations.append(op.get("duration", 1))

    min_proc = min(all_durations) if all_durations else 1
    max_proc = max(all_durations) if all_durations else 1

    return JobConfig(
        num_jobs=len(job_list),
        min_ops_per_job=min_ops,
        max_ops_per_job=max_ops,
        min_proc_time=min_proc,
        max_proc_time=max_proc,
        machine_choices=1,  # JSON 中已指定机器
        total_machines=num_machines,
        seed=42,
    )


def create_env_from_config(
    config_path: str | dict, random_target: bool = False
) -> GridFactoryEnv:
    """
    从配置文件创建 GridFactoryEnv 环境

    Args:
        config_path: 配置文件路径
        random_target: 是否使用随机目标

    Returns:
        初始化后的 GridFactoryEnv 实例
    """
    # 1. 按类型划分逻辑，加载/验证配置
    if isinstance(config_path, str):
        config = load_grid_factory_config(config_path)
        print(f"成功从路径 {config_path} 加载配置")

    elif isinstance(config_path, dict):
        config = config_path
        print("直接使用传入的配置字典")

    else:
        print(
            f"config_path 必须是 str（文件路径）或 dict（配置字典），但收到 {type(config_path).__name__} 类型"
        )

    # 2. 解析配置
    grid_cfg = parse_grid_config(config)
    machine_cfg, machine_positions = parse_machine_config(config)
    job_cfg = parse_job_config(config, machine_cfg.num_machines)

    # 3. 设置机器位置到 grid_config
    grid_cfg.possible_targets_xy = machine_positions

    print(
        f"已创建 GridFactoryEnv，环境参数：\n"
        f"grid_config: {grid_cfg}\n"
        f"machine_config: {machine_cfg}\n"
        f"job_config: {job_cfg}"
    )
    # 4. 创建环境
    env = GridFactoryEnv(
        grid_config=grid_cfg,
        machine_config=machine_cfg,
        job_config=job_cfg,
        random_target=random_target,
    )

    return env


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 配置文件路径
    CONFIG_PATH = r"E:\Project\FinalPro\SkyEngine\dataset\grid_factory.json"

    # ====== 示例 1: 基础环境初始化 ======
    print("\n" + "#" * 60)
    print("# 示例 1: 基础环境初始化")
    print("#" * 60)

    env = create_env_from_config(CONFIG_PATH, random_target=False)
    obs, info = env.reset()
    from joint_sim.component.Coordinator.coordinator import (
        Coordinator,
    )
    from joint_sim.utils.pic_drawer import (
        draw_svg_with_machines_and_targets,
    )

    coordinator = Coordinator()
    # 测试多次步进
    for i in range(150):
        actions = coordinator.decide(obs)

        obs, rewards, terminations, truncations, infos = env.step(actions)

        res = draw_svg_with_machines_and_targets(env.pogema_env, env.env_timeline)
        makedirs("temp", exist_ok=True)
        with open(f"temp/{env.env_timeline}.svg", "w") as f:
            f.write(res)
