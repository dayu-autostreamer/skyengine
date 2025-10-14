'''
@Project ：tiangong 
@File    ：file_service.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/7/21 11:35 
'''

from pogema import GridConfig


def get_default_config():
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
    # todo 此处后续需要动态实现
    job_config = {}
    agent_config = {'agent_name': 'deterministic_policy'}
    hyper_config = {'seed':42}
    return grid_config, job_config, agent_config,hyper_config
