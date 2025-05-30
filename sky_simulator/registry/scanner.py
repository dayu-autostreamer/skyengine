'''
@Project ：tiangong 
@File    ：scanner.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:38 
'''
import importlib
import pkgutil
import sky_simulator  # 你定义的组件模块包

def scan_and_register_components():
    """
    自动导入并触发装饰器注册
    """
    package = sky_simulator
    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        importlib.import_module(module_name)