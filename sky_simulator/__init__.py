import os

# 动态查找项目根目录
def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    print(get_project_root())