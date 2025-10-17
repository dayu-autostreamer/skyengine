'''
@Project ：tiangong 
@File    ：SimpleTrainer.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 21:24 
'''

import time
from typing import Dict, Any
from sky_logs.logger import LOGGER

from .BaseTrainer import BaseTrainer


class SimpleTrainer(BaseTrainer):
    """
    简单训练器实现
    适用于基础的强化学习训练
    """
    
    def __init__(self, 
                 env, 
                 agent, 
                 episodes: int = 100,
                 save_dir: str = "./models",
                 log_interval: int = 10,
                 save_interval: int = 50,
                 eval_interval: int = 20,
                 max_episode_steps: int = 1000,
                 learning_rate: float = 0.001,
                 gamma: float = 0.99
                 ):
        """
        初始化简单训练器
        
        Args:
            env: 训练环境
            agent: 智能体
            episodes: 训练轮数
            save_dir: 模型保存目录
            log_interval: 日志记录间隔
            save_interval: 模型保存间隔
            eval_interval: 评估间隔
            max_episode_steps: 每轮最大步数
            learning_rate: 学习率
            gamma: 折扣因子
        """
        super().__init__(env, agent, episodes, save_dir, log_interval, 
                        save_interval, eval_interval, max_episode_steps)
        
        self.learning_rate = learning_rate
        self.gamma = gamma
        
        LOGGER.info(f"简单训练器初始化完成 - 学习率: {learning_rate}, 折扣因子: {gamma}")

    def train_episode(self, episode: int) -> Dict[str, Any]:
        """
        训练一个episode
        
        Args:
            episode: 当前episode编号
            
        Returns:
            包含训练指标的字典
        """
        episode_start_time = time.time()
        obs = self.env.reset()
        episode_reward = 0
        episode_length = 0
        episode_loss = 0
        
        while not self.env.env_is_finished() and episode_length < self.max_episode_steps:
            # 智能体决策
            action = self.agent.decision(obs)
            
            # 环境执行
            next_obs, reward, done, _, _ = self.env.step({'decisions': action})
            
            # 智能体学习
            if hasattr(self.agent, 'train'):
                loss = self.agent.train(obs, action, reward, next_obs, done)
                if loss is not None:
                    episode_loss += loss
            
            # 更新状态
            obs = next_obs
            episode_reward += sum(reward.values()) if isinstance(reward, dict) else reward
            episode_length += 1
            self.total_steps += 1
        
        episode_time = time.time() - episode_start_time
        
        # 记录episode信息
        if episode % self.log_interval == 0:
            LOGGER.info(f"Episode {episode} - 奖励: {episode_reward:.2f}, "
                       f"长度: {episode_length}, 用时: {episode_time:.2f}s")
        
        return {
            'episode_rewards': episode_reward,
            'episode_lengths': episode_length,
            'episode_times': episode_time,
            'losses': episode_loss / max(episode_length, 1)
        }


class DQNTrainer(BaseTrainer):
    """
    DQN训练器
    适用于深度Q网络训练
    """
    
    def __init__(self, 
                 env, 
                 agent, 
                 episodes: int = 1000,
                 save_dir: str = "./models",
                 log_interval: int = 10,
                 save_interval: int = 100,
                 eval_interval: int = 50,
                 max_episode_steps: int = 1000,
                 batch_size: int = 32,
                 target_update_freq: int = 100,
                 epsilon_start: float = 1.0,
                 epsilon_end: float = 0.01,
                 epsilon_decay: float = 0.995):
        """
        初始化DQN训练器
        
        Args:
            env: 训练环境
            agent: DQN智能体
            episodes: 训练轮数
            save_dir: 模型保存目录
            log_interval: 日志记录间隔
            save_interval: 模型保存间隔
            eval_interval: 评估间隔
            max_episode_steps: 每轮最大步数
            batch_size: 批处理大小
            target_update_freq: 目标网络更新频率
            epsilon_start: 初始探索率
            epsilon_end: 最终探索率
            epsilon_decay: 探索率衰减
        """
        super().__init__(env, agent, episodes, save_dir, log_interval, 
                        save_interval, eval_interval, max_episode_steps)
        
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.current_epsilon = epsilon_start
        
        LOGGER.info(f"DQN训练器初始化完成 - 批大小: {batch_size}, 目标更新频率: {target_update_freq}")

    def train_episode(self, episode: int) -> Dict[str, Any]:
        """
        训练一个DQN episode
        
        Args:
            episode: 当前episode编号
            
        Returns:
            包含训练指标的字典
        """
        episode_start_time = time.time()
        obs = self.env.reset()
        episode_reward = 0
        episode_length = 0
        episode_loss = 0
        
        while not self.env.env_is_finished() and episode_length < self.max_episode_steps:
            # 使用epsilon-greedy策略选择动作
            if hasattr(self.agent, 'select_action_epsilon_greedy'):
                action = self.agent.select_action_epsilon_greedy(obs, self.current_epsilon)
            else:
                action = self.agent.decision(obs)
            
            # 环境执行
            next_obs, reward, done, _, _ = self.env.step({'decisions': action})
            
            # 存储经验
            if hasattr(self.agent, 'store_experience'):
                self.agent.store_experience(obs, action, reward, next_obs, done)
            
            # 训练网络
            if hasattr(self.agent, 'train') and len(self.agent.replay_buffer) >= self.batch_size:
                loss = self.agent.train(self.batch_size)
                if loss is not None:
                    episode_loss += loss
            
            # 更新目标网络
            if self.total_steps % self.target_update_freq == 0:
                if hasattr(self.agent, 'update_target_network'):
                    self.agent.update_target_network()
            
            # 更新状态
            obs = next_obs
            episode_reward += sum(reward.values()) if isinstance(reward, dict) else reward
            episode_length += 1
            self.total_steps += 1
        
        # 更新epsilon
        self.current_epsilon = max(self.epsilon_end, 
                                 self.current_epsilon * self.epsilon_decay)
        
        episode_time = time.time() - episode_start_time
        
        # 记录episode信息
        if episode % self.log_interval == 0:
            LOGGER.info(f"Episode {episode} - 奖励: {episode_reward:.2f}, "
                       f"长度: {episode_length}, Epsilon: {self.current_epsilon:.3f}")
        
        return {
            'episode_rewards': episode_reward,
            'episode_lengths': episode_length,
            'episode_times': episode_time,
            'losses': episode_loss / max(episode_length, 1)
        }


