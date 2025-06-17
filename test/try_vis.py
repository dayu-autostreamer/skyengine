from sky_simulator.packet_factory import packet_factory_v0 
from sky_simulator.call_back.base_callback.EnvVisualizer import EnvVisualizer
from sky_simulator.packet_factory.packet_factory_env.Utils.logger import LOGGER

# 创建环境与智能体
random_Agent = packet_factory_v0.RandomAgent(name='sky', agent_id='1')
env = packet_factory_v0.PacketFactoryEnv(agent=random_Agent)

# 重置环境
observations = env.reset()

env_visualizer = EnvVisualizer(env)
env_visualizer.visualize_env(fps=3)

# 运行一个 episode（直到结束）
while random_Agent.is_alive():
    # 输入获得环境状态并决策
    actions = env.action_space(random_Agent)

    # agent在外部决策
    observations, rewards, terminations, truncations, infos = env.step(actions)
    
    # 启动可视化（每step更新一次）
    env_visualizer.visualize_env(fps=3)

    # 渲染当前状态（控制台打印）
    env.render()

    # 更新 done 状态
    done = terminations

LOGGER.info(f"total makespan: {env.env_timeline}s")