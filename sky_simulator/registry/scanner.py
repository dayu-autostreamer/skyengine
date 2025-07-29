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


def load_config(config: str | dict):
    if isinstance(config, str):
        if not os.path.exists(config):
            raise FileNotFoundError(f"Configuration file not found: {config}")

        with open(config, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        if "config" not in raw_config:
            raise ValueError("Missing 'config' section in configuration.")

        # 获取文件内的配置
        sky_config = raw_config["config"]
        # 保存配置文件的路径
        sky_config['config_path'] = Path(config)
        component_registry['config'] = sky_config
    elif isinstance(config, dict):
        # 保存配置文件的路径
        component_registry['config_path'] = config


def scan_and_register_components():
    """
    自动导入并触发装饰器注册
    """
    package = sky_simulator
    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        importlib.import_module(module_name)
