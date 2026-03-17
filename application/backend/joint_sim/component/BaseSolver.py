'''
@Project ：SkyEngine 
@File    ：BaseSolver.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 22:35
'''
from abc import ABC, abstractmethod

class BaseSolver(ABC):
    @abstractmethod
    def solve(self, problem_instance, **kwargs):
        """
        求解接口
        Args:
            problem_instance: 调度或路由问题实例
            kwargs: 可选的求解参数
        Returns:
            result: 标准化结构，包含调度/路径/指标信息
        """
        pass

    @abstractmethod
    def compute_metrics(self, result):
        """计算性能指标"""
        pass
