# 这里对新的环境与coordinator进行测试

# 这里对machine生成策略进行测试，查看是否成功实现不同的machine生成策略
from pogema import GridConfig
from sky_executor.grid_factory.factory.grid_factory_env.grid_factory_env import (
    GridFactoryEnv,
)
from sky_executor.grid_factory.factory.grid_factory_env.Utils.pic_drawer import (
    draw_svg_with_machines_and_targets,
)

from sky_executor.grid_factory.factory.grid_factory_env.Component.Coordinator.coordinator import (
    Coordinator,
)


def sky_test_new_env():
    """测试网格工厂环境"""
    print("=== 测试新的环境交互方式 ===")
    # 创建环境
    env = GridFactoryEnv()

    # 测试环境重置
    obs, info = env.reset(seed=42)
    res = draw_svg_with_machines_and_targets(env.pogema_env, env.env_timeline)
    with open("initial.svg", "w") as f:
        f.write(res)

    coordinator = Coordinator()
    actions = coordinator.decide(obs)
    print(f"初始动作: {actions}")

    obs, rewards, terminations, truncations, infos = env.step(actions)
    # 测试多次步进
    for i in range(5):
        actions = coordinator.decide(obs)
        env.show_actions(actions)
        obs, rewards, terminations, truncations, infos = env.step(actions)

        res = draw_svg_with_machines_and_targets(env.pogema_env, env.env_timeline)
        with open(f"temp{env.env_timeline}.svg", "w") as f:
            f.write(res)
        print(f"步进 {i + 1}: 位置 {env.get_agent_positions()}")

    print("\n=== 测试完成 ===")
    return True


if __name__ == "__main__":
    try:
        sky_test_new_env()
        print("\n🎉 所有测试通过！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
