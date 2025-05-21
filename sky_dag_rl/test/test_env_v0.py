'''
@Project ：tiangong 
@File    ：test_env_v0.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/19 11:13 
'''
from sky_dag_rl.sky_dag import sky_dag_v0  # 替换为你的环境文件名

# 创建环境与智能体
# greedy_Agent = sky_dag_v0.GreedyAgent(name='sky', agent_id='1')
random_Agent = sky_dag_v0.RandomAgent(name='sky', agent_id='1')
env = sky_dag_v0.SkyDagEnv(agent=random_Agent)

# 重置环境
observations = env.reset()

# 运行一个 episode（直到结束）
while random_Agent.is_alive():
    # 传入agent在内部决策,外部不需要主动传入action了
    observations, rewards, terminations, truncations, infos = env.step()

    # 渲染当前状态（控制台打印）
    env.render()

    # 更新 done 状态
    done = terminations
