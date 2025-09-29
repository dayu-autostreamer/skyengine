'''
@Project ：tiangong 
@File    ：test_trainer_performance.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 21:24 

训练器性能测试
'''

import unittest
import time
import tempfile
import os
import shutil
import sys
import numpy as np

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from sky_executor.packet_factory.packet_factory.Trainer import (
    SimpleTrainer, DQNTrainer, PPOTrainer
)


class MockAgent:
    """高性能模拟智能体"""
    
    def __init__(self, agent_id="perf_agent", name="PerfAgent"):
        self.agent_id = agent_id
        self.name = name
        self.alive = True
        self.turns = 0
        
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
        return np.random.choice([0, 1, 2])
    
    def train(self, obs, action, reward, next_obs, done):
        return np.random.uniform(0, 1)
    
    def save_model(self, path):
        with open(path, 'w') as f:
            f.write(f"model_{self.name}")
    
    def load_model(self, path):
        return os.path.exists(path)


class MockEnvironment:
    """高性能模拟环境"""
    
    def __init__(self, max_steps=10):
        self.step_count = 0
        self.max_steps = max_steps
        self.finished = False
        
    def reset(self):
        self.step_count = 0
        self.finished = False
        return {"obs": np.random.random(10)}
    
    def step(self, action):
        self.step_count += 1
        if self.step_count >= self.max_steps:
            self.finished = True
        
        obs = {"obs": np.random.random(10)}
        reward = {"Agent": np.random.uniform(-1, 1)}
        done = self.finished
        info = {}
        
        return obs, reward, done, info, {}
    
    def env_is_finished(self):
        return self.finished


