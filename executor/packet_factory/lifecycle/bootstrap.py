'''
@Project ：tiangong 
@File    ：bootstrap.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:18 
'''
# bootstrap.py
from executor.packet_factory.registry import scan_and_register_components, load_config
from .context_creator import create_context
from executor.packet_factory.logger.logger import LOGGER

def bootstrap(config):
    # ---------- 读取配置 ----------
    LOGGER.info("[Bootstrap] Loading configuration...")
    load_config(config)

    # ---------- 扫描组件 ----------
    LOGGER.info("[Bootstrap] Scanning and registering components...")
    scan_and_register_components()

    # ---------- 创建环境 ----------
    LOGGER.info("[Bootstrap] Creating context...")
    environment, agent = create_context()

    # ---------- 检查环境 ----------
    LOGGER.info("[Bootstrap] Checking context...")

    LOGGER.info("[Bootstrap] Env, Agent Created Successfully...")
    return environment, agent
