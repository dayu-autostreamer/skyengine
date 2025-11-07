'''
@Project ：SkyEngine 
@File    ：sky_test_coordinator.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 23:10
'''
# 这里对machine生成策略进行测试，查看是否成功实现不同的machine生成策略
from pogema import GridConfig
from sky_executor.grid_factory.factory.grid_factory_env.grid_factory_env import GridFactoryEnv
from sky_executor.grid_factory.factory.Agent.DeterministicPolicy import DeterministicPolicy
from sky_executor.grid_factory.factory.grid_factory_env.Utils.pic_drawer import draw_svg, \
    draw_svg_with_machines_and_targets

from sky_executor.grid_factory.factory.grid_factory_env.Component.Coordinator.coordinator import Coordinator


def sky_test_coordinator():
    """测试网格工厂环境"""
    print("=== 测试新的绘图方法 ===")
    # 创建环境
    env = GridFactoryEnv()

    # 测试环境重置
    obs, info = env.reset(seed=42)
    res = draw_svg(env.pogema_env, env.get_env_timeline())
    with open("temp.svg", "w") as f:
        f.write(res)

    coordinator = Coordinator()
    actions = coordinator.decide(obs)

    obs, rewards, terminations, truncations, infos = env.step(actions)

    # 测试多次步进
    for i in range(5):
        coordinator = Coordinator()
        actions = coordinator.decide(obs)
        obs, rewards, terminations, truncations, infos = env.step(actions)

        res = draw_svg(env.pogema_env, env.get_env_timeline())
        with open(f"temp{env.get_env_timeline()}.svg", "w") as f:
            f.write(res)
        print(f"步进 {i + 1}: 位置 {env.get_agent_positions()}")

    print("\n=== 测试完成 ===")
    return True


def sky_test_machine_draw_method():
    """测试网格工厂环境"""
    print("=== 测试带有机器的绘图方法 ===")

    # 创建网格配置
    grid_config = GridConfig(
        num_agents=4,  # 4个智能体
        size=15,  # 15x15网格
        density=0.3,  # 30%障碍物密度
        seed=42,  # 随机种子
        max_episode_steps=100,  # 最大步数
        obs_radius=3,  # 观察半径
        collision_system='priority',  # 碰撞系统
        on_target='restart'  # 到达目标后重启
    )

    # 创建环境
    env = GridFactoryEnv(
        grid_config=grid_config,
    )

    # 测试环境重置
    obs, info = env.reset(seed=42)
    res = draw_svg_with_machines_and_targets(env.pogema_env, env.machines)
    with open("temp.svg", "w") as f:
        f.write(res)

    dp = DeterministicPolicy()
    print(obs['agent_observation'])
    agent_actions = dp.act(obs['agent_observation'])
    machine_actions = []
    obs, rewards, terminations, truncations, infos = env.step({'agent_actions': agent_actions,
                                                               'machine_actions': machine_actions})

    # 测试多次步进
    for i in range(5):
        agent_actions = dp.act(obs['agent_observation'])
        machine_actions = []
        obs, rewards, terminations, truncations, infos = env.step({'agent_actions': agent_actions,
                                                                   'machine_actions': machine_actions})

        res = draw_svg_with_machines_and_targets(env.pogema_env, env.machines)
        with open(f"temp{env.get_env_timeline()}.svg", "w") as f:
            f.write(res)
        print(f"步进 {i + 1}: 位置 {env.get_agent_positions()}")

    print("\n=== 测试完成 ===")
    return True


if __name__ == '__main__':
    try:
        sky_test_new_draw_method()
        sky_test_machine_draw_method()
        print("\n🎉 所有测试通过！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
