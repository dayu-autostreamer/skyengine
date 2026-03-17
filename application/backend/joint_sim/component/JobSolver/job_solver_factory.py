'''
@Project ：SkyEngine 
@File    ：job_solver_factory.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/4 23:09
'''

from joint_sim.component.JobSolver.template_solver.job_solver import JobSolver


class JobSolverFactory:
    """JobSolver 工厂类：支持类注册与装饰器注册"""

    _registry = {}

    # ------------------------------------------------------------
    # ✅ 1. 普通注册接口
    # ------------------------------------------------------------
    @classmethod
    def register(cls, name: str, solver_class):
        """显式注册一个 JobSolver"""
        if not issubclass(solver_class, JobSolver):
            raise TypeError(f"{solver_class} 必须继承  JobSolver")
        cls._registry[name.lower()] = solver_class
        return solver_class

    # ------------------------------------------------------------
    # ✅ 2. 装饰器形式注册接口
    # ------------------------------------------------------------
    @classmethod
    def register_solver(cls, name: str):
        """
        用作装饰器:
        @JobSolverFactory.register_solver("random")
        class RandomJobSolver(BaseJobSolver): ...
        """

        def decorator(solver_class):
            return cls.register(name, solver_class)

        return decorator

    # ------------------------------------------------------------
    # ✅ 3. 工厂创建接口
    # ------------------------------------------------------------
    @classmethod
    def create(cls, name: str, **kwargs) -> JobSolver:
        name = name.lower()
        if name not in cls._registry:
            raise ValueError(
                f"未知的 JobSolver 类型: {name}，可选项为: {list(cls._registry.keys())}"
            )
        solver_class = cls._registry[name]
        return solver_class(**kwargs)

    @classmethod
    def available(cls):
        return list(cls._registry.keys())
