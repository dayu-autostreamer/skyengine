'''
@Project ：tiangong 
@File    ：test_agv_callback.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/18 15:11 
'''
import argparse
from sky_simulator.lifecycle.bootstrap import bootstrap

# 测试agv的回调
if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="启动环境与智能体")
    parser.add_argument('--config', type=str, help='YAML 配置文件路径')

    args = parser.parse_args()
    config_path = args.config
    # config_path = '../../config/application_config.yaml'

    # 创建环境与智能体
    env, agent = bootstrap(config_path)
    import sky_simulator.environment.packet_factory.packet_factory_env.packet_factory_env as packet_factory_env

    env: packet_factory_env

    # 重置环境
    observations = env.reset()

    # 运行一个 episode（直到结束）
    while not env.env_is_finished():
        # 输入获得环境状态并决策
        actions = env.action_space(agent)

        # agent在外部决策
        observations, rewards, terminations, truncations, infos = env.step(actions)

        # 渲染当前状态（控制台打印）
        env.render()

        # 更新 done 状态
        done = terminations

    LOGGER.info(f"total makespan: {env.env_timeline}s")