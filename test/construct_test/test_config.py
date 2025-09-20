'''
@Project ：tiangong 
@File    ：test_config.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 21:24 

训练器测试配置
'''

import os
import tempfile
from typing import Dict, Any

class TestConfig:
    """测试配置类"""
    
    # 基础配置
    BASE_CONFIG = {
        'episodes': 10,
        'max_episode_steps': 5,
        'log_interval': 1,
        'save_interval': 5,
        'eval_interval': 3
    }
    
    # 性能测试配置
    PERFORMANCE_CONFIG = {
        'episodes': 100,
        'max_episode_steps': 10,
        'log_interval': 20,
        'save_interval': 50,
        'eval_interval': 25
    }
    
    # 大规模测试配置
    LARGE_SCALE_CONFIG = {
        'episodes': 1000,
        'max_episode_steps': 20,
        'log_interval': 100,
        'save_interval': 200,
        'eval_interval': 100
    }
    
    # 训练器特定配置
    TRAINER_CONFIGS = {
        'simple': {
            'learning_rate': 0.001,
            'gamma': 0.99
        },
        'dqn': {
            'batch_size': 32,
            'target_update_freq': 100,
            'epsilon_start': 1.0,
            'epsilon_end': 0.01,
            'epsilon_decay': 0.995
        },
        'ppo': {
            'update_epochs': 4,
            'clip_ratio': 0.2,
            'value_coef': 0.5,
            'entropy_coef': 0.01,
            'update_frequency': 10
        }
    }
    
    @classmethod
    def get_test_config(cls, test_type: str = 'base') -> Dict[str, Any]:
        """
        获取测试配置
        
        Args:
            test_type: 测试类型 ('base', 'performance', 'large_scale')
            
        Returns:
            测试配置字典
        """
        configs = {
            'base': cls.BASE_CONFIG,
            'performance': cls.PERFORMANCE_CONFIG,
            'large_scale': cls.LARGE_SCALE_CONFIG
        }
        
        if test_type not in configs:
            raise ValueError(f"不支持的测试类型: {test_type}")
        
        return configs[test_type].copy()
    
    @classmethod
    def get_trainer_config(cls, trainer_type: str) -> Dict[str, Any]:
        """
        获取训练器特定配置
        
        Args:
            trainer_type: 训练器类型
            
        Returns:
            训练器配置字典
        """
        if trainer_type not in cls.TRAINER_CONFIGS:
            raise ValueError(f"不支持的训练器类型: {trainer_type}")
        
        return cls.TRAINER_CONFIGS[trainer_type].copy()
    
    @classmethod
    def get_full_config(cls, trainer_type: str, test_type: str = 'base') -> Dict[str, Any]:
        """
        获取完整配置
        
        Args:
            trainer_type: 训练器类型
            test_type: 测试类型
            
        Returns:
            完整配置字典
        """
        base_config = cls.get_test_config(test_type)
        trainer_config = cls.get_trainer_config(trainer_type)
        
        # 合并配置
        full_config = {**base_config, **trainer_config}
        
        # 添加通用配置
        full_config.update({
            'save_dir': tempfile.mkdtemp(prefix=f"test_{trainer_type}_"),
            'trainer_type': trainer_type,
            'test_type': test_type
        })
        
        return full_config
    
    @classmethod
    def cleanup_temp_dirs(cls, configs: list):
        """
        清理临时目录
        
        Args:
            configs: 配置列表
        """
        import shutil
        
        for config in configs:
            save_dir = config.get('save_dir')
            if save_dir and os.path.exists(save_dir):
                try:
                    shutil.rmtree(save_dir)
                except Exception as e:
                    print(f"清理目录失败: {save_dir}, 错误: {e}")


# 测试用例配置
TEST_CASES = [
    {
        'name': 'basic_functionality',
        'description': '基本功能测试',
        'trainer_types': ['simple', 'dqn', 'ppo'],
        'test_type': 'base',
        'timeout': 30
    },
    {
        'name': 'performance_test',
        'description': '性能测试',
        'trainer_types': ['simple', 'dqn', 'ppo'],
        'test_type': 'performance',
        'timeout': 60
    },
    {
        'name': 'memory_test',
        'description': '内存使用测试',
        'trainer_types': ['simple'],
        'test_type': 'base',
        'timeout': 30
    },
    {
        'name': 'concurrent_test',
        'description': '并发测试',
        'trainer_types': ['simple'],
        'test_type': 'base',
        'timeout': 45
    },
    {
        'name': 'large_scale_test',
        'description': '大规模测试',
        'trainer_types': ['simple'],
        'test_type': 'large_scale',
        'timeout': 120
    }
]

# 测试环境配置
TEST_ENVIRONMENT_CONFIG = {
    'max_steps': 10,
    'observation_size': 10,
    'action_size': 3,
    'reward_range': (-1, 1)
}

# 模拟智能体配置
MOCK_AGENT_CONFIG = {
    'agent_id': 'test_agent',
    'name': 'TestAgent',
    'alive': True,
    'turns': 0
}
