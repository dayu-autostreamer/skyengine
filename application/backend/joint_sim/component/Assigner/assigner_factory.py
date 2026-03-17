'''
@Project ：SkyEngine 
@File    ：assigner_factory.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/4 23:09
'''
from joint_sim.component.Assigner.template_assigner.assigner import Assigner


class AssignerFactory:
    """Assigner 工厂类：支持类注册与装饰器注册"""

    _registry = {}

    # ------------------------------------------------------------
    # ✅ 1. 普通注册接口
    # ------------------------------------------------------------
    @classmethod
    def register(cls, name: str, solver_class):
        """显式注册一个 Assigner"""
        if not issubclass(solver_class, Assigner):
            raise TypeError(f"{solver_class} 必须继承  Assigner")
        cls._registry[name.lower()] = solver_class
        return solver_class

    # ------------------------------------------------------------
    # ✅ 2. 装饰器形式注册接口
    # ------------------------------------------------------------
    @classmethod
    def register_solver(cls, name: str):
        """
        用作装饰器:
        @AssignerFactory.register_solver("random")
        class RandomAssigner(Assigner): ...
        """

        def decorator(solver_class):
            return cls.register(name, solver_class)

        return decorator

    # ------------------------------------------------------------
    # ✅ 3. 工厂创建接口
    # ------------------------------------------------------------
    @classmethod
    def create(cls, name: str, **kwargs) -> Assigner:
        name = name.lower()
        if name not in cls._registry:
            raise ValueError(
                f"未知的 Assigner 类型: {name}，可选项为: {list(cls._registry.keys())}"
            )
        solver_class = cls._registry[name]
        return solver_class(**kwargs)

    @classmethod
    def available(cls):
        return list(cls._registry.keys())