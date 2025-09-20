'''
@Project ：tiangong 
@File    ：BaseTrainer.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 21:24 
'''

import os
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from tiangong_logs.logger import LOGGER

from tiangong_simulator.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
from tiangong_simulator.packet_factory.Agent.BaseAgent import BaseAgent


class BaseTrainer(ABC):
    """
    基础训练器抽象类
    定义了训练器的基本接口和通用功能
    """
    
    def __init__(self, 
                 env: PacketFactoryEnv, 
                 agent: BaseAgent, 
                 episodes: int = 100,
                 save_dir: str = "./models",
                 log_interval: int = 10,
                 save_interval: int = 50,
                 eval_interval: int = 20,
                 max_episode_steps: int = 1000):
        """
        初始化训练器
        
        Args:
            env: 训练环境
            agent: 智能体
            episodes: 训练轮数
            save_dir: 模型保存目录
            log_interval: 日志记录间隔
            save_interval: 模型保存间隔
            eval_interval: 评估间隔
            max_episode_steps: 每轮最大步数
        """
        self.env = env
        self.agent = agent
        self.episodes = episodes
        self.save_dir = save_dir
        self.log_interval = log_interval
        self.save_interval = save_interval
        self.eval_interval = eval_interval
        self.max_episode_steps = max_episode_steps
        
        # 训练统计
        self.training_metrics = {
            'episode_rewards': [],
            'episode_lengths': [],
            'episode_times': [],
            'losses': [],
            'eval_rewards': []
        }
        
        # 创建保存目录
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 训练状态
        self.current_episode = 0
        self.total_steps = 0
        self.start_time = None
        
        LOGGER.info(f"训练器初始化完成: {self.__class__.__name__}")
        LOGGER.info(f"训练轮数: {episodes}, 保存目录: {save_dir}")

    @abstractmethod
    def train_episode(self, episode: int) -> Dict[str, Any]:
        """
        训练一个episode的抽象方法
        
        Args:
            episode: 当前episode编号
            
        Returns:
            包含训练指标的字典
        """
        pass

    def train(self) -> Dict[str, Any]:
        """
        执行完整训练过程
        
        Returns:
            训练结果统计
        """
        LOGGER.info(f"开始训练，共 {self.episodes} 轮")
        self.start_time = time.time()
        
        try:
            for episode in range(self.episodes):
                self.current_episode = episode
                
                # 训练一个episode
                episode_metrics = self.train_episode(episode)
                
                # 更新统计信息
                self._update_metrics(episode_metrics)
                
                # 定期评估
                if episode % self.eval_interval == 0 and episode > 0:
                    eval_metrics = self.evaluate(num_episodes=5)
                    self.training_metrics['eval_rewards'].append(eval_metrics['mean_reward'])
                
                # 定期保存模型
                if episode % self.save_interval == 0 and episode > 0:
                    self.save_model(episode)
                
                # 定期记录日志
                if episode % self.log_interval == 0:
                    self._log_progress(episode)
                    
        except KeyboardInterrupt:
            LOGGER.info("训练被用户中断")
        except Exception as e:
            LOGGER.error(f"训练过程中发生错误: {e}")
            raise
        finally:
            # 保存最终模型
            self.save_model(self.current_episode, is_final=True)
            
        # 训练完成统计
        training_time = time.time() - self.start_time
        LOGGER.info(f"训练完成！总用时: {training_time:.2f}秒")
        
        return self._get_training_summary()

    def evaluate(self, num_episodes: int = 10) -> Dict[str, Any]:
        """
        评估智能体性能
        
        Args:
            num_episodes: 评估轮数
            
        Returns:
            评估结果
        """
        LOGGER.info(f"开始评估，共 {num_episodes} 轮")
        
        eval_rewards = []
        eval_lengths = []
        
        for episode in range(num_episodes):
            obs = self.env.reset()
            episode_reward = 0
            episode_length = 0
            
            while not self.env.env_is_finished() and episode_length < self.max_episode_steps:
                # 使用智能体决策（不学习）
                action = self.agent.decision(obs)
                
                # 环境执行
                next_obs, reward, done, _, _ = self.env.step({'decisions': action})
                
                obs = next_obs
                episode_reward += sum(reward.values()) if isinstance(reward, dict) else reward
                episode_length += 1
            
            eval_rewards.append(episode_reward)
            eval_lengths.append(episode_length)
        
        eval_metrics = {
            'mean_reward': np.mean(eval_rewards),
            'std_reward': np.std(eval_rewards),
            'mean_length': np.mean(eval_lengths),
            'std_length': np.std(eval_lengths),
            'rewards': eval_rewards,
            'lengths': eval_lengths
        }
        
        LOGGER.info(f"评估完成 - 平均奖励: {eval_metrics['mean_reward']:.2f} ± {eval_metrics['std_reward']:.2f}")
        
        return eval_metrics

    def save_model(self, episode: int, is_final: bool = False) -> None:
        """
        保存模型
        
        Args:
            episode: 当前episode
            is_final: 是否为最终保存
        """
        if hasattr(self.agent, 'save_model'):
            suffix = "_final" if is_final else f"_ep{episode}"
            model_path = os.path.join(self.save_dir, f"model{suffix}.pkl")
            self.agent.save_model(model_path)
            LOGGER.info(f"模型已保存到: {model_path}")
        else:
            LOGGER.warning("智能体不支持模型保存功能")

    def load_model(self, model_path: str) -> None:
        """
        加载模型
        
        Args:
            model_path: 模型文件路径
        """
        if hasattr(self.agent, 'load_model'):
            self.agent.load_model(model_path)
            LOGGER.info(f"模型已从 {model_path} 加载")
        else:
            LOGGER.warning("智能体不支持模型加载功能")

    def _update_metrics(self, episode_metrics: Dict[str, Any]) -> None:
        """
        更新训练指标
        
        Args:
            episode_metrics: episode指标
        """
        for key, value in episode_metrics.items():
            if key in self.training_metrics:
                self.training_metrics[key].append(value)

    def _log_progress(self, episode: int) -> None:
        """
        记录训练进度
        
        Args:
            episode: 当前episode
        """
        if len(self.training_metrics['episode_rewards']) > 0:
            recent_rewards = self.training_metrics['episode_rewards'][-self.log_interval:]
            avg_reward = np.mean(recent_rewards)
            
            recent_lengths = self.training_metrics['episode_lengths'][-self.log_interval:]
            avg_length = np.mean(recent_lengths)
            
            LOGGER.info(f"Episode {episode} - 平均奖励: {avg_reward:.2f}, 平均长度: {avg_length:.2f}")

    def _get_training_summary(self) -> Dict[str, Any]:
        """
        获取训练总结
        
        Returns:
            训练总结统计
        """
        if not self.training_metrics['episode_rewards']:
            return {}
            
        summary = {
            'total_episodes': len(self.training_metrics['episode_rewards']),
            'total_steps': self.total_steps,
            'training_time': time.time() - self.start_time if self.start_time else 0,
            'final_avg_reward': np.mean(self.training_metrics['episode_rewards'][-10:]) if len(self.training_metrics['episode_rewards']) >= 10 else np.mean(self.training_metrics['episode_rewards']),
            'best_reward': np.max(self.training_metrics['episode_rewards']),
            'worst_reward': np.min(self.training_metrics['episode_rewards']),
            'avg_episode_length': np.mean(self.training_metrics['episode_lengths']) if self.training_metrics['episode_lengths'] else 0
        }
        
        return summary

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取当前训练指标
        
        Returns:
            训练指标字典
        """
        return self.training_metrics.copy()

    def reset_metrics(self) -> None:
        """
        重置训练指标
        """
        for key in self.training_metrics:
            self.training_metrics[key] = []
        self.current_episode = 0
        self.total_steps = 0
        self.start_time = None
