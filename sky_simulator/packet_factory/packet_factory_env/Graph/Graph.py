from typing import List, Dict, Optional, Tuple
import math
from heapq import heappush, heappop

class Point:
    def __init__(self, id, x, y):
        self.id = id
        self.x = x
        self.y = y
    
    def get_xy(self) -> Tuple[float, float]:
        return self.x, self.y

class Link:
    def __init__(self, id, point1, point2):
        self.id = id
        self.point1 = point1
        self.point2 = point2
        self.weight = 1.0

class Graph:
    def __init__(self, points: List[Point], links: List[Link]):
        self.points = points
        self.links = links
        self.adj_map = {}  # 邻接表：{point_id: [(neighbor_id, weight)]}
        self.path_cache = {}  # 路径缓存：{src_id: {dst_id: [path]}}
        self._build_adjacency_map()
        self._precompute_all_paths()

        
    def get_weight(self, link):
        point1 = self.get_point_by_id(link.point1)
        point2 = self.get_point_by_id(link.point2)
        dx = point1.x - point2.x
        dy = point1.y - point2.y
        return math.hypot(dx, dy)  # 欧氏距离

    def get_point_by_id(self, point_id):
        for point in self.points:
            if point.id == point_id:
                return point
        return None

    def _build_adjacency_map(self):
        """构建带权重的邻接表"""
        self.adj_map.clear()
        for point in self.points:
            self.adj_map[point.id] = []

        for link in self.links:
            p1 = link.point1
            p2 = link.point2
            link.weight = self.get_weight(link)
            self.adj_map[p1].append((p2, link.weight))
            self.adj_map[p2].append((p1, link.weight))  # 无向图

    def dijkstra_shortest_path(self, start_id) -> Optional[List[int]]:
        """使用 Dijkstra 算法找出从 start_id 出发的最短路径"""
        if start_id not in self.adj_map:
            return None

        # (distance, current_node, path)
        heap = [(0, start_id, [start_id])]
        visited = set()

        while heap:
            dist, current, path = heappop(heap)

            if current in visited:
                continue

            visited.add(current)

            self.path_cache[start_id][current] = path if path is not None else []

            for neighbor, weight in self.adj_map[current]:
                if neighbor not in visited:
                    heappush(heap, (dist + weight, neighbor, path + [neighbor]))

        return None  # 没有找到路径

    def _precompute_all_paths(self):
        """预处理所有点对之间的最短路径"""
        self.path_cache.clear()
        all_ids = list(self.adj_map.keys())
        for src in all_ids:
            self.path_cache[src] = {}
            self.dijkstra_shortest_path(src)

    def get_path(self, source_id, target_id) -> List[int]:
        """O(1) 查询从 source_id 到 target_id 的最短路径"""
        return self.path_cache.get(source_id, {}).get(target_id, [])
    

if __name__ == '__main__':
    # 构造点和边
    p1 = Point(1, 0, 0)
    p2 = Point(2, 3, 4)
    p3 = Point(3, 6, 8)
    p4 = Point(4, 0, 10)


    l1 = Link(1, 1, 2)
    l2 = Link(2, 2, 3)
    l3 = Link(3, 3, 4)
    l4 = Link(4, 1, 4)

    graph = Graph([p1, p2, p3, p4], [l1, l2, l3, l4])

    # 获取路径
    print(graph.get_path(1, 3))  