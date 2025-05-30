'''
@Project ：tiangong 
@File    ：lifecycle_mixin.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/30 0:18 
'''
from typing import List
from .lifecycle_hooks import EnvInitializer, EnvPostProcessor, EnvLifecycleListener


class LifecycleHookMixin:
    def __init__(self):
        self.initializers: List[EnvInitializer] = []
        self.post_processors: List[EnvPostProcessor] = []
        self.lifecycle_listeners: List[EnvLifecycleListener] = []

    def register_initializer(self, initializer: EnvInitializer):
        self.initializers.append(initializer)

    def register_post_processor(self, processor: EnvPostProcessor):
        self.post_processors.append(processor)

    def register_lifecycle_listener(self, listener: EnvLifecycleListener):
        self.lifecycle_listeners.append(listener)

    def call_initializers(self):
        for initializer in self.initializers:
            initializer.initialize(self)

    def call_post_processors(self):
        for processor in self.post_processors:
            processor.post_process(self)

    def call_on_start(self):
        for listener in self.lifecycle_listeners:
            listener.on_env_start(self)

    def call_on_step(self):
        for listener in self.lifecycle_listeners:
            listener.on_env_step(self)

    def call_on_end(self):
        for listener in self.lifecycle_listeners:
            listener.on_env_end(self)