class TestTrainerPerformance(unittest.TestCase):
    """训练器性能测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.agent = MockAgent()
        self.env = MockEnvironment(max_steps=5)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_simple_trainer_performance(self):
        """测试SimpleTrainer性能"""
        print("\n测试SimpleTrainer性能...")
        
        trainer = SimpleTrainer(
            env=self.env,
            agent=self.agent,
            episodes=100,
            max_episode_steps=5,
            save_dir=self.temp_dir
        )
        
        start_time = time.time()
        results = trainer.train()
        end_time = time.time()
        
        training_time = end_time - start_time
        episodes_per_second = 100 / training_time
        
        print(f"SimpleTrainer性能:")
        print(f"  训练时间: {training_time:.2f}秒")
        print(f"  每秒episodes: {episodes_per_second:.2f}")
        print(f"  总步数: {results['total_steps']}")
        
        # 性能断言
        self.assertLess(training_time, 10.0)  # 应该在10秒内完成
        self.assertGreater(episodes_per_second, 10.0)  # 每秒至少10个episodes
    
    def test_dqn_trainer_performance(self):
        """测试DQNTrainer性能"""
        print("\n测试DQNTrainer性能...")
        
        trainer = DQNTrainer(
            env=self.env,
            agent=self.agent,
            episodes=50,
            max_episode_steps=5,
            save_dir=self.temp_dir,
            batch_size=16
        )
        
        start_time = time.time()
        results = trainer.train()
        end_time = time.time()
        
        training_time = end_time - start_time
        episodes_per_second = 50 / training_time
        
        print(f"DQNTrainer性能:")
        print(f"  训练时间: {training_time:.2f}秒")
        print(f"  每秒episodes: {episodes_per_second:.2f}")
        print(f"  总步数: {results['total_steps']}")
        
        # 性能断言
        self.assertLess(training_time, 15.0)  # 应该在15秒内完成
        self.assertGreater(episodes_per_second, 3.0)  # 每秒至少3个episodes
    
    def test_ppo_trainer_performance(self):
        """测试PPOTrainer性能"""
        print("\n测试PPOTrainer性能...")
        
        trainer = PPOTrainer(
            env=self.env,
            agent=self.agent,
            episodes=50,
            max_episode_steps=5,
            save_dir=self.temp_dir,
            update_frequency=5
        )
        
        start_time = time.time()
        results = trainer.train()
        end_time = time.time()
        
        training_time = end_time - start_time
        episodes_per_second = 50 / training_time
        
        print(f"PPOTrainer性能:")
        print(f"  训练时间: {training_time:.2f}秒")
        print(f"  每秒episodes: {episodes_per_second:.2f}")
        print(f"  总步数: {results['total_steps']}")
        
        # 性能断言
        self.assertLess(training_time, 20.0)  # 应该在20秒内完成
        self.assertGreater(episodes_per_second, 2.5)  # 每秒至少2.5个episodes
    
    def test_memory_usage(self):
        """测试内存使用"""
        print("\n测试内存使用...")
        
        import psutil
        import gc
        
        # 获取初始内存
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 创建多个训练器
        trainers = []
        for i in range(10):
            trainer = SimpleTrainer(
                env=MockEnvironment(max_steps=3),
                agent=MockAgent(f"agent_{i}"),
                episodes=10,
                max_episode_steps=3
            )
            trainers.append(trainer)
        
        # 获取创建后的内存
        after_creation_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 训练一个训练器
        trainers[0].train()
        
        # 获取训练后的内存
        after_training_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 清理
        del trainers
        gc.collect()
        
        # 获取清理后的内存
        after_cleanup_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = after_creation_memory - initial_memory
        training_memory_increase = after_training_memory - after_creation_memory
        
        print(f"内存使用:")
        print(f"  初始内存: {initial_memory:.2f} MB")
        print(f"  创建后内存: {after_creation_memory:.2f} MB")
        print(f"  训练后内存: {after_training_memory:.2f} MB")
        print(f"  清理后内存: {after_cleanup_memory:.2f} MB")
        print(f"  创建增加: {memory_increase:.2f} MB")
        print(f"  训练增加: {training_memory_increase:.2f} MB")
        
        # 内存使用断言
        self.assertLess(memory_increase, 100.0)  # 创建不应该增加太多内存
        self.assertLess(training_memory_increase, 50.0)  # 训练不应该增加太多内存
    
    def test_concurrent_training(self):
        """测试并发训练"""
        print("\n测试并发训练...")
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def train_worker(trainer_id):
            """训练工作线程"""
            try:
                trainer = SimpleTrainer(
                    env=MockEnvironment(max_steps=3),
                    agent=MockAgent(f"agent_{trainer_id}"),
                    episodes=5,
                    max_episode_steps=3
                )
                
                start_time = time.time()
                results = trainer.train()
                end_time = time.time()
                
                results_queue.put({
                    'trainer_id': trainer_id,
                    'success': True,
                    'training_time': end_time - start_time,
                    'total_steps': results['total_steps']
                })
            except Exception as e:
                results_queue.put({
                    'trainer_id': trainer_id,
                    'success': False,
                    'error': str(e)
                })
        
        # 创建多个训练线程
        threads = []
        num_threads = 3
        
        start_time = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(target=train_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 收集结果
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        print(f"并发训练结果:")
        print(f"  线程数: {num_threads}")
        print(f"  总时间: {total_time:.2f}秒")
        print(f"  成功数: {sum(1 for r in results if r['success'])}")
        
        for result in results:
            if result['success']:
                print(f"  训练器{result['trainer_id']}: {result['training_time']:.2f}秒, {result['total_steps']}步")
            else:
                print(f"  训练器{result['trainer_id']}: 失败 - {result['error']}")
        
        # 并发训练断言
        self.assertEqual(len(results), num_threads)
        self.assertTrue(all(r['success'] for r in results))
        self.assertLess(total_time, 30.0)  # 并发训练应该在30秒内完成
    
    def test_large_scale_training(self):
        """测试大规模训练"""
        print("\n测试大规模训练...")
        
        # 创建大规模训练器
        trainer = SimpleTrainer(
            env=MockEnvironment(max_steps=10),
            agent=MockAgent(),
            episodes=1000,
            max_episode_steps=10,
            save_dir=self.temp_dir,
            log_interval=100,
            save_interval=200
        )
        
        start_time = time.time()
        results = trainer.train()
        end_time = time.time()
        
        training_time = end_time - start_time
        episodes_per_second = 1000 / training_time
        
        print(f"大规模训练结果:")
        print(f"  Episodes: 1000")
        print(f"  训练时间: {training_time:.2f}秒")
        print(f"  每秒episodes: {episodes_per_second:.2f}")
        print(f"  总步数: {results['total_steps']}")
        print(f"  平均奖励: {results['final_avg_reward']:.4f}")
        
        # 大规模训练断言
        self.assertEqual(results['total_episodes'], 1000)
        self.assertGreater(results['total_steps'], 0)
        self.assertLess(training_time, 60.0)  # 应该在60秒内完成
        self.assertGreater(episodes_per_second, 15.0)  # 每秒至少15个episodes


if __name__ == '__main__':
    # 运行性能测试
    print("开始训练器性能测试")
    print("=" * 60)
    
    unittest.main(verbosity=2)
