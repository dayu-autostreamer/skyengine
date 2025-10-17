'''
@Project ：tiangong 
@File    ：BaselineAgent.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/21 11:51 
'''
# 一定会完成任务的基线策略,用于给其他agent保底


from abc import ABC, abstractmethod

# Agent:
# input: 状态
# output: [(Operation, AGV, Machine), ...] （job可以混合）


from sky_executor.utils.registry import register_component

@register_component("packet_factory.BaselineAgent")
class BaseAgent(ABC):
    def __init__(self, name=None, agent_id=None, context=None):
        """
        通用智能体基类
        :param name: 智能体名称
        :param agent_id: 智能体ID或唯一标识
        :param context: 可选的上下文或环境句柄
        """
        self.name = name or self.__class__.__name__
        self.agent_id = agent_id
        self.context = context
        self.alive = True  # 是否在线
        self.turns = 0  # 存活轮次


    def is_alive(self):
        return self.alive

    @abstractmethod
    def reward(self, *args, **kwargs):
        """Agent 计算自身的reward"""
        pass

    @abstractmethod
    def is_finish(self):
        """判断任务是否完成"""
        pass

    @abstractmethod
    def sample(self, *args, **kwargs):
        """Agent 推理采样"""
        pass

    @abstractmethod
    def before_sample(self, *args, **kwargs):
        pass

    @abstractmethod
    def after_sample(self, *args, **kwargs):
        pass

    @abstractmethod
    def decision(self, *args, **kwargs):
        """Agent 推理采样"""
        self.before_sample(*args, **kwargs)
        self.sample(*args, **kwargs)
        self.after_sample(*args, **kwargs)

    @abstractmethod
    def train(self, *args, **kwargs):
        """Agent 训练"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.agent_id} name={self.name}>"
