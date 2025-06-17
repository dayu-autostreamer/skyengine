'''
@Project ：tiangong 
@File    ：bootstrap.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:18 
'''
# bootstrap.py
from sky_simulator.utils import load_config
from sky_simulator.registry import scan_and_register_components
from .context_creator import create_context,check_context
def bootstrap(config_path):
    # ---------- 读取配置 ----------
    print("[Bootstrap] Loading configuration...")
    load_config(config_path)

    # ---------- 扫描组件 ----------
    print("[Bootstrap] Scanning and registering components...")
    scan_and_register_components()

    # ---------- 创建环境 ----------
    print("[Bootstrap] Creating context...")
    environment = create_context()

    # ---------- 检查环境 ----------
    print("[Bootstrap] Checking context...")
    check_context(environment)

    return environment, config
