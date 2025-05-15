from abc import ABC, abstractmethod

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

    def set_context(self, context):
        """设置上下文"""
        self.context = context

    @abstractmethod
    def step(self, *args, **kwargs):
        """Agent 的主要逻辑，每次环境更新时调用"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.agent_id} name={self.name}>"