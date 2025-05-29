'''
@Project ：tiangong 
@File    ：lifecycle_hooks.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/30 0:17 
'''
# lifecycle_hooks.py

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sky_simulator.packet_factory.packet_factory_env import PacketFactoryEnv


class EnvInitializer(ABC):
    @abstractmethod
    def initialize(self, env: "PacketFactoryEnv"):
        pass


class EnvPostProcessor(ABC):
    @abstractmethod
    def post_process(self, env: "PacketFactoryEnv"):
        pass


class EnvLifecycleListener(ABC):
    def on_env_start(self, env: "PacketFactoryEnv"):
        pass

    def on_env_step(self, env: "PacketFactoryEnv"):
        pass

    def on_env_end(self, env: "PacketFactoryEnv"):
        pass
