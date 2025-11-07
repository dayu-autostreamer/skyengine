'''
@Project ：tiangong 
@File    ：test_context.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 23:01 
'''

from sky_executor.utils.registry import scan_and_register_components
from sky_executor.utils.registry.scanner import load_config
from sky_executor.utils.call_back import BackendMapLoader

config_path = '../../config/application_config.yaml'

if __name__ == '__main__':
    load_config(config_path)
    scan_and_register_components()



