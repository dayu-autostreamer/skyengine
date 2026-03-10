"""
@Project ：SkyEngine
@File    ：assigner_factory.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/4 23:09
"""

from application.backend.core.BaseFactoryProxy import BaseFactoryProxy


class ProxyFactory:
    """Proxy 工厂类：支持类注册与装饰器注册"""

    _registry = {}

    # ------------------------------------------------------------
    # ✅ 1. 普通注册接口
    # ------------------------------------------------------------
    @classmethod
    def register(cls, name: str, proxy_class):
        """显式注册一个 Proxy"""
        if not issubclass(proxy_class, BaseFactoryProxy):
            raise TypeError(f"{proxy_class} 必须继承  BaseFactoryProxy")
        cls._registry[name.lower()] = proxy_class
        return proxy_class

    # ------------------------------------------------------------
    # ✅ 2. 装饰器形式注册接口
    # ------------------------------------------------------------
    @classmethod
    def register_proxy(cls, name: str):
        """
        用作装饰器:
        @ProxyFactory.register_proxy("random")
        class RandomProxy(Proxy): ...
        """

        def decorator(proxy_class):
            return cls.register(name, proxy_class)

        return decorator

    # ------------------------------------------------------------
    # ✅ 3. 工厂创建接口
    # ------------------------------------------------------------
    @classmethod
    def create(cls, name: str, **kwargs) -> BaseFactoryProxy:
        name = name.lower()
        if name not in cls._registry:
            raise ValueError(
                f"未知的 FactoryProxy 类型: {name}，可选项为: {list(cls._registry.keys())}"
            )
        solver_class = cls._registry[name]
        return solver_class(**kwargs)

    @classmethod
    def available(cls):
        return list(cls._registry.keys())
