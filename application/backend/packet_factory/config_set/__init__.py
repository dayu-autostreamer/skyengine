import os
import json

# 初始化目录映射字典
dir_map = {}
dir_path = os.path.dirname(os.path.abspath(__file__))


def scan_directories(root_dir='.'):
    """递归扫描指定目录下的所有文件夹并存储信息到dir_map"""
    for item in os.listdir(root_dir):
        item_path = os.path.join(root_dir, item)
        # 检查是否为目录
        if os.path.isdir(item_path):
            # 获取相对路径（相对于当前目录）
            rel_path = os.path.relpath(item_path)
            # 获取目录创建时间（时间戳）
            create_time = os.path.getctime(item_path)
            # 获取目录修改时间（时间戳）
            modify_time = os.path.getmtime(item_path)

            # 存储目录信息
            dir_map[rel_path] = {
                'path': rel_path,
                'create_time': create_time,
                'modify_time': modify_time,
                'subdirectories': scan_directories(item_path)  # 递归扫描子目录
            }

    return list(dir_map.keys())  # 返回当前目录下的子目录列表


# 执行扫描
scan_directories()

# 打印结果（可选）
if __name__ == "__main__":
    print(json.dumps(dir_map, indent=2))
    print(dir_path)
