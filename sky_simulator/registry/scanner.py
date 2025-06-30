'''
@Project ：tiangong 
@File    ：scanner.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:38 
'''
import importlib
import pkgutil
import sky_simulator

import yaml
import os
from sky_simulator.registry.registry import component_registry
from pathlib import Path


def load_config(config_path: str):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    if "config" not in raw_config:
        raise ValueError("Missing 'config' section in configuration.")

    sky_config = raw_config["config"]
    sky_config['config_path'] = Path(config_path)

    component_registry['config'] = sky_config


def scan_and_register_components():
    """
    自动导入并触发装饰器注册
    """
    package = sky_simulator
    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        importlib.import_module(module_name)
