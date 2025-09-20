'''
@Project ：tiangong 
@File    ：test_trainer.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 21:24 

训练器模块测试
'''

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, MagicMock, patch
import numpy as np
import sys
import time

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from tiangong_simulator.packet_factory.Trainer import (
    BaseTrainer, SimpleTrainer, DQNTrainer, PPOTrainer,
    TrainerFactory, create_trainer
)


class MockAgent:
    """模拟智能体类用于测试"""
    
    def __init__(self, agent_id="test_agent", name="TestAgent"):
        self.agent_id = agent_id
        self.name = name
        self.alive = True
        self.turns = 0
        self.training_calls = 0
        self.decision_calls = 0
        
    def is_alive(self):
        return self.alive
    
    def reward(self, *args, **kwargs):
        return np.random.uniform(-1, 1)
    
    def is_finish(self):
        return self.turns > 10
    
    def sample(self, *args, **kwargs):
        return np.random.choice([0, 1, 2])
    
    def before_sample(self, *args, **kwargs):
        pass
    
    def after_sample(self, *args, **kwargs):
        pass
    
    def decision(self, obs):
        """决策方法"""
        self.decision_calls += 1
        return np.random.choice([0, 1, 2])
    
    def train(self, obs, action, reward, next_obs, done):
        """训练方法"""
        self.training_calls += 1
        return np.random.uniform(0, 1)  # 模拟损失值
    
    def save_model(self, path):
        """保存模型"""
        with open(path, 'w') as f:
            f.write(f"model_{self.name}")
    
    def load_model(self, path):
        """加载模型"""
        if os.path.exists(path):
            return True
        return False


class MockEnvironment:
    """模拟环境类用于测试"""
    
    def __init__(self):
        self.step_count = 0
        self.max_steps = 5
        self.finished = False
        
    def reset(self):
        """重置环境"""
        self.step_count = 0
        self.finished = False
        return {"obs": np.random.random(10)}
    
    def step(self, action):
        """执行一步"""
        self.step_count += 1
        if self.step_count >= self.max_steps:
            self.finished = True
        
        obs = {"obs": np.random.random(10)}
        reward = {"agent": np.random.uniform(-1, 1)}
        done = self.finished
        info = {}
        
        return obs, reward, done, info, {}
    
    def env_is_finished(self):
        """检查环境是否结束"""
        return self.finished