class PPOTrainer(BaseTrainer):
    """
    PPO训练器
    适用于近端策略优化算法
    """
    
    def __init__(self, 
                 env, 
                 agent, 
                 episodes: int = 1000,
                 save_dir: str = "./models",
                 log_interval: int = 10,
                 save_interval: int = 100,
                 eval_interval: int = 50,
                 max_episode_steps: int = 1000,
                 update_epochs: int = 4,
                 clip_ratio: float = 0.2,
                 value_coef: float = 0.5,
                 entropy_coef: float = 0.01):
        """
        初始化PPO训练器
        
        Args:
            env: 训练环境
            agent: PPO智能体
            episodes: 训练轮数
            save_dir: 模型保存目录
            log_interval: 日志记录间隔
            save_interval: 模型保存间隔
            eval_interval: 评估间隔
            max_episode_steps: 每轮最大步数
            update_epochs: 每次更新的轮数
            clip_ratio: PPO裁剪比例
            value_coef: 价值函数系数
            entropy_coef: 熵系数
        """
        super().__init__(env, agent, episodes, save_dir, log_interval, 
                        save_interval, eval_interval, max_episode_steps)
        
        self.update_epochs = update_epochs
        self.clip_ratio = clip_ratio
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        
        # PPO需要收集多个episode的数据
        self.episode_buffer = []
        self.update_frequency = 10  # 每10个episode更新一次
        
        LOGGER.info(f"PPO训练器初始化完成 - 更新轮数: {update_epochs}, 裁剪比例: {clip_ratio}")

    def train_episode(self, episode: int) -> Dict[str, Any]:
        """
        训练一个PPO episode
        
        Args:
            episode: 当前episode编号
            
        Returns:
            包含训练指标的字典
        """
        episode_start_time = time.time()
        obs = self.env.reset()
        episode_reward = 0
        episode_length = 0
        episode_data = []
        
        while not self.env.env_is_finished() and episode_length < self.max_episode_steps:
            # 智能体决策并获取动作概率
            if hasattr(self.agent, 'get_action_and_value'):
                action, log_prob, value = self.agent.get_action_and_value(obs)
            else:
                action = self.agent.decision(obs)
                log_prob = 0
                value = 0
            
            # 环境执行
            next_obs, reward, done, _, _ = self.env.step({'decisions': action})
            
            # 存储episode数据
            episode_data.append({
                'obs': obs,
                'action': action,
                'reward': sum(reward.values()) if isinstance(reward, dict) else reward,
                'log_prob': log_prob,
                'value': value,
                'done': done
            })
            
            # 更新状态
            obs = next_obs
            episode_reward += sum(reward.values()) if isinstance(reward, dict) else reward
            episode_length += 1
            self.total_steps += 1
        
        # 计算优势函数和回报
        if hasattr(self.agent, 'compute_advantages_and_returns'):
            episode_data = self.agent.compute_advantages_and_returns(episode_data)
        
        # 存储到缓冲区
        self.episode_buffer.extend(episode_data)
        
        episode_time = time.time() - episode_start_time
        
        # 定期更新策略
        episode_loss = 0
        if len(self.episode_buffer) >= self.update_frequency * self.max_episode_steps:
            if hasattr(self.agent, 'update_policy'):
                episode_loss = self.agent.update_policy(
                    self.episode_buffer, 
                    self.update_epochs,
                    self.clip_ratio,
                    self.value_coef,
                    self.entropy_coef
                )
            self.episode_buffer = []  # 清空缓冲区
        
        # 记录episode信息
        if episode % self.log_interval == 0:
            LOGGER.info(f"Episode {episode} - 奖励: {episode_reward:.2f}, "
                       f"长度: {episode_length}, 损失: {episode_loss:.4f}")
        
        return {
            'episode_rewards': episode_reward,
            'episode_lengths': episode_length,
            'episode_times': episode_time,
            'losses': episode_loss
        }
