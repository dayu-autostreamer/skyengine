'''
@Project ：tiangong 
@File    ：bootstrap.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:18 
'''
from sky_executor.utils.registry import load_config, selective_scan_and_register_components
from .context_creator import create_context
from sky_logs.logger import LOGGER


def bootstrap(config):
    # ---------- 读取配置 ----------
    LOGGER.info("[Bootstrap] Loading configuration...")
    load_config(config)

    # ---------- 扫描组件 ----------
    LOGGER.info("[Bootstrap] Scanning and registering components...")
    selective_scan_and_register_components(scan_all=True,
                                           exclude_dirs=["environment.factory",
                                                         "call_back.grid_factory_callback",
                                                         "event.event.grid_factory_event",
                                                         "environment.packet_factory.Trainer"
                                                         ])

    # ---------- 创建环境 ----------
    LOGGER.info("[Bootstrap] Creating context...")
    environment, agent = create_context()

    # ---------- 检查环境,todo----------
    LOGGER.info("[Bootstrap] Checking context...")

    LOGGER.info("[Bootstrap] Env, Agent Created Successfully...")
    return environment, agent
