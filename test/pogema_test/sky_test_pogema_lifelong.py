"""
@Project ：SkyEngine
@File    ：sky_test_pogema_lifelong.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/17 20:13
"""

from sky_executor.grid_factory.factory.Agent.DeterministicPolicy import (
    DeterministicPolicy,
)
from sky_executor.grid_factory.factory.grid_factory_env.Utils.machine import (
    generate_machines,
    MachineConfig,
)
from sky_executor.grid_factory.factory.grid_factory_env.Utils.pic_drawer import (
    draw_svg,
    draw_svg_with_machines_and_targets,
)
import random


import numpy as np
from pogema import GridConfig
from pogema.envs import PogemaLifeLong
from sky_executor.grid_factory.factory.grid_factory_env.Utils.assign_env import (
    PogemaLifeLongWithAssign,
)


def test_pogema_lifelong():
    """
    测试 PogemaLifeLong 环境
    """
    # ---------- 1. 配置环境 ----------
    num_agents = 3
    size = 10

    grid_config = GridConfig(
        num_agents=num_agents,
        size=size,
        density=0.2,
        obs_radius=2,
        max_episode_steps=20,
    )
    # ---------- 2. 初始化 PogemaLifeLong ----------
    from pogema import AnimationMonitor

    env = PogemaLifeLongWithAssign(grid_config)
    env = AnimationMonitor(env)
    env.reset()
    print(env.grid.get_obstacles())
    # ======================= 生成机器位置 =============================
    machines = generate_machines(
        env.grid.get_obstacles(),
        MachineConfig(
            num_machines=4,
            strategy="random",
            seed=42,
            zones=4,
        ),
    )
    machine_possible_positions = [m.location for m in machines]
    print(f"可行的空地:{machine_possible_positions}")
    # 预补偿：在输入 possible_targets_xy 时减去 obs_radius
    # possible_targets_xy = [
    #     (x - grid_config.obs_radius, y - grid_config.obs_radius)
    #     for (x, y) in machine_possible_positions
    # ]
    possible_targets_xy = machine_possible_positions
    # ======================= 结束生成机器位置 =============================
    env.grid_config.possible_targets_xy = possible_targets_xy
    # ---------- 3. 重置环境 ----------
    obs, info = env.reset()
    env.render()
    print("\n渲染环境 (SVG)")
    # 利用env.grid_config.possible_targets_xy和env.grid.finishes_xy即可绘制。
    # svg_str = draw_svg_with_machines_and_targets(env)
    # with open("temp.svg", "w") as f:
    #     f.write(svg_str)
    for idx, inf in enumerate(info):
        print(f"Agent {idx}: {inf}")

    # ---------- 4. 分配新的初始 agent 的目标位置 ----------
    print("修正后的初始目标位置:")
    for idx in range(num_agents):
        # goal = env.grid.finishes_xy[idx]
        env.grid.finishes_xy[idx] = random.choice(possible_targets_xy)
        print(f"Agent {idx} target: {env.grid.finishes_xy[idx]}")

    dp = DeterministicPolicy()
    # ---------- 5. 随机移动 agents，模拟几个 step ----------
    idx = 0
    while True:
        print(env.grid.finishes_xy)
        idx += 1
        actions = dp.act(obs)
        obs, rewards, terminated, truncated, infos = env.step(actions)
        # print(obs, rewards, terminated, truncated, infos)
        # ---------- 6. 渲染环境 ----------
        env.render()

        svg_str = draw_svg_with_machines_and_targets(env, timeline=idx)
        with open(f"temp{idx}.svg", "w") as f:
            f.write(svg_str)
        if idx > 40:
            break


if __name__ == "__main__":
    test_pogema_lifelong()
