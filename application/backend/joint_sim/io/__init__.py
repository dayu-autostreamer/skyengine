"""
IO 模块 - 配置加载与转换

此模块提供配置文件的加载、解析和转换功能。

====== 主要函数 ======
1. load_grid_factory_config - 加载 JSON 配置文件
2. parse_grid_config - 解析 GridConfig
3. parse_machine_config - 解析机器配置
4. parse_job_config - 解析任务配置
5. create_env_from_config - 从配置创建环境

====== 数据格式强制规约 ======
1. JSON 输入: location 必须是 List[int], 长度 = 2
2. Python 内部: location 使用 Tuple[int, int]
3. 输出快照: location 转回 List[int]

====== 使用示例 ======
from joint_sim.io import create_env_from_config, load_grid_factory_config

# 方式1: 直接从配置文件创建环境
env = create_env_from_config("config.json")

# 方式2: 分步加载
config = load_grid_factory_config("config.json")
grid_config = parse_grid_config(config)
machine_config, positions = parse_machine_config(config)
job_config = parse_job_config(config, machine_config.num_machines)
"""

from joint_sim.io.use_io import (
    load_grid_factory_config,
    parse_grid_config,
    parse_machine_config,
    parse_job_config,
    create_env_from_config,
)

__all__ = [
    "load_grid_factory_config",
    "parse_grid_config",
    "parse_machine_config",
    "parse_job_config",
    "create_env_from_config",
]
