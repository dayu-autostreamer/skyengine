'''
@Project ：tiangong 
@File    ：file_service.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/7/21 11:35 
'''
import backend.config_set as config

def get_config_dir():
    return config.dir_path


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
    create_dir(dir_name)

    # 构建完整保存路径
    save_path = os.path.join(dir_name, file.filename)

    # 保存文件
    with open(save_path, "wb") as f:
        content = file.file.read()
        f.write(content)

    return save_path



def get_log():
    pass


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
    dir_path = config.dir_path + '/'+ relative_dir_path
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
    print(get_config_set())
