'''
@Project ：tiangong 
@File    ：load_config.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 1:30 
'''
# config/loader.py

import yaml
import os

def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    if "sky" not in raw_config:
        raise ValueError("Missing 'sky' section in configuration.")

    sky_config = raw_config["sky"]

    env_type = sky_config.get("env_type")
    if env_type not in ("simulation", "real"):
        raise ValueError(f"Invalid env_type: {env_type}. Must be 'simulation' or 'real'.")

    common_config = sky_config.get("common", {})
    env_specific_config = sky_config.get(env_type, {})

    # 合并 common 和 env-specific
    merged_config = {
        "env_type": env_type,
        **common_config,
        **env_specific_config
    }

    return merged_config
