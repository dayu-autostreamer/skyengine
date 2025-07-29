'''
@Project ：tiangong 
@File    ：file_service.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/7/21 11:35 
'''
import backend.config_set as backend_config
import config


def get_config_dir():
    return backend_config.dir_path


import os


def create_dir(dir_name):
    """
    创建指定目录（如果不存在）。
    """
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return dir_name


def save_file(dir_name, file):
    """
    将文件保存到指定目录中。
    参数：
    - dir_name: 目标目录（必须是有效路径）
    - file: FastAPI UploadFile 对象
    """
    # 确保目录存在
    create_dir(os.path.join(config.BACKEND_DATA_DIR, dir_name))
    # 构建完整保存路径
    save_path = os.path.join(config.BACKEND_DATA_DIR, file.filename)
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
    config_root = config.BACKEND_DATA_DIR
    if not os.path.exists(config_root):
        return []

    folder_list = [
        name for name in os.listdir(config_root)
        if os.path.isdir(os.path.join(config_root, name)) and name != '__pycache__'
    ]

    return folder_list


def get_file_content():
    pass


def get_config_set(relative_dir_path='template_config_set'):
    """
    输入文件夹路径,获得配置文件集合

    返回格式:
    {
        "config1.yaml": { ... },  # 配置文件内容
        "config2.yaml": { ... },
        ...
    }
    """
    config_set = []
    dir_path = config.dir_path + '/' + relative_dir_path
    # 检查目录是否存在
    if not os.path.exists(dir_path):
        print(f"警告: 目录 '{dir_path}' 不存在")
        return config_set

    # 遍历目录中的所有文件
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)

        # 检查是否为文件且为yaml格式
        if os.path.isfile(file_path) and filename.endswith(('.yaml', '.yml')):
            print(file_path)

    return config_set


if __name__ == '__main__':
    print(get_config_list())
    print(get_log(config.BACKEND_CONFIG_DIR))
