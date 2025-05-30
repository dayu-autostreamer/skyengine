'''
@Project ：tiangong 
@File    ：bootstrap.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/5/31 0:18 
'''
def bootstrap():
    # Step 1: 检测运行环境（仿真 / 实机）
    env_type = detect_environment()
    print(f"[Bootstrap] Detected environment: {env_type}")

    # Step 2: 初始化上下文环境
    initializer = Initializer(env_type)
    context = initializer.initialize()

    print(f"[Bootstrap] Initialization complete. Environment context is ready.")
    return context