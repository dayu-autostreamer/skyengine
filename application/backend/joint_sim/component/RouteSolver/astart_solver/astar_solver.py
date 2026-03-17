'''
@Project ：SkyEngine 
@File    ：astar_solver.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/4 23:01
'''

import numpy as np
from heapq import heappop, heappush
from pogema import GridConfig
from joint_sim.component.RouteSolver.route_solver_factory import \
    RouteSolverFactory
from joint_sim.component.RouteSolver.template_solver.route_solver import \
    RouteSolver


@RouteSolverFactory.register_solver("astar")
class AStarRouteSolver(RouteSolver):
    def __init__(self, random_seed=42, random_rate=0.2):
        """
        RouteSolver 与环境绑定。
        env 通常是 Pogema 式的多智能体网格环境。
        """
        super().__init__()
        self.agents = None
        self.actions = {tuple(GridConfig().MOVES[i]): i for i in
                        range(len(GridConfig().MOVES))}  # make a dictionary to translate coordinates of action into id
        self.obs_radius = GridConfig().obs_radius
        self._rnd = np.random.RandomState(random_seed)
        self._random_rate = random_rate

    def get_goal(self, obs):
        goal = np.nonzero(obs[2])
        goal_i = goal[0][0]
        goal_j = goal[1][0]
        if obs[0][goal_i][goal_j]:
            goal_i -= 1 if goal_i == 0 else 0
            goal_i += 1 if goal_i == self.obs_radius * 2 else 0
            goal_j -= 1 if goal_j == 0 else 0
            goal_j += 1 if goal_j == self.obs_radius * 2 else 0
        return goal_i, goal_j

    def plan(self, obs: dict) -> list:
        """
        核心接口：根据当前环境状态和待搬运任务，输出每个agent的动作。

        输入:
        ------
        obs : dict
            当前环境观测，包含每个AGV的局部视野等信息。
            通常来源于 env.step() 或 env.reset() 返回。
        输出:
        ------
        agent_actions : list[int]
            每个AGV在当前时间步要执行的动作（例如0=stay, 1=up, 2=down, 3=left, 4=right）
            格式直接兼容 Pogema 的输入:
                env.step({'agent_actions': agent_actions, 'machine_actions': machine_actions})
        """
        if self.agents is None:
            self.obs_radius = len(obs[0][0]) // 2
            self.agents = [AStar() for _ in range(len(obs))]  # create a planner for each of the agents
        actions = []
        for k in range(len(obs)):
            start = (self.obs_radius, self.obs_radius)
            goal = self.get_goal(obs[k])
            if start == goal:  # don't waste time on the agents that have already reached their goals
                actions.append(0)  # just add useless action to save the order and length of the actions
                continue
            self.agents[k].update_obstacles(obs[k][0], obs[k][1])
            self.agents[k].update_path(start, goal)
            next_node = self.agents[k].get_next_node()
            actions.append(self.actions[(next_node[0] - start[0], next_node[1] - start[1])])
        for idx, action in enumerate(actions):
            if self._rnd.random() < self._random_rate:
                actions[idx] = self._rnd.randint(1, 4)
        return actions


INF = 1000000007


class Node:
    def __init__(self, coord=(INF, INF), g: int = 0, h: int = 0):
        self.i, self.j = coord
        self.g = g
        self.h = h
        self.f = g + h

    def __lt__(self, other):
        return self.f < other.f or ((self.f == other.f) and (self.g < other.g))


class AStar:
    def __init__(self):
        self.start = (0, 0)
        self.goal = (0, 0)
        self.max_steps = 500
        self.OPEN = list()
        self.CLOSED = dict()
        self.obstacles = set()
        self.other_agents = set()
        self.best_node = Node(self.start, 0, self.h(self.start))

    def h(self, node):
        return abs(node[0] - self.goal[0]) + abs(node[1] - self.goal[1])

    def get_neighbours(self, u):
        neighbors = []
        for d in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            if (u[0] + d[0], u[1] + d[1]) not in self.obstacles:
                neighbors.append((u[0] + d[0], u[1] + d[1]))
        return neighbors

    def compute_shortest_path(self):
        u = Node()
        steps = 0
        while len(self.OPEN) > 0 and steps < self.max_steps and (u.i, u.j) != self.goal:
            u = heappop(self.OPEN)
            if self.best_node.h > u.h:
                self.best_node = u
            steps += 1
            for n in self.get_neighbours((u.i, u.j)):
                if n not in self.CLOSED and n not in self.other_agents:
                    heappush(self.OPEN, Node(n, u.g + 1, self.h(n)))
                    self.CLOSED[n] = (u.i, u.j)

    def get_next_node(self):
        next_node = self.start
        if self.goal in self.CLOSED:
            next_node = self.goal
            while self.CLOSED[next_node] != self.start:
                next_node = self.CLOSED[next_node]
        return next_node

    def update_obstacles(self, obs, other_agents):
        obstacles = np.nonzero(obs)
        self.obstacles.clear()
        for k in range(len(obstacles[0])):
            self.obstacles.add((obstacles[0][k], obstacles[1][k]))
        self.other_agents.clear()
        agents = np.nonzero(other_agents)
        for k in range(len(agents[0])):
            self.other_agents.add((agents[0][k], agents[1][k]))

    def reset(self):
        self.CLOSED = dict()
        self.OPEN = list()
        heappush(self.OPEN, Node(self.start, 0, self.h(self.start)))
        self.best_node = Node(self.start, 0, self.h(self.start))

    def update_path(self, start, goal):
        self.start = start
        self.goal = goal
        self.reset()
        self.compute_shortest_path()
