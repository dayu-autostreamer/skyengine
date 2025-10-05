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
from typing import List, Optional
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
        component_registry['config'] = config


def scan_and_register_components():
    """
    自动导入并触发装饰器注册
    """
    package = sky_simulator
    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        importlib.import_module(module_name)


def selective_scan_and_register_components(
        include_dirs: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None,
        scan_all: bool = False
):
    """
    自动导入并触发装饰器注册

    参数:
        include_dirs: 指定需要扫描的子目录列表（相对于 sky_simulator 包）
        exclude_dirs: 指定需要排除的子目录列表（相对于 sky_simulator 包）
        scan_all: 是否扫描整个 sky_simulator 包（True 会忽略 include_dirs）

    调用示例:
        scan_and_register_components()                     # 默认扫描 include_dirs（或空，扫描核心目录）
        scan_and_register_components(scan_all=True)       # 扫描全量
        scan_and_register_components(exclude_dirs=["MAPF_GPT/gpt"])  # 排除特定目录
        scan_and_register_components(include_dirs=["core", "environment"])  # 扫描指定目录
    """

    def should_scan(module_name: str) -> bool:
        # 排除优先
        for ex in exclude_dirs:
            if module_name.startswith(f"{package.__name__}.{ex}"):
                return False
        # 如果有 include_dirs，只有包含的才扫描
        if include_dirs:
            for inc in include_dirs:
                if module_name.startswith(f"{package.__name__}.{inc}"):
                    return True
            return False
        # 默认扫描根目录下非子目录模块
        return True

    package = sky_simulator

    if scan_all:
        # 扫描整个包
        for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            if should_scan(module_name):
                importlib.import_module(module_name)
        return

    # 构建最终扫描目录
    include_dirs = include_dirs or []
    exclude_dirs = exclude_dirs or []

    # walk_packages 遍历所有子模块
    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if should_scan(module_name):
            importlib.import_module(module_name)