class TestBaseTrainer(unittest.TestCase):
    """测试BaseTrainer基类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.agent = MockAgent()
        self.env = MockEnvironment()
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """测试初始化"""
        trainer = SimpleTrainer(
            env=self.env,
            agent=self.agent,
            episodes=10,
            save_dir=self.temp_dir
        )
        
        self.assertEqual(trainer.episodes, 10)
        self.assertEqual(trainer.save_dir, self.temp_dir)
        self.assertEqual(trainer.current_episode, 0)
        self.assertEqual(trainer.total_steps, 0)
        self.assertIsNotNone(trainer.training_metrics)
    
    def test_metrics_initialization(self):
        """测试指标初始化"""
        trainer = SimpleTrainer(self.env, self.agent)
        
        expected_metrics = ['episode_rewards', 'episode_lengths', 
                          'episode_times', 'losses', 'eval_rewards']
        
        for metric in expected_metrics:
            self.assertIn(metric, trainer.training_metrics)
            self.assertEqual(len(trainer.training_metrics[metric]), 0)
    
    def test_save_model(self):
        """测试模型保存"""
        trainer = SimpleTrainer(self.env, self.agent, save_dir=self.temp_dir)
        
        # 测试保存模型
        trainer.save_model(episode=1)
        
        # 检查文件是否创建
        expected_path = os.path.join(self.temp_dir, "model_ep1.pkl")
        self.assertTrue(os.path.exists(expected_path))
    
    def test_load_model(self):
        """测试模型加载"""
        trainer = SimpleTrainer(self.env, self.agent, save_dir=self.temp_dir)
        
        # 先保存一个模型
        model_path = os.path.join(self.temp_dir, "test_model.pkl")
        trainer.save_model(episode=1)
        
        # 测试加载模型
        trainer.load_model(model_path)
        # 由于MockAgent的load_model总是返回True，这里主要测试方法调用
    
    def test_evaluate(self):
        """测试评估功能"""
        trainer = SimpleTrainer(self.env, self.agent, max_episode_steps=3)
        
        # 执行评估
        eval_results = trainer.evaluate(num_episodes=2)
        
        # 检查评估结果
        self.assertIn('mean_reward', eval_results)
        self.assertIn('std_reward', eval_results)
        self.assertIn('mean_length', eval_results)
        self.assertIn('std_length', eval_results)
        self.assertIn('rewards', eval_results)
        self.assertIn('lengths', eval_results)
        
        self.assertEqual(len(eval_results['rewards']), 2)
        self.assertEqual(len(eval_results['lengths']), 2)
    
    def test_get_metrics(self):
        """测试获取指标"""
        trainer = SimpleTrainer(self.env, self.agent)
        
        # 添加一些测试数据
        trainer.training_metrics['episode_rewards'] = [1.0, 2.0, 3.0]
        trainer.training_metrics['episode_lengths'] = [10, 20, 30]
        
        metrics = trainer.get_metrics()
        
        self.assertEqual(metrics['episode_rewards'], [1.0, 2.0, 3.0])
        self.assertEqual(metrics['episode_lengths'], [10, 20, 30])
        self.assertIsNot(trainer.training_metrics, metrics)  # 应该是副本
    
    def test_reset_metrics(self):
        """测试重置指标"""
        trainer = SimpleTrainer(self.env, self.agent)
        
        # 添加一些数据
        trainer.training_metrics['episode_rewards'] = [1.0, 2.0, 3.0]
        trainer.current_episode = 5
        trainer.total_steps = 100
        
        # 重置指标
        trainer.reset_metrics()
        
        # 检查是否重置
        for key in trainer.training_metrics:
            self.assertEqual(len(trainer.training_metrics[key]), 0)
        self.assertEqual(trainer.current_episode, 0)
        self.assertEqual(trainer.total_steps, 0)


class TestSimpleTrainer(unittest.TestCase):
    """测试SimpleTrainer"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.agent = MockAgent()
        self.env = MockEnvironment()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """测试SimpleTrainer初始化"""
        trainer = SimpleTrainer(
            env=self.env,
            agent=self.agent,
            episodes=50,
            learning_rate=0.01,
            gamma=0.95
        )
        
        self.assertEqual(trainer.learning_rate, 0.01)
        self.assertEqual(trainer.gamma, 0.95)
        self.assertEqual(trainer.episodes, 50)
    
    def test_train_episode(self):
        """测试训练一个episode"""
        trainer = SimpleTrainer(self.env, self.agent, max_episode_steps=3)
        
        # 训练一个episode
        metrics = trainer.train_episode(episode=0)
        
        # 检查返回的指标
        self.assertIn('episode_rewards', metrics)
        self.assertIn('episode_lengths', metrics)
        self.assertIn('episode_times', metrics)
        self.assertIn('losses', metrics)
        
        # 检查智能体是否被调用
        self.assertGreater(self.agent.decision_calls, 0)
        self.assertGreater(self.agent.training_calls, 0)
    
    def test_full_training(self):
        """测试完整训练过程"""
        trainer = SimpleTrainer(
            env=self.env,
            agent=self.agent,
            episodes=3,
            max_episode_steps=2,
            save_dir=self.temp_dir
        )
        
        # 执行训练
        results = trainer.train()
        
        # 检查训练结果
        self.assertIn('total_episodes', results)
        self.assertIn('total_steps', results)
        self.assertIn('training_time', results)
        self.assertIn('final_avg_reward', results)
        
        self.assertEqual(results['total_episodes'], 3)
        self.assertGreater(results['total_steps'], 0)


