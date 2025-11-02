# 此处测试环境在job层本身的相关情况
from sky_executor.grid_factory.factory.grid_factory_env.grid_factory_env import (
    GridFactoryEnv,
)
from sky_executor.grid_factory.factory.grid_factory_env.Utils.pic_drawer import (
    draw_svg_with_machines_and_targets,
)


if __name__ == "__main__":
    env = GridFactoryEnv()
    
    # 测试环境重置
    obs, info = env.reset(seed=42)
    res = draw_svg_with_machines_and_targets(env.pogema_env, env.get_env_timeline())
    with open("temp.svg", "w") as f:
        f.write(res)
