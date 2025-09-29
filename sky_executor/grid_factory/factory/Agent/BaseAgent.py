import time
from abc import ABC, abstractmethod
from sky_executor.grid_factory.factory.grid_factory_env.Utils.env_const import ObsType

# Agent:
# input: 智能体自己观察的状态
# output: 智能体自己的动作中的一个


from sky_executor.utils.registry import register_component


@register_component("factory.GridBaseAgent")
class GridBaseAgent(ABC):
    """
    网格工厂AGV智能体基类

    功能特性:
    1. 支持上下左右移动动作
    2. 支持多种移动策略
    3. 支持路径规划和目标导航
    4. 支持避障和碰撞检测
    """
    # 不同观察的智能体处理方案不同
    AGENT_TYPE:ObsType = ObsType.DEFAULT.value

    def __init__(self, name=None, agent_id=None, parameter: dict = None):
        """
        通用智能体基类
        :param name: 智能体名称
        :param agent_id: 智能体ID或唯一标识
        :param parameter: 相关参数
        """
        self.name = name or self.__class__.__name__
        self.agent_id = agent_id

        self.parameter = parameter or {
            "step_times": 100,
            "learning_rate": 0.01,
            "max_turns": 20000,
            "epsilon": 0.1,
            "min_epsilon": 0.01,
            "epsilon_decay": 0.995,
            "batch_size": 64,
            "buffer_size": 10000,
            "target_update_freq": 500,
            "warmup_steps": 1000,
            "device": "cpu",
            "seed": 42,
        }  # 配置参数,根据不同的agent有不同的视线

        self.alive = True  # 是否在线
        self.turns = 0  # 存活轮次
        self.sample_time = []  # 每轮的决策时间
        self.buffer = []  # 采样记忆池,每条时刻的数据由不同的agent实现

    def is_alive(self):
        return self.alive

    @abstractmethod
    def reward(self, *args, **kwargs):
        """Agent 计算自身的reward"""
        pass

    @abstractmethod
    def is_finish(self, *args, **kwargs):
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
    def before_train(self, *args, **kwargs):
        pass

    @abstractmethod
    def after_train(self, *args, **kwargs):
        pass

    @abstractmethod
    def decision(self, *args, **kwargs):
        """Agent 推理采样"""
        # todo 此处需要进行测试
        start_time = time.time()
        self.before_sample(*args, **kwargs)
        actions = self.sample(*args, **kwargs)
        self.after_sample(*args, **kwargs)
        end_time = time.time()

        self.before_train()
        self.train()
        self.after_train()

        self.turns += 1

        if self.turns >= self.parameter.get("max_turns", 1000):
            self.alive = False

        return {
            "actions": actions,
            "reward": self.reward(*args, **kwargs),
            "is_finish": self.is_finish(*args, **kwargs),
            "sample_time": end_time - start_time,
        }

    @abstractmethod
    def train(self, *args, **kwargs):
        """Agent 训练"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.agent_id} name={self.name}>"
