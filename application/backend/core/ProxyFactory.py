"""
@Project ：SkyEngine
@File    ：ProxyFactory.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/4 23:09
"""

import sys
from pathlib import Path


from application.backend.core.BaseFactoryProxy import BaseFactoryProxy, FactoryProxyProtocol


class ProxyFactory:
    """Proxy 工厂类：支持类注册与装饰器注册"""

    _registry = {}

    # ------------------------------------------------------------
    # ✅ 1. 普通注册接口
    # ------------------------------------------------------------
    @classmethod
    def register(cls, name: str, proxy_class):
        """显式注册一个 Proxy"""
        # 支持两种方式：继承 BaseFactoryProxy 或实现 FactoryProxyProtocol
        is_valid = (
            issubclass(proxy_class, BaseFactoryProxy) or
            isinstance(proxy_class, FactoryProxyProtocol)
        )
        if not is_valid:
            # 尝试通过鸭子类型检查：至少有这些方法
            required_methods = ['initialize', 'start', 'pause', 'reset', 'cleanup', 'set_config']
            has_methods = all(hasattr(proxy_class, m) for m in required_methods)
            if not has_methods:
                raise TypeError(
                    f"{proxy_class} 必须继承 BaseFactoryProxy 或实现 FactoryProxyProtocol 接口"
                )
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

        # 针对插件环境进行延迟导入
        if name == "grid_factory":
            try:
                # 添加 backend 目录到 sys.path，使得可以 import joint_sim
                _backend_path = Path(__file__).parent.parent
                if str(_backend_path) not in sys.path:
                    sys.path.insert(0, str(_backend_path))
                from joint_sim.proxy.grid_factory_proxy import GridFactoryProxy

                if name not in cls._registry:
                    cls.register(name, GridFactoryProxy)
            except ImportError as e:
                raise ImportError(f"创建 {name} 失败。请先安装必要的依赖包: {e}")

        elif name == "packet_factory":
            try:
                from application.backend.core.PacketFactoryProxy import PacketFactoryProxy

                if name not in cls._registry:
                    cls.register(name, PacketFactoryProxy)
            except ImportError as e:
                raise ImportError(f"创建 {name} 失败。请先安装必要的依赖包: {e}")

        if name not in cls._registry:
            raise ValueError(
                f"未知的 FactoryProxy 类型: {name}，可选项为: {list(cls._registry.keys())}"
            )
        solver_class = cls._registry[name]
        return solver_class(**kwargs)

    @classmethod
    def available(cls):
        return list(cls._registry.keys())