class TestDQNTrainer(unittest.TestCase):
    """测试DQNTrainer"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.agent = MockAgent()
        self.env = MockEnvironment()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """测试DQNTrainer初始化"""
        trainer = DQNTrainer(
            env=self.env,
            agent=self.agent,
            episodes=100,
            batch_size=16,
            target_update_freq=50,
            epsilon_start=0.9,
            epsilon_end=0.05,
            epsilon_decay=0.99
        )
        
        self.assertEqual(trainer.batch_size, 16)
        self.assertEqual(trainer.target_update_freq, 50)
        self.assertEqual(trainer.epsilon_start, 0.9)
        self.assertEqual(trainer.epsilon_end, 0.05)
        self.assertEqual(trainer.epsilon_decay, 0.99)
        self.assertEqual(trainer.current_epsilon, 0.9)
    
    def test_epsilon_decay(self):
        """测试epsilon衰减"""
        trainer = DQNTrainer(self.env, self.agent, max_episode_steps=2)
        
        initial_epsilon = trainer.current_epsilon
        
        # 训练一个episode
        trainer.train_episode(episode=0)
        
        # 检查epsilon是否衰减
        self.assertLess(trainer.current_epsilon, initial_epsilon)
    
    def test_train_episode(self):
        """测试DQN训练episode"""
        trainer = DQNTrainer(self.env, self.agent, max_episode_steps=3)
        
        # 训练一个episode
        metrics = trainer.train_episode(episode=0)
        
        # 检查指标
        self.assertIn('episode_rewards', metrics)
        self.assertIn('episode_lengths', metrics)
        self.assertIn('episode_times', metrics)
        self.assertIn('losses', metrics)


class TestPPOTrainer(unittest.TestCase):
    """测试PPOTrainer"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.agent = MockAgent()
        self.env = MockEnvironment()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """测试PPOTrainer初始化"""
        trainer = PPOTrainer(
            env=self.env,
            agent=self.agent,
            episodes=100,
            update_epochs=3,
            clip_ratio=0.1,
            value_coef=0.3,
            entropy_coef=0.02
        )
        
        self.assertEqual(trainer.update_epochs, 3)
        self.assertEqual(trainer.clip_ratio, 0.1)
        self.assertEqual(trainer.value_coef, 0.3)
        self.assertEqual(trainer.entropy_coef, 0.02)
        self.assertEqual(trainer.update_frequency, 10)
    
    def test_episode_buffer(self):
        """测试episode缓冲区"""
        trainer = PPOTrainer(self.env, self.agent, max_episode_steps=2)
        
        # 训练几个episode
        trainer.train_episode(episode=0)
        trainer.train_episode(episode=1)
        
        # 检查缓冲区是否有数据
        self.assertGreater(len(trainer.episode_buffer), 0)
    
    def test_train_episode(self):
        """测试PPO训练episode"""
        trainer = PPOTrainer(self.env, self.agent, max_episode_steps=3)
        
        # 训练一个episode
        metrics = trainer.train_episode(episode=0)
        
        # 检查指标
        self.assertIn('episode_rewards', metrics)
        self.assertIn('episode_lengths', metrics)
        self.assertIn('episode_times', metrics)
        self.assertIn('losses', metrics)


