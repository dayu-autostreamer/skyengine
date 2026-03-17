



# 这里获得job层根据job本身生成的路由任务，观察当前的状况并进行分配给AGV。


# Assigner/__init__.py
import pkgutil
import importlib

def recursive_import(package):
    for _, name, ispkg in pkgutil.iter_modules(package.__path__):
        full_name = f"{package.__name__}.{name}"
        module = importlib.import_module(full_name)
        if ispkg:
            recursive_import(module)

def auto_import_solvers():
    import sys
    current_module = sys.modules[__name__]
    recursive_import(current_module)

auto_import_solvers()