'''
@Project ：tiangong 
@File    ：TrainerFactory.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 21:24 
'''

from typing import Dict, Any, Type
from tiangong_logs.logger import LOGGER

from .BaseTrainer import BaseTrainer
from .SimpleTrainer import SimpleTrainer, DQNTrainer, PPOTrainer


class TrainerFactory:
    """
    训练器工厂类
    用于创建不同类型的训练器
    """
    
    # 注册的训练器类型
    _trainers = {
        'simple': SimpleTrainer,
        'dqn': DQNTrainer,
        'ppo': PPOTrainer,
    }
    
    @classmethod
    def create_trainer(cls, 
                      trainer_type: str, 
                      env, 
                      agent, 
                      **kwargs) -> BaseTrainer:
        """
        创建训练器实例
        
        Args:
            trainer_type: 训练器类型 ('simple', 'dqn', 'ppo')
            env: 训练环境
            agent: 智能体
            **kwargs: 其他参数
            
        Returns:
            训练器实例
            
        Raises:
            ValueError: 不支持的训练器类型
        """
        if trainer_type not in cls._trainers:
            available_types = list(cls._trainers.keys())
            raise ValueError(f"不支持的训练器类型: {trainer_type}. "
                           f"可用类型: {available_types}")
        
        trainer_class = cls._trainers[trainer_type]
        LOGGER.info(f"创建训练器: {trainer_type} -> {trainer_class.__name__}")
        
        return trainer_class(env, agent, **kwargs)
    
    @classmethod
    def register_trainer(cls, name: str, trainer_class: Type[BaseTrainer]) -> None:
        """
        注册新的训练器类型
        
        Args:
            name: 训练器名称
            trainer_class: 训练器类
        """
        if not issubclass(trainer_class, BaseTrainer):
            raise ValueError(f"训练器类必须继承自BaseTrainer: {trainer_class}")
        
        cls._trainers[name] = trainer_class
        LOGGER.info(f"注册训练器: {name} -> {trainer_class.__name__}")
    
    @classmethod
    def get_available_trainers(cls) -> list:
        """
        获取可用的训练器类型列表
        
        Returns:
            训练器类型列表
        """
        return list(cls._trainers.keys())
    
    @classmethod
    def get_trainer_info(cls, trainer_type: str) -> Dict[str, Any]:
        """
        获取训练器信息
        
        Args:
            trainer_type: 训练器类型
            
        Returns:
            训练器信息字典
        """
        if trainer_type not in cls._trainers:
            raise ValueError(f"不支持的训练器类型: {trainer_type}")
        
        trainer_class = cls._trainers[trainer_type]
        
        return {
            'name': trainer_type,
            'class': trainer_class.__name__,
            'description': trainer_class.__doc__ or "无描述",
            'parameters': cls._get_trainer_parameters(trainer_class)
        }
    
    @classmethod
    def _get_trainer_parameters(cls, trainer_class: Type[BaseTrainer]) -> Dict[str, Any]:
        """
        获取训练器参数信息
        
        Args:
            trainer_class: 训练器类
            
        Returns:
            参数信息字典
        """
        import inspect
        
        sig = inspect.signature(trainer_class.__init__)
        parameters = {}
        
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
                
            param_info = {
                'type': param.annotation if param.annotation != inspect.Parameter.empty else 'Any',
                'default': param.default if param.default != inspect.Parameter.empty else None,
                'required': param.default == inspect.Parameter.empty
            }
            parameters[name] = param_info
        
        return parameters


def create_trainer(trainer_type: str, env, agent, **kwargs) -> BaseTrainer:
    """
    便捷函数：创建训练器
    
    Args:
        trainer_type: 训练器类型
        env: 训练环境
        agent: 智能体
        **kwargs: 其他参数
        
    Returns:
        训练器实例
    """
    return TrainerFactory.create_trainer(trainer_type, env, agent, **kwargs)
