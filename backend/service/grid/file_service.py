'''
@Project ：tiangong 
@File    ：file_service.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/7/21 11:35 
'''

from pogema import GridConfig


def get_default_config(
        num_agents=4,
        size=15,
        density=0.3,
        seed=42,
        max_episode_steps=100,
        obs_radius=3,
        collision_system='priority',
        on_target='restart',
        map_name="sky_pogema-logo",
):
    grid_config = GridConfig(
        num_agents=num_agents,  # 4个智能体
        size=size,  # 15x15网格
        density=density,  # 30%障碍物密度
        seed=42,  # 随机种子
        max_episode_steps=max_episode_steps,  # 最大步数
        obs_radius=obs_radius,  # 观察半径
        collision_system=collision_system,  # 碰撞系统
        on_target=on_target,  # 到达目标后重启
        map_name=map_name
    )
    # todo 此处后续需要动态实现
    job_config = {}
    agv_agent_config = {'agent_name': 'deterministic_policy'}
    system_agent_config = {'agent_name': 'deterministic_policy'}
    hyper_config = {'seed': 42}
    return grid_config, job_config, agv_agent_config, system_agent_config, hyper_config
