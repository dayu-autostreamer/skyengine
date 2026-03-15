'''
@Project ：tiangong 
@File    ：file_service.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/7/21 11:35 
'''
import yaml
import os

import application.backend.packet_factory.config_set as config_set
import application.backend.packet_factory.config as config
import executor.packet_factory.logger.backend_logs as BACKEND_LOGGER
import executor.packet_factory.logger.system_logs as SYSTEM_LOGGER

def get_config_set_dir():
    return config_set.dir_path

def get_config_dir():
    return config.dir_path

def get_backend_log_dir():
    return BACKEND_LOGGER.dir_path

def get_system_log_dir():
    return SYSTEM_LOGGER.dir_path


def create_dir(dir_name):
    """
    创建指定目录（如果不存在）。
    """
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return dir_name


def save_file(dir_name, file):
    """
    将新的config_set保存到指定目录中。
    参数：
    - dir_name: 目标目录（必须是有效路径）
    - file: FastAPI UploadFile 对象
    """
    # 确保目录存在
    dir_path=os.path.join(get_config_set_dir(), dir_name)
    create_dir(dir_path)
    # 构建完整保存路径
    save_path = os.path.join(dir_path, file.filename)
    # 保存文件
    with open(save_path, "wb") as f:
        content = file.file.read()
        f.write(content)

    return save_path


def get_log(log_path):
    """
    扫描 log_path 目录下的所有日志文件，按修改时间排序，返回最新的一个。

    参数：
        log_path (str): 日志文件所在的目录。

    返回：
        str | None: 最新的日志文件路径，如果没有则返回 None。
    """
    if not os.path.exists(log_path) or not os.path.isdir(log_path):
        return None

    # 获取所有文件的完整路径
    log_files = [
        os.path.join(log_path, f)
        for f in os.listdir(log_path)
        if os.path.isfile(os.path.join(log_path, f))
    ]

    if not log_files:
        return None

    # 按文件修改时间排序（降序），最新的在前面
    log_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    return log_files[0]


def get_config_list():
    """
    扫描 config_set 文件夹内的所有子文件夹，返回文件夹名称列表。
    返回：
        List[str]: 所有子文件夹的名称列表。
    """
    config_root = get_config_set_dir()
    print(config_root)
    if not os.path.exists(config_root):
        return []

    folder_list = [
        name for name in os.listdir(config_root)
        if os.path.isdir(os.path.join(config_root, name)) and name != '__pycache__'
    ]
    print(folder_list)

    return folder_list


def get_file_content():
    pass

def load_factory_config(target_factory: str):
    base_dir = os.path.join(get_config_set_dir(), target_factory)

    event_config_path = os.path.join(base_dir, "event_config.yaml")
    job_config_path = os.path.join(base_dir, "job_config.yaml")
    map_config_path = os.path.join(base_dir, "map_config.yaml")

    return {
        "event_config": event_config_path,
        "job_config": job_config_path,
        "map_config": map_config_path
    }


def get_new_config_file(target_factory: str):
    # 配置文件插入
    specific_config_files = load_factory_config(target_factory)

    template_config_path = os.path.join(get_config_dir(), 'application_config.yaml')

    with open(template_config_path, 'r') as f:
        specific_config = yaml.safe_load(f)

    sky_config = specific_config['config']
    env_type = sky_config['env_type']
    sky_config[env_type]['task_config']['file'] = specific_config_files['job_config']
    sky_config[env_type]['event_config']['file'] = specific_config_files['event_config']
    sky_config[env_type]['factory_config']['file'] = specific_config_files['map_config']

    new_config_path = os.path.join(get_config_dir(), f'{target_factory}_config.yaml')
    # 写入新配置
    with open(new_config_path, 'w') as f:
        yaml.dump(specific_config, f, default_flow_style=False, allow_unicode=True)

    sky_config['config_path'] = new_config_path
    print(sky_config)
    return sky_config

if __name__ == '__main__':
    get_new_config_file('template_config_set')
