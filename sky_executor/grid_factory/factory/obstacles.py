"""Shared logical-grid obstacle policy, independent of fault clocks and devices."""
from collections import deque
from typing import Tuple, Optional


def can_block_cell(state, size, cell, *, preserve_connectivity=True):
    width, height = size
    if (len(cell) != 2 or any(type(v) is not int for v in cell)
            or not 0 <= cell[0] < width or not 0 <= cell[1] < height):
        return False
    if not preserve_connectivity:
        return True
    grid = state.grid.obstacles
    return walkable_component_count(grid) >= walkable_component_count(grid, state._to_internal_xy(cell))


def walkable_component_count( grid, blocked_cell: Optional[Tuple[int, int]] = None) -> int:
    visited = set()
    components = 0
    height, width = grid.shape

    def is_walkable(cell: Tuple[int, int]) -> bool:
        if blocked_cell is not None and cell == blocked_cell:
            return False
        return int(grid[cell]) == 0

    for i in range(height):
        for j in range(width):
            start = (i, j)
            if start in visited or not is_walkable(start):
                continue
            components += 1
            queue = deque([start])
            visited.add(start)
            while queue:
                cur_i, cur_j = queue.popleft()
                for nxt in (
                    (cur_i - 1, cur_j),
                    (cur_i + 1, cur_j),
                    (cur_i, cur_j - 1),
                    (cur_i, cur_j + 1),
                ):
                    ni, nj = nxt
                    if not (0 <= ni < height and 0 <= nj < width):
                        continue
                    if nxt in visited or not is_walkable(nxt):
                        continue
                    visited.add(nxt)
                    queue.append(nxt)
    return components
