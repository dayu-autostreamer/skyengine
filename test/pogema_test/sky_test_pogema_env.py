'''
@Project ：SkyEngine 
@File    ：sky_test_pogema_env.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/8 23:12
'''
from pogema import GridConfig
from sky_simulator.environment.grid_factory.grid_factory_env.grid_factory_env import GridFactoryEnv
from sky_simulator.environment.grid_factory.Agent.DeterministicPolicy import DeterministicPolicy
from sky_logs.dc_helper import DiskCacheHelper
from config.all_field_const import CacheInfo

dh = DiskCacheHelper(expire=600)


def sky_test_grid_factory_env():
    """测试网格工厂环境"""
    print("=== 测试基于Pogema的网格工厂环境 ===")

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

    print(f"网格配置: {grid_config.num_agents}个智能体, {grid_config.size}x{grid_config.size}网格")

    # 创建环境
    env = GridFactoryEnv(
        grid_config=grid_config,
    )

    print("✓ 环境创建成功")

    # 测试环境重置
    obs, info = env.reset(seed=42)
    print(dh.get(CacheInfo.SVG_IMAGE.value))
    print(f"✓ 环境重置成功")

    dp = DeterministicPolicy()
    # 测试环境步进
    print(obs['agent_observation'])
    agent_actions = dp.act(obs['agent_observation'])
    machine_actions = []
    print(f"请看这里：{agent_actions}")
    obs, rewards, terminations, truncations, infos = env.step({'agent_actions': agent_actions,
                                                               'machine_actions': machine_actions})

    print("✓ 环境步进成功")

    # 获取环境信息
    print(f"智能体位置: {env.get_agent_positions()}")
    print(f"智能体目标: {env.get_agent_targets()}")
    print(f"智能体信息: {env.get_agents_info()}")

    # 测试多次步进
    for i in range(5):
        agent_actions = dp.act(obs['agent_observation'])
        machine_actions = []
        obs, rewards, terminations, truncations, infos = env.step({'agent_actions': agent_actions,
                                                                   'machine_actions': machine_actions})
        # print(dh.get(CacheInfo.SVG_IMAGE.value))
        print(f"步进 {i + 1}: 位置 {env.get_agent_positions()}")

    print("✓ 多次步进测试成功")

    # 测试环境状态
    print(f"环境时间: {env.get_env_timeline()}")

    print("\n=== 测试完成 ===")
    return True


if __name__ == '__main__':
    try:
        # 测试Pogema环境
        sky_test_grid_factory_env()
        print("\n🎉 所有测试通过！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
