# 贪心的assigner

import random


class RandomAssigner:
    def __init__(self, grid):
        self.grid = grid

    def assign(self, agent_idx, grid=None):
        grid = grid or self.grid
        # 随机找一个非障碍点
        return grid.sample_free_cell()
