# 此处测试环境在job层本身的相关情况
from pogema import GridConfig

from sky_executor.grid_factory.factory.grid_factory_env.grid_factory_env import (
    GridFactoryEnv,
)
from sky_executor.grid_factory.factory.grid_factory_env.Utils.pic_drawer import (
    draw_svg_with_machines_and_targets,
)

if __name__ == "__main__":
    grid_config = GridConfig(
        num_agents=4,
        size=8,
        density=0.3,
        seed=42,
        max_episode_steps=256,
        obs_radius=5,
        on_target="restart",
    )
    env = GridFactoryEnv(grid_config=grid_config)
    # possible_targets_xy = [
    #     (x - grid_config.obs_radius, y - grid_config.obs_radius)
    #     for (x, y) in machine_possible_positions
    # ]
    # 测试环境重置
    obs, info = env.reset(seed=42)
    print(f"当前可能的机器位置{env.machine_possible_positions}")
    print(f"当前的目标位置{env.current_targets}")
    print(env.pogema_env.grid.get_obstacles())
    res = draw_svg_with_machines_and_targets(env.pogema_env, env.get_env_timeline())
    with open("temp.svg", "w") as f:
        f.write(res)