class TestTrainerFactory(unittest.TestCase):
    """测试TrainerFactory"""
    
    def setUp(self):
        self.agent = MockAgent()
        self.env = MockEnvironment()
    
    def test_get_available_trainers(self):
        """测试获取可用训练器"""
        trainers = TrainerFactory.get_available_trainers()
        
        expected_trainers = ['simple', 'dqn', 'ppo']
        for trainer in expected_trainers:
            self.assertIn(trainer, trainers)
    
    def test_create_trainer(self):
        """测试创建训练器"""
        # 测试创建简单训练器
        trainer = TrainerFactory.create_trainer(
            'simple', self.env, self.agent, episodes=10
        )
        self.assertIsInstance(trainer, SimpleTrainer)
        
        # 测试创建DQN训练器
        trainer = TrainerFactory.create_trainer(
            'dqn', self.env, self.agent, episodes=10
        )
        self.assertIsInstance(trainer, DQNTrainer)
        
        # 测试创建PPO训练器
        trainer = TrainerFactory.create_trainer(
            'ppo', self.env, self.agent, episodes=10
        )
        self.assertIsInstance(trainer, PPOTrainer)
    
    def test_create_invalid_trainer(self):
        """测试创建无效训练器"""
        with self.assertRaises(ValueError):
            TrainerFactory.create_trainer('invalid', self.env, self.agent)
    
    def test_get_trainer_info(self):
        """测试获取训练器信息"""
        info = TrainerFactory.get_trainer_info('simple')
        
        self.assertIn('name', info)
        self.assertIn('class', info)
        self.assertIn('description', info)
        self.assertIn('parameters', info)
        
        self.assertEqual(info['name'], 'simple')
        self.assertEqual(info['class'], 'SimpleTrainer')
    
    def test_register_custom_trainer(self):
        """测试注册自定义训练器"""
        class CustomTrainer(BaseTrainer):
            def train_episode(self, episode):
                return {'episode_rewards': 0, 'episode_lengths': 0, 
                       'episode_times': 0, 'losses': 0}
        
        # 注册自定义训练器
        TrainerFactory.register_trainer('custom', CustomTrainer)
        
        # 检查是否注册成功
        trainers = TrainerFactory.get_available_trainers()
        self.assertIn('custom', trainers)
        
        # 测试创建自定义训练器
        trainer = TrainerFactory.create_trainer('custom', self.env, self.agent)
        self.assertIsInstance(trainer, CustomTrainer)
    
    def test_register_invalid_trainer(self):
        """测试注册无效训练器"""
        class InvalidTrainer:
            pass
        
        with self.assertRaises(ValueError):
            TrainerFactory.register_trainer('invalid', InvalidTrainer)


class TestCreateTrainerFunction(unittest.TestCase):
    """测试create_trainer便捷函数"""
    
    def setUp(self):
        self.agent = MockAgent()
        self.env = MockEnvironment()
    
    def test_create_trainer_function(self):
        """测试create_trainer函数"""
        trainer = create_trainer('simple', self.env, self.agent, episodes=5)
        self.assertIsInstance(trainer, SimpleTrainer)
        self.assertEqual(trainer.episodes, 5)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.agent = MockAgent()
        self.env = MockEnvironment()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_training_workflow(self):
        """测试完整训练工作流"""
        # 创建训练器
        trainer = create_trainer(
            'simple',
            self.env,
            self.agent,
            episodes=3,
            save_dir=self.temp_dir,
            log_interval=1,
            save_interval=2
        )
        
        # 执行训练
        results = trainer.train()
        
        # 检查训练结果
        self.assertIsInstance(results, dict)
        self.assertIn('total_episodes', results)
        self.assertEqual(results['total_episodes'], 3)
        
        # 检查模型是否保存
        model_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.pkl')]
        self.assertGreater(len(model_files), 0)
        
        # 测试评估
        eval_results = trainer.evaluate(num_episodes=2)
        self.assertIn('mean_reward', eval_results)
        self.assertEqual(len(eval_results['rewards']), 2)
    
    def test_metrics_tracking(self):
        """测试指标跟踪"""
        trainer = SimpleTrainer(self.env, self.agent, episodes=2, max_episode_steps=2)
        
        # 训练
        trainer.train()
        
        # 检查指标
        metrics = trainer.get_metrics()
        
        self.assertEqual(len(metrics['episode_rewards']), 2)
        self.assertEqual(len(metrics['episode_lengths']), 2)
        self.assertEqual(len(metrics['episode_times']), 2)
        self.assertEqual(len(metrics['losses']), 2)
        
        # 检查指标值类型
        for reward in metrics['episode_rewards']:
            self.assertIsInstance(reward, (int, float))
        
        for length in metrics['episode_lengths']:
            self.assertIsInstance(length, int)
            self.assertGreaterEqual(length, 0)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
