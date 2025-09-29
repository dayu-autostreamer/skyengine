'''
@Project ：tiangong 
@File    ：example_usage.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 21:24 

训练器使用示例
'''

from sky_executor.packet_factory.packet_factory.Trainer import (
    BaseTrainer, SimpleTrainer, DQNTrainer, PPOTrainer, 
    TrainerFactory, create_trainer
)


def example_simple_trainer():
    """简单训练器使用示例"""
    print("=== 简单训练器示例 ===")
    
    # 创建环境和智能体（这里需要根据实际情况实现）
    # env = PacketFactoryEnv(Agent)
    # Agent = YourAgent()
    
    # 创建简单训练器
    trainer = SimpleTrainer(
        env=None,  # 替换为实际环境
        agent=None,  # 替换为实际智能体
        episodes=100,
        save_dir="./models/simple",
        log_interval=10,
        learning_rate=0.001,
        gamma=0.99
    )
    
    # 开始训练
    # results = trainer.train()
    # print(f"训练结果: {results}")


def example_dqn_trainer():
    """DQN训练器使用示例"""
    print("=== DQN训练器示例 ===")
    
    trainer = DQNTrainer(
        env=None,  # 替换为实际环境
        agent=None,  # 替换为实际DQN智能体
        episodes=1000,
        save_dir="./models/dqn",
        batch_size=32,
        target_update_freq=100,
        epsilon_start=1.0,
        epsilon_end=0.01,
        epsilon_decay=0.995
    )
    
    # 开始训练
    # results = trainer.train()


def example_ppo_trainer():
    """PPO训练器使用示例"""
    print("=== PPO训练器示例 ===")
    
    trainer = PPOTrainer(
        env=None,  # 替换为实际环境
        agent=None,  # 替换为实际PPO智能体
        episodes=1000,
        save_dir="./models/ppo",
        update_epochs=4,
        clip_ratio=0.2,
        value_coef=0.5,
        entropy_coef=0.01
    )
    
    # 开始训练
    # results = trainer.train()


def example_factory_usage():
    """工厂模式使用示例"""
    print("=== 工厂模式示例 ===")
    
    # 查看可用的训练器类型
    available_trainers = TrainerFactory.get_available_trainers()
    print(f"可用的训练器类型: {available_trainers}")
    
    # 获取训练器信息
    for trainer_type in available_trainers:
        info = TrainerFactory.get_trainer_info(trainer_type)
        print(f"\n训练器类型: {trainer_type}")
        print(f"类名: {info['class']}")
        print(f"描述: {info['description']}")
        print(f"参数: {list(info['parameters'].keys())}")
    
    # 使用工厂创建训练器
    try:
        trainer = create_trainer(
            trainer_type='simple',
            env=None,  # 替换为实际环境
            agent=None,  # 替换为实际智能体
            episodes=100,
            save_dir="./models/factory"
        )
        print(f"\n成功创建训练器: {type(trainer).__name__}")
    except ValueError as e:
        print(f"创建训练器失败: {e}")


def example_custom_trainer():
    """自定义训练器示例"""
    print("=== 自定义训练器示例 ===")
    
    class CustomTrainer(BaseTrainer):
        """自定义训练器实现"""
        
        def __init__(self, env, agent, episodes=100, custom_param="default", **kwargs):
            super().__init__(env, agent, episodes, **kwargs)
            self.custom_param = custom_param
            print(f"自定义训练器初始化，参数: {custom_param}")
        
        def train_episode(self, episode: int):
            """实现自定义的训练逻辑"""
            print(f"自定义训练 Episode {episode}")
            
            # 这里实现你的自定义训练逻辑
            # ...
            
            return {
                'episode_rewards': 0.0,
                'episode_lengths': 0,
                'episode_times': 0.0,
                'losses': 0.0
            }
    
    # 注册自定义训练器
    TrainerFactory.register_trainer('custom', CustomTrainer)
    
    # 使用自定义训练器
    trainer = create_trainer(
        trainer_type='custom',
        env=None,
        agent=None,
        custom_param="my_value",
        episodes=50
    )
    
    print(f"自定义训练器创建成功: {type(trainer).__name__}")


def example_training_workflow():
    """完整训练工作流示例"""
    print("=== 完整训练工作流示例 ===")
    
    # 1. 创建环境和智能体
    # env = PacketFactoryEnv(Agent)
    # Agent = YourAgent()
    
    # 2. 创建训练器
    trainer = SimpleTrainer(
        env=None,  # 替换为实际环境
        agent=None,  # 替换为实际智能体
        episodes=200,
        save_dir="./models/workflow",
        log_interval=20,
        save_interval=50,
        eval_interval=25
    )
    
    # 3. 开始训练
    print("开始训练...")
    # results = trainer.train()
    
    # 4. 查看训练结果
    # print(f"训练完成！结果: {results}")
    
    # 5. 评估模型
    print("评估模型...")
    # eval_results = trainer.evaluate(num_episodes=10)
    # print(f"评估结果: {eval_results}")
    
    # 6. 保存最终模型
    # trainer.save_model(episode=200, is_final=True)
    
    # 7. 加载模型进行推理
    # trainer.load_model("./models/workflow/model_final.pkl")


if __name__ == "__main__":
    print("训练器模块使用示例")
    print("=" * 50)
    
    example_simple_trainer()
    print()
    
    example_dqn_trainer()
    print()
    
    example_ppo_trainer()
    print()
    
    example_factory_usage()
    print()
    
    example_custom_trainer()
    print()
    
    example_training_workflow()
    
    print("\n示例完成！")
