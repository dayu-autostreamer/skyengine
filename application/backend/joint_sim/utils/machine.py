import random
from typing import List, Tuple
from collections import deque
from joint_sim.utils.structure import (
    Machine,
    MachineConfig,
)


class MachineGenerator:
    """多策略机器生成器（带内部区域检测）"""

    def __init__(self, grid: List[List[int]], config: MachineConfig):
        self.grid = grid
        self.cfg = config
        self.height = len(grid)
        self.width = len(grid[0]) if self.height else 0

        if not self.height or not self.width:
            raise ValueError("Grid is empty")

        # ✅ 初始化时自动检测“内部连通区域”
        self.inner_area = self._get_inner_area_by_bounding_box()

    # ========= 工具函数 =========
    def _is_valid(self, r: int, c: int) -> bool:
        return 0 <= r < self.height and 0 <= c < self.width

    def _get_inner_area_by_bounding_box(self) -> List[Tuple[int, int]]:
        """基于外层边界的内区提取（假设外圈为1）"""
        ones = [(r, c)
                for r in range(self.height)
                for c in range(self.width)
                if self.grid[r][c] == 1]

        if not ones:
            raise ValueError("Grid has no obstacles (1s), cannot find boundary.")

        # 找到外圈边界框
        min_r = min(r for r, _ in ones)
        max_r = max(r for r, _ in ones)
        min_c = min(c for _, c in ones)
        max_c = max(c for _, c in ones)

        # 内部有效区域（排除边界1）
        inner_area = []
        for r in range(min_r + 1, max_r):
            for c in range(min_c + 1, max_c):
                if self.grid[r][c] == 0:
                    inner_area.append((r, c))

        return inner_area

    def _get_largest_connected_region(self) -> List[Tuple[int, int]]:
        """找到地图中最大的连通0区域（四邻域）"""
        visited = [[False] * self.width for _ in range(self.height)]
        regions = []
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        for r in range(self.height):
            for c in range(self.width):
                if self.grid[r][c] == 0 and not visited[r][c]:
                    region = []
                    q = deque([(r, c)])
                    visited[r][c] = True
                    while q:
                        x, y = q.popleft()
                        region.append((x, y))
                        for dx, dy in dirs:
                            nx, ny = x + dx, y + dy
                            if (
                                    self._is_valid(nx, ny)
                                    and not visited[nx][ny]
                                    and self.grid[nx][ny] == 0
                            ):
                                visited[nx][ny] = True
                                q.append((nx, ny))
                    regions.append(region)

        # ✅ 选择最大的那块区域
        if not regions:
            raise ValueError("No free space found in grid!")

        largest = max(regions, key=len)
        return largest

    def _get_empty_cells(self) -> List[Tuple[int, int]]:
        """仅从内部区域中取可用点"""
        return list(self.inner_area)

    def _is_inner_cell(self, r: int, c: int) -> bool:
        """是否在内部区域"""
        return (r, c) in self.inner_area

    def _is_connected(self, positions: List[Tuple[int, int]]) -> bool:
        """检查机器点是否在同一连通区域"""
        if not positions:
            return True

        visited = set()
        q = deque([positions[0]])
        visited.add(positions[0])
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        while q:
            r, c = q.popleft()
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if (nr, nc) in positions and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    q.append((nr, nc))

        return len(visited) == len(positions)

    # ========= 策略实现 =========
    def _generate_random(self) -> List[Tuple[int, int]]:
        cells = self._get_empty_cells()
        random.shuffle(cells)
        return cells[: self.cfg.num_machines]

    def _generate_grid(self) -> List[Tuple[int, int]]:
        cells = self._get_empty_cells()
        selected = []
        if not cells:
            return selected

        min_r = min(r for r, _ in cells)
        min_c = min(c for _, c in cells)

        n_side = int(self.cfg.num_machines ** 0.5) + 1
        for i in range(n_side):
            for j in range(n_side):
                if len(selected) >= self.cfg.num_machines:
                    break
                x = min_r + i * self.cfg.grid_spacing
                y = min_c + j * self.cfg.grid_spacing
                if (x, y) in cells:
                    selected.append((x, y))
        return selected

    def _generate_grid_noise(self) -> List[Tuple[int, int]]:
        base = self._generate_grid()
        noisy = []
        for (x, y) in base:
            nx = int(round(x + random.uniform(-self.cfg.noise, self.cfg.noise)))
            ny = int(round(y + random.uniform(-self.cfg.noise, self.cfg.noise)))
            if (nx, ny) in self.inner_area:
                noisy.append((nx, ny))
        if len(noisy) < self.cfg.num_machines:
            remain = [p for p in self.inner_area if p not in noisy]
            random.shuffle(remain)
            noisy += remain[: self.cfg.num_machines - len(noisy)]
        return noisy
    def _generate_custom(self) -> List[Tuple[int, int]]:
        """使用预定义的自定义位置"""
        if not self.cfg.custom_positions:
            raise ValueError("custom_positions is required when strategy='custom'")
        return self.cfg.custom_positions[:self.cfg.num_machines]
    def _generate_zones(self) -> List[Tuple[int, int]]:
        """内部区域按分区选点"""
        cells = self._get_empty_cells()
        if not cells:
            return []

        rs = [r for r, _ in cells]
        cs = [c for _, c in cells]
        min_r, max_r = min(rs), max(rs)
        min_c, max_c = min(cs), max(cs)

        zone_h = max(1, (max_r - min_r + 1) // self.cfg.zones)
        zone_w = max(1, (max_c - min_c + 1) // self.cfg.zones)

        selected = []
        for i in range(self.cfg.zones):
            for j in range(self.cfg.zones):
                if len(selected) >= self.cfg.num_machines:
                    break
                r0, r1 = min_r + i * zone_h, min_r + (i + 1) * zone_h
                c0, c1 = min_c + j * zone_w, min_c + (j + 1) * zone_w
                region = [
                    (r, c)
                    for (r, c) in cells
                    if r0 <= r < r1 and c0 <= c < c1
                ]
                if region:
                    random.shuffle(region)
                    selected.append(region[0])

        if len(selected) < self.cfg.num_machines:
            remain = [p for p in cells if p not in selected]
            random.shuffle(remain)
            selected += remain[: self.cfg.num_machines - len(selected)]
        return selected

    # ========= 主入口 =========
    def generate(self) -> List[Machine]:
        random.seed(self.cfg.seed)
        strategy_fn = {
            "random": self._generate_random,
            "grid": self._generate_grid,
            "grid+noise": self._generate_grid_noise,
            "zones": self._generate_zones,
            "custom": self._generate_custom,  # 新增
        }.get(self.cfg.strategy)

        if strategy_fn is None:
            raise ValueError(f"Unknown strategy: {self.cfg.strategy}")

        candidates = strategy_fn()
        if len(candidates) < self.cfg.num_machines:
            remain = [p for p in self.inner_area if p not in candidates]
            random.shuffle(remain)
            candidates += remain[: self.cfg.num_machines - len(candidates)]

        return [Machine(i, loc) for i, loc in enumerate(candidates[: self.cfg.num_machines])]


def generate_machines(grid: List[List[int]], machine_config: MachineConfig) -> List[Machine]:
    return MachineGenerator(grid, machine_config).generate()


def revert_to_relative(machines: List[Machine], padding: int = 4):
    """输入绝对,转换为相对"""
    for m in machines:
        m.location = (m.location[0] - padding , m.location[1] - padding)
    return machines


def revert_to_absolute(machines: List[Machine], padding: int = 4):
    """输入相对,转换为绝对"""
    for m in machines:
        m.location = (m.location[0] + padding, m.location[1] + padding)
    return machines


if __name__ == "__main__":
    # print(1.0==1)
    grid = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
    new_grid = grid
    config = MachineConfig(num_machines=6, strategy="grid+noise", seed=123, noise=1.5)
    machines = generate_machines(grid, config)
    new_machines = revert_to_pogema(machines, padding=1)
    for m in machines:
        new_grid[m.location[0]][m.location[1]] = 233
        print(m)
    print(new_grid)
    new_grid = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 233, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 233, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 233, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 233, 0.0, 1.0, 1.0, 0.0, 233, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 233, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
