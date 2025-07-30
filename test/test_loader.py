'''
@Project ：tiangong 
@File    ：test_loader.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/7/30 12:39 
'''

from sky_simulator.registry import scan_and_register_components
from sky_simulator.registry.scanner import load_config
from sky_simulator.call_back.backend_callback.BackendMapLoader import FactoryMapLoader
import config

config_path = config.CONFIG_DIR+'/template_config_set_config.yaml'

if __name__ == '__main__':
    load_config(config_path)
    scan_and_register_components()
    map_loader = FactoryMapLoader()
    print(map_loader())



