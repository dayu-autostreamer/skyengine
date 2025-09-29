
---

# Pogema Grid 类说明文档

## 1. 概述

`Grid` 类是 Pogema 环境中用于表示网格地图及 agent/目标状态的核心类。它封装了：

* 地图障碍信息 (`obstacles`)
* agent 的起始位置 (`starts_xy`)
* agent 的目标位置 (`finishes_xy`)
* agent 的当前位置 (`positions_xy`)
* agent 的活跃状态 (`is_active`)

该类支持**人工边界**扩展、位置验证、局部观察切片、以及 agent 移动操作。

`GridLifeLong` 是 `Grid` 的子类，增加了**连通分量分析**功能，用于长期任务或复杂连通性约束。

---

## 2. 初始化

```python
Grid(grid_config: GridConfig, add_artificial_border=True, num_retries=10)
```

### 参数

| 参数                      | 类型           | 说明                             |
| ----------------------- | ------------ | ------------------------------ |
| `grid_config`           | `GridConfig` | 网格配置对象，包含地图、障碍密度、agent数量、视野半径等 |
| `add_artificial_border` | `bool`       | 是否在地图周围添加人工障碍边界                |
| `num_retries`           | `int`        | 在生成 agent/目标位置时的最大重试次数         |

### 初始化流程

1. 根据 `grid_config.map` 或随机生成障碍 (`generate_obstacles`) 初始化地图。
2. 处理 agent 的起止点：

   * 如果提供 `agents_xy` 和 `targets_xy`，直接使用；
   * 否则从可能的位置生成 (`generate_from_possible_positions`) 或快速随机生成 (`generate_positions_and_targets_fast`)。
3. 校验位置有效性，尝试重试 `num_retries` 次以生成合法配置。
4. 如果 `add_artificial_border=True`，调用 `add_artificial_border()` 增加地图边界。
5. 初始化 `positions` 矩阵和 `_initial_xy` 记录 agent 初始位置。

---

## 3. 属性说明

| 属性             | 类型                     | 说明                        |
| -------------- | ---------------------- | ------------------------- |
| `obstacles`    | `np.ndarray`           | 地图障碍信息，0=空地，1=障碍          |
| `starts_xy`    | `List[Tuple[int,int]]` | agent 起始位置                |
| `finishes_xy`  | `List[Tuple[int,int]]` | agent 目标位置                |
| `positions`    | `np.ndarray`           | agent 实时占据状态矩阵，0=空地，1=被占据 |
| `positions_xy` | `List[Tuple[int,int]]` | agent 当前坐标                |
| `_initial_xy`  | `List[Tuple[int,int]]` | agent 初始位置副本              |
| `is_active`    | `Dict[int,bool]`       | 每个 agent 的活跃状态            |

---

## 4. 核心方法

### 4.1 边界处理

```python
add_artificial_border()
```

* 在地图周围增加障碍边界（厚度=`obs_radius`），可选择保留外围空地或随机障碍。

### 4.2 获取障碍信息

```python
get_obstacles(ignore_borders=False) -> np.ndarray
```

* 返回地图障碍矩阵，可选择忽略人工边界。

### 4.3 获取 agent/目标坐标

```python
get_agents_xy(only_active=False, ignore_borders=False) -> List[Tuple[int,int]]
get_targets_xy(only_active=False, ignore_borders=False) -> List[Tuple[int,int]]
```

* 返回 agent 或目标的坐标，支持：

  * `only_active`：仅返回活跃 agent
  * `ignore_borders`：忽略人工边界偏移

### 4.4 相对坐标

```python
get_agents_xy_relative()
get_targets_xy_relative()
```

* 返回 agent/目标相对于初始位置的偏移量 `(dx, dy)`。

### 4.5 状态与观察

```python
get_state(ignore_borders=False, as_dict=False) -> np.ndarray or dict
get_observation_shape() -> Tuple[int,int,int]
get_num_actions() -> int
get_obstacles_for_agent(agent_id) -> np.ndarray
get_positions(agent_id) -> np.ndarray
get_target(agent_id) -> Tuple[float,float]
get_square_target(agent_id) -> np.ndarray
```

* `get_state` 返回 agent 坐标、目标坐标、障碍的全局状态，可选择字典格式。
* `get_obstacles_for_agent` / `get_positions` 返回局部观测，大小为 `(2*obs_radius+1)^2`。
* `get_target` 返回归一化的目标方向向量。
* `get_square_target` 返回局部目标矩阵，用于局部感知的目标表示。

### 4.6 移动操作

```python
move(agent_id, action)
move_without_checks(agent_id, action)
move_agent_to_cell(agent_id, x, y)
```

* `move` 根据动作更新 agent 位置，自动检查障碍和冲突。
* `move_without_checks` 忽略障碍和冲突，直接移动。
* `move_agent_to_cell` 强制将 agent 移到指定位置（用于初始化或调试）。

### 4.7 Agent 状态管理

```python
on_goal(agent_id) -> bool
hide_agent(agent_id) -> bool
show_agent(agent_id) -> bool
```

* 检查 agent 是否到达目标。
* 隐藏/显示 agent（更新 `is_active` 和 `positions`）。

### 4.8 渲染

```python
render(mode='human')
```

* 使用 Pogema 内部的 `render_grid` 显示地图、agent、目标和障碍。

---

## 5. GridLifeLong 子类

```python
class GridLifeLong(Grid)
```

* 在 `Grid` 的基础上增加**连通分量分析**：

  * `component_to_points`：每个连通组件的所有点
  * `point_to_component`：每个点所属连通组件
* 生成时会检查 agent 起点和目标是否在同一组件，不在则发出警告并修改目标。

---

## 6. 使用示例

```python
from pogema.grid_registry import get_grid
from pogema.grid_config import GridConfig

config = GridConfig(map_name=None, num_agents=3, height=10, width=10, density=0.2, seed=42)
grid = Grid(config)

print(grid.get_obstacles())
print(grid.get_agents_xy())
print(grid.get_targets_xy())

grid.render()
```

---

## 7. 注意事项

* `obs_radius` 参数影响局部观察大小和人工边界厚度。
* 初始化时，如果地图障碍太密或 agent/目标过多，可能无法生成合法配置。
* `positions` 矩阵用于内部冲突检测，不应直接修改。
* 如果要与 Machine 或 AGV 协同，需要在空地上生成逻辑节点，并在 agent 目标中使用其位置。

---

