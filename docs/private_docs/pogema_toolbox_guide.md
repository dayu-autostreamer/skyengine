# Pogema-Toolbox 使用指南
1. 概述 - Pogema-Toolbox 的基本介绍和主要功能
2. 安装方法 - 如何安装 Pogema-Toolbox
3. 核心功能 - 详细介绍了算法注册、自定义地图管理、地图生成器和评估系统
4. 完整评估流程示例 - 提供了使用 Pogema-Toolbox 进行评估的完整代码示例
5. Pogema 的集成 - 说明了如何将 Pogema-Toolbox 与 Pogema 环境集成
6. 高级功能 - 介绍了配置变体生成器和 MovingAI 地图导入等高级功能


## 1. 概述

Pogema-Toolbox 是一个为 Pogema 环境提供的综合工具包，专注于简化多智能体路径规划算法的测试、评估和可视化过程。该工具包提供了统一的接口，使任何可学习的 MAPF（多智能体路径规划）算法能够在 Pogema 环境中无缝执行。

主要功能包括：
- 自定义地图管理：注册和使用自定义地图
- 算法注册与评估：统一接口注册和评估不同的 MAPF 算法
- 分布式测试：使用 Dask 进行并行测试和评估
- 结果可视化：提供多种可视化工具展示评估结果

## 2. 安装

```bash
pip install pogema-toolbox
```

## 3. 核心功能

### 3.1 算法注册与使用

Pogema-Toolbox 允许用户注册自定义算法，并通过统一接口使用它们：

```python
from pogema import BatchAStarAgent
from pogema_toolbox.registry import ToolboxRegistry

# 注册 A* 算法
ToolboxRegistry.register_algorithm('A*', BatchAStarAgent)

# 创建算法实例
algo = ToolboxRegistry.create_algorithm("A*")
```

对于带有可调超参数的复杂算法，可以这样注册：

```python
# 注册带配置的算法
ToolboxRegistry.register_algorithm('Follower', FollowerInference, 
                                  FollowerInferenceConfig,
                                  follower_preprocessor)
```

### 3.2 自定义地图管理

Pogema-Toolbox 提供了简单的方式来创建和注册自定义地图：

```python
from pogema_toolbox.registry import ToolboxRegistry

# 创建自定义地图
custom_map = """
.......#.
...#...#.
.#.###.#.
"""

# 注册自定义地图
ToolboxRegistry.register_maps({"custom_map": custom_map})
```

### 3.3 地图生成器

Pogema-Toolbox 包含多种地图生成器，位于 `generators` 目录下：

- `random_generator.py`: 随机地图生成器
- `maze_generator.py`: 迷宫地图生成器
- `warehouse_generator.py`: 仓库场景地图生成器
- `house_generator.py`: 房屋场景地图生成器

这些生成器可以创建不同类型和复杂度的环境，用于测试算法在各种场景下的性能。

### 3.4 评估系统

Pogema-Toolbox 提供了完整的评估框架，可以通过 YAML 配置文件定义评估参数：

```python
from pogema_toolbox.evaluator import evaluation
import yaml

# 加载评估配置
with open("evaluation_config.yaml") as f:
    evaluation_config = yaml.safe_load(f)

# 执行评估
evaluation(evaluation_config, eval_dir="results")
```

评估配置示例：

```yaml
environment:  # 环境配置
  name: Environment
  on_target: 'restart'
  max_episode_steps: 128
  observation_type: 'POMAPF'
  collision_system: 'soft'
  seed: 
    grid_search: [ 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 ]
  num_agents:
    grid_search: [ 8, 16, 24, 32, 48, 64 ]
  map_name:
    grid_search: [
        validation-mazes-seed-000, validation-mazes-seed-001, validation-mazes-seed-002, 
        validation-mazes-seed-003, validation-mazes-seed-004, validation-mazes-seed-005, 
    ]

algorithms:  # 算法配置
  RHCR-5-10:
    name: RHCR
    parallel_backend: 'balanced_dask'
    num_process: 32
    simulation_window: 5
    planning_window: 10
    time_limit: 10
    low_level_planner: 'SIPP'
    solver: 'PBS'

results_views:  # 结果可视化配置
  01-mazes:
```

### 3.5 结果可视化

Pogema-Toolbox 的 `views` 模块提供了多种可视化工具：

- `view_plot.py`: 基本绘图工具
- `view_multi_plot.py`: 多图表绘制工具
- `view_tabular.py`: 表格形式展示结果
- `view_utils.py`: 可视化辅助工具

这些工具可以将评估结果以图表、表格等形式直观地展示出来。

## 4. 完整评估流程示例

以下是使用 Pogema-Toolbox 进行完整评估的示例：

```python
from pogema_toolbox.evaluator import evaluation
from pogema import BatchAStarAgent
from pogema_toolbox.eval_utils import initialize_wandb, save_evaluation_results
from pogema_toolbox.create_env import create_env_base, Environment
from pogema_toolbox.registry import ToolboxRegistry
import yaml
from pathlib import Path

# 设置日志级别
ToolboxRegistry.setup_logger(level='INFO')

# 注册环境和算法
ToolboxRegistry.register_env('Pogema-v0', create_env_base, Environment)
ToolboxRegistry.register_algorithm('A*', BatchAStarAgent)

# 加载配置文件
config_path = Path('config_examples/my_config.yaml')
with open(config_path) as f:
    evaluation_config = yaml.safe_load(f)

# 初始化 wandb（可选）
initialize_wandb(evaluation_config, eval_dir='results', disable_wandb=True, project_name='my-project')

# 执行评估
evaluation(evaluation_config, eval_dir='results')

# 保存评估结果
save_evaluation_results('results')
```

## 5. 与 Pogema 的集成

Pogema-Toolbox 与 Pogema 环境无缝集成，可以直接使用 Pogema 的功能：

```python
from pogema_toolbox.create_env import create_env_base
from pogema_toolbox.registry import ToolboxRegistry

# 注册环境
ToolboxRegistry.register_env('Pogema-v0', create_env_base)

# 创建环境
env_config = {
    'num_agents': 8,
    'size': 16,
    'obs_radius': 5,
    'map_name': 'custom_map'
}
env = ToolboxRegistry.create_env('Pogema-v0', env_config)
```

## 6. 高级功能

### 6.1 配置变体生成器

Pogema-Toolbox 提供了配置变体生成器，可以自动生成多种配置组合：

```python
from pogema_toolbox.config_variant_generator import ConfigVariantGenerator

config = {
    'num_agents': {'grid_search': [4, 8, 16]},
    'size': {'grid_search': [16, 32]}
}

generator = ConfigVariantGenerator()
variants = generator.variants(config)

for variant in variants:
    print(variant)  # 输出所有配置组合
```

### 6.2 MovingAI 地图导入

Pogema-Toolbox 支持导入 MovingAI 格式的地图：

```python
from pogema_toolbox.moving_ai_ingestion import load_moving_ai_map

map_data = load_moving_ai_map('path/to/map.map')
ToolboxRegistry.register_maps({"moving_ai_map": map_data})
```

## 7. 总结

Pogema-Toolbox 是 Pogema 环境的强大扩展，提供了丰富的工具和功能，使多智能体路径规划算法的测试、评估和可视化变得简单高效。通过统一的接口和灵活的配置系统，用户可以轻松地：

- 注册和使用自定义算法
- 创建和管理自定义地图
- 进行分布式并行测试
- 可视化和分析评估结果

这使得 Pogema-Toolbox 成为研究和开发多智能体路径规划算法的理想工具。