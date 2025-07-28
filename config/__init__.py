# 提供全局根路径,提供各个文件夹相对根路径的相对寻址,跨平台

import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 给出后端路径
BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')
BACKEND_DATA_DIR = os.path.join(BACKEND_DIR, 'config_set')

# 给出数据集路径
CONFIG_DIR = os.path.join(ROOT_DIR, 'config')
MAP_CONFIG_DIR = os.path.join(CONFIG_DIR, 'config_set')

# 给出日志路径
LOG_DIR = os.path.join(ROOT_DIR, 'sky_logs')
TEMP_LOG_DIR = os.path.join(LOG_DIR, 'temp_logs')
BACKEND_LOG_DIR = os.path.join(LOG_DIR, 'backend_logs')
SYSTEM_LOG_DIR = os.path.join(LOG_DIR, 'system_logs')

if __name__ == '__main__':
    print(CONFIG_DIR)
    print(LOG_DIR)
