'''
@Project ：tiangong 
@File    ：EventMachineUncertain.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/7/2 15:52 
'''
import numpy as np

from executor.packet_factory.logger.logger import LOGGER


class MachineUncertaintySimulator:
    # todo: 通过yaml配置是否开启、随机种子、随机概率

    def __init__(self, base_seed=None, probability=0.3):
        """
        :param base_seed: 基础种子, 用于初始化随机流, None 表示系统随机
        :param probability: 不确定事件发生的概率 [0, 1]
        """
        self.base_seed = base_seed
        self.probability = probability
        self.cache = {}
        # 创建一个独立的随机数生成器
        self.seed_seq = np.random.SeedSequence(base_seed)
        self.rng = np.random.Generator(np.random.PCG64(self.seed_seq))
        # 从上次调用uncertain_event_occurred函数开始，是否发生过不确定事件
        self.is_occurred = False

    def uncertain_event_ratio(self, machine_id, operation_id):
        """
        :param machine_id: 机器 ID
        :param operation_id: 操作 ID
        :return: 若随机事件发生, 返回实际机器执行时间和原始执行时间的比例, 否则返回1
        :rtype: float
        """
        key = (machine_id, operation_id)
        if key in self.cache:
            return self.cache[key]

        # 使用类内部的 rng 生成随机值
        random_value = self.rng.random()
        result = random_value < self.probability

        if result:
            LOGGER.info(f"Machine {machine_id} operation {operation_id} has uncertain event")
            self.is_occurred = True
            # todo: 通过yaml配置随机事件后的具体影响
            random_ratio = np.random.uniform(1, 1.5)
        else:
            random_ratio = 1

        self.cache[key] = random_ratio
        return random_ratio

    def uncertain_event_occurred(self):
        """
        :return: 若发生随机事件, 返回True, 否则返回False
        :rtype: bool
        """
        result = self.is_occurred
        self.is_occurred = False
        return result
