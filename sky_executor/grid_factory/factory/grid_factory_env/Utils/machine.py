import random
from typing import List, Tuple
from collections import deque
from sky_executor.grid_factory.factory.grid_factory_env.Utils.structure import (
    Machine,
    MachineConfig,
)


class MachineGenerator:
    """多策略机器生成器"""

    def __init__(self, grid: List[List[int]], config: MachineConfig):
        self.grid = grid
        self.cfg = config
        self.height = len(grid)
        self.width = len(grid[0]) if self.height else 0

        if not self.height or not self.width:
            raise ValueError("Grid is empty")

    # ========= 工具函数 =========
    def _is_inner_cell(self, r: int, c: int) -> bool:
        """判断是否为可用的非边界空格"""
        return (
            1 <= r < self.height - 1
            and 1 <= c < self.width - 1
            and self.grid[r][c] == 0
        )

    def _get_empty_cells(self) -> List[Tuple[int, int]]:
        """获取所有可用空格"""
        return [
            (r, c)
            for r in range(self.height)
            for c in range(self.width)
            if self._is_inner_cell(r, c)
        ]

    def _is_connected(self, positions: List[Tuple[int, int]]) -> bool:
        """检查机器点是否在同一连通区域（4邻域）"""
        if not positions:
            return True

        grid = [
            [self.grid[r][c] for c in range(self.width)] for r in range(self.height)
        ]
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
        selected = []
        n_side = int(self.cfg.num_machines**0.5) + 1
        for i in range(n_side):
            for j in range(n_side):
                if len(selected) >= self.cfg.num_machines:
                    break
                x, y = i * self.cfg.grid_spacing, j * self.cfg.grid_spacing
                if self._is_inner_cell(x, y):
                    selected.append((x, y))
        # 补足数量
        if len(selected) < self.cfg.num_machines:
            remaining = [c for c in self._get_empty_cells() if c not in selected]
            random.shuffle(remaining)
            selected += remaining[: self.cfg.num_machines - len(selected)]
        return selected

    def _generate_grid_noise(self) -> List[Tuple[int, int]]:
        selected = []
        n_side = int(self.cfg.num_machines**0.5) + 1
        for i in range(n_side):
            for j in range(n_side):
                if len(selected) >= self.cfg.num_machines:
                    break
                x = int(
                    round(
                        i * self.cfg.grid_spacing
                        + random.uniform(-self.cfg.noise, self.cfg.noise)
                    )
                )
                y = int(
                    round(
                        j * self.cfg.grid_spacing
                        + random.uniform(-self.cfg.noise, self.cfg.noise)
                    )
                )
                x = max(1, min(x, self.height - 2))
                y = max(1, min(y, self.width - 2))
                if self._is_inner_cell(x, y) and (x, y) not in selected:
                    selected.append((x, y))
        # 补足数量
        if len(selected) < self.cfg.num_machines:
            remaining = [c for c in self._get_empty_cells() if c not in selected]
            random.shuffle(remaining)
            selected += remaining[: self.cfg.num_machines - len(selected)]
        return selected

    def _generate_zones(self) -> List[Tuple[int, int]]:
        selected = []
        zone_h = max(1, self.height // self.cfg.zones)
        zone_w = max(1, self.width // self.cfg.zones)
        for i in range(self.cfg.zones):
            for j in range(self.cfg.zones):
                if len(selected) >= self.cfg.num_machines:
                    break
                r0, r1 = max(1, i * zone_h), min((i + 1) * zone_h, self.height - 1)
                c0, c1 = max(1, j * zone_w), min((j + 1) * zone_w, self.width - 1)
                candidates = [
                    (r, c)
                    for r in range(r0, r1)
                    for c in range(c0, c1)
                    if self._is_inner_cell(r, c)
                ]
                if candidates:
                    random.shuffle(candidates)
                    selected.append(candidates[0])
        if len(selected) < self.cfg.num_machines:
            remaining = [c for c in self._get_empty_cells() if c not in selected]
            random.shuffle(remaining)
            selected += remaining[: self.cfg.num_machines - len(selected)]
        return selected

    # ========= 主入口 =========
    def generate(self) -> List[Machine]:
        random.seed(self.cfg.seed)

        strategy_fn = {
            "random": self._generate_random,
            "grid": self._generate_grid,
            "grid+noise": self._generate_grid_noise,
            "zones": self._generate_zones,
        }.get(self.cfg.strategy)

        if strategy_fn is None:
            raise ValueError(f"Unknown strategy: {self.cfg.strategy}")

        candidates = strategy_fn()

        # 过滤非法点（落入障碍或边界）
        valid = [(r, c) for r, c in candidates if self._is_inner_cell(r, c)]
        if len(valid) < self.cfg.num_machines:
            remaining = [c for c in self._get_empty_cells() if c not in valid]
            random.shuffle(remaining)
            valid += remaining[: self.cfg.num_machines - len(valid)]

        # ✅ 检查连通性，如果不连通则重新生成（最多尝试3次）
        for _ in range(3):
            if self._is_connected(valid):
                break
            random.shuffle(valid)

        return [Machine(i, loc) for i, loc in enumerate(valid[: self.cfg.num_machines])]


def generate_machines(
    grid: List[List[int]], machine_config: MachineConfig
) -> List[Machine]:
    return MachineGenerator(grid, machine_config).generate()


if __name__ == "__main__":
    grid = [
        [0, 0, 0, 0, 0, 0],
        [0, 1, 1, 0, 1, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0],
    ]
    config = MachineConfig(num_machines=6, strategy="grid+noise", seed=123, noise=1.5)
    machines = generate_machines(grid, config)
    for m in machines:
        print(m)
