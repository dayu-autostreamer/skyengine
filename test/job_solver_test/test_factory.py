'''
@Project ：SkyEngine 
@File    ：test_factory.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/4 23:31
'''

from sky_executor.grid_factory.factory.grid_factory_env.Component.RouteSolver.route_solver_factory import RouteSolverFactory
print(RouteSolverFactory.available())
solver = RouteSolverFactory.create("astar")
print(solver)
