
---

# Pogema Grid 生成与分配函数文档

## 1️⃣ 概述

该文件提供了一系列工具函数，用于：

1. 随机生成网格障碍 (`generate_obstacles`)
2. 计算地图的连通分量 (`bfs` / `get_components`)
3. 快速或常规生成 agent 起点和目标位置 (`placing_fast`, `placing`, `generate_positions_and_targets_fast`)
4. 支持从指定可能位置生成起点/目标 (`generate_from_possible_positions`)
5. 为长期任务生成新目标 (`generate_new_target`)
6. 性能测试函数 (`time_it`)

它是 Pogema 内部网格初始化的核心逻辑基础。

---

## 2️⃣ 障碍生成

```python
def generate_obstacles(grid_config: GridConfig, rnd=None):
    if rnd is None:
        rnd = np.random.default_rng(grid_config.seed)
    return rnd.binomial(1, grid_config.density, (grid_config.size, grid_config.size))
```

### 功能

* 根据网格大小 `grid_config.size` 和障碍密度 `grid_config.density` 生成二值障碍矩阵：

  * `1` = 障碍
  * `0` = 空地
* 支持可复现随机种子 `grid_config.seed`

---

## 3️⃣ BFS 连通分量

```python
def bfs(grid, moves, size, start_id, free_cell):
    ...
```

### 功能

* 在网格中识别每个连通的空地区域，并给每个区域分配唯一 `component_id`。
* 输入：

  * `grid`：二维障碍矩阵
  * `moves`：可移动方向（例如上下左右）
  * `start_id`：用于标记第一个连通分量的编号
  * `free_cell`：空地标记值
* 输出：

  * `components`：列表，记录每个连通分量包含的格子数
* 算法：

  1. 遍历整个网格
  2. 对每个未标记空地执行 BFS，标记同一连通分量
  3. 返回每个连通分量大小

> 连通分量信息对生成合法 agent 起止点非常重要，保证 agent 起点和目标在同一连通区域。

---

## 4️⃣ agent/目标生成

### 4.1 常规放置算法

```python
def placing(order, components, grid, start_id, num_agents):
    ...
```

* 输入：

  * `order`：空地坐标列表（随机顺序）
  * `components`：连通分量大小列表
  * `grid`：带连通分量标记的网格
  * `start_id`：分量编号起始值
  * `num_agents`：agent 数量
* 输出：

  * `positions_xy`：agent 起点坐标
  * `finishes_xy`：agent 目标坐标
* 思路：

  1. 遍历空地，如果该分量可用（大小≥2），从队列中分配起点和目标
  2. 记录请求列表，确保每个 agent 有唯一目标
  3. 遍历直到生成 `num_agents` 对起止点

### 4.2 快速放置算法

```python
def placing_fast(order, components, grid, start_id, num_agents):
    ...
```

* 与 `placing` 类似，但使用链表索引映射方式，提高生成速度。
* 适合大规模环境或性能测试。

---

## 5️⃣ 从可能位置生成

```python
def generate_from_possible_positions(grid_config: GridConfig):
    ...
```

* 直接从用户提供的 `possible_agents_xy` 和 `possible_targets_xy` 中随机抽取 agent 起点和目标
* 确保数量足够
* 支持随机种子保证复现

---

## 6️⃣ 快速生成 agent 起点和目标

```python
def generate_positions_and_targets_fast(obstacles, grid_config):
    ...
```

* 输入：

  * `obstacles`：障碍矩阵
  * `grid_config`：配置对象
* 输出：

  * `positions_xy`：起点列表
  * `finishes_xy`：目标列表
* 流程：

  1. 复制障碍矩阵
  2. 用 BFS 标记连通分量
  3. 将空地坐标随机打乱 (`order`)
  4. 调用 `placing` 生成 agent 起点/目标对

---

## 7️⃣ 新目标生成

```python
def generate_from_possible_targets(rnd_generator, possible_positions, position)
def generate_new_target(rnd_generator, point_to_component, component_to_points, position)
```

* 支持为 agent 生成新的目标位置
* 可约束在同一连通分量内
* 用于长期任务或连续任务生成

---

## 8️⃣ 获取连通分量信息

```python
def get_components(grid_config, obstacles, positions_xy, target_xy):
    ...
```

* 输出：

  * `comp_to_points`：每个连通分量包含的所有坐标
  * `point_to_comp`：每个坐标所属连通分量编号
* 用于 agent 起点/目标检查和长期任务规划

---

## 9️⃣ 性能测试

```python
def time_it(func, num_iterations)
```

* 输入：

  * `func`：生成函数，例如 `generate_positions_and_targets_fast`
  * `num_iterations`：循环次数
* 输出：函数执行总耗时
* 用于对生成方法的性能评估

---

## 10️⃣ main 函数示例

```python
def main():
    num_iterations = 1000
    time_it(generate_positions_and_targets_fast, num_iterations=1)
    print('fast:', time_it(generate_positions_and_targets_fast, num_iterations=num_iterations))
```

* 单次生成测试
* 多次生成性能统计

---

## 11️⃣ 总结

* **核心功能**：障碍生成 → 连通分量分析 → agent 起点/目标分配
* **优化点**：

  * `placing_fast` 提升大规模地图的生成速度
  * 连通分量保证 agent 可以从起点到达目标
* **扩展性**：

  * 可以支持指定起点/目标位置
  * 可生成长期任务或动态目标

---

```
生成障碍 → BFS连通分量 → 打乱空地顺序 → placing(或placing_fast) → 生成agent起止点
```

