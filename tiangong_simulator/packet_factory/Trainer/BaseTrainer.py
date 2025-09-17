'''
@Project ：tiangong 
@File    ：BaseTrainer.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 21:24 
'''



class Trainer:
    def __init__(self, env: PacketFactoryEnv, agent: BaseAgent, episodes=100):
        self.env = env
        self.agent = agent
        self.episodes = episodes

    def train(self):
        for ep in range(self.episodes):
            obs = self.env.reset()
            done = False
            ep_reward = 0

            while not self.env.env_is_finished():
                # agent 根据 obs 选择动作
                action = self.agent.select_action(obs)

                # 环境执行
                next_obs, reward, done, _, _ = self.env.step(action)

                # agent 学习
                self.agent.learn(obs, action, reward, next_obs, done)

                obs = next_obs
                ep_reward += sum(reward.values())

            print(f"Episode {ep}: total reward = {ep_reward}")
