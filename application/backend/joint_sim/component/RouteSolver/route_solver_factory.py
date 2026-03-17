"""
@Project ：SkyEngine
@File    ：route_solver_factory.py
@Author  ：Skyrimforest
@Date    ：2025/11/04
"""

from joint_sim.component.RouteSolver.template_solver.route_solver import \
    RouteSolver


class RouteSolverFactory:
    """RouteSolver 工厂类：支持类注册与装饰器注册"""

    _registry = {}

    # ------------------------------------------------------------
    # ✅ 1. 普通注册接口
    # ------------------------------------------------------------
    @classmethod
    def register(cls, name: str, solver_class):
        """显式注册一个 RouteSolver"""
        if not issubclass(solver_class, RouteSolver):
            raise TypeError(f"{solver_class} 必须继承  RouteSolver")
        cls._registry[name.lower()] = solver_class
        return solver_class

    # ------------------------------------------------------------
    # ✅ 2. 装饰器形式注册接口
    # ------------------------------------------------------------
    @classmethod
    def register_solver(cls, name: str):
        """
        用作装饰器:
        @RouteSolverFactory.register_solver("random")
        class RandomRouteSolver(BaseRouteSolver): ...
        """

        def decorator(solver_class):
            return cls.register(name, solver_class)

        return decorator

    # ------------------------------------------------------------
    # ✅ 3. 工厂创建接口
    # ------------------------------------------------------------
    @classmethod
    def create(cls, name: str, **kwargs) -> RouteSolver:
        name = name.lower()
        if name not in cls._registry:
            raise ValueError(
                f"未知的 RouteSolver 类型: {name}，可选项为: {list(cls._registry.keys())}"
            )
        solver_class = cls._registry[name]
        return solver_class(**kwargs)

    @classmethod
    def available(cls):
        return list(cls._registry.keys())
