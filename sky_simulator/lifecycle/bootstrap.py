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

def bootstrap():
    print("[Bootstrap] Loading configuration...")
    config = load_config("config/application.yml")  # ✅ 此时读取

    print("[Bootstrap] Creating environment...")
    env_type = config["env"]["type"]  # "sim" or "real"
    environment = create_environment(env_type, config)

    print("[Bootstrap] Scanning and registering components...")
    scan_and_register_components()

    return environment, config
