from typing import List, Tuple

from executor.packet_factory.call_back.EnvCallback import EnvCallback
from executor.packet_factory.registry import register_component
from executor.packet_factory.packet_factory.packet_factory_env.Machine.Machine import Machine
from executor.packet_factory.packet_factory.packet_factory_env.Agv.AGV import AGV
from executor.packet_factory.packet_factory.packet_factory_env.Utils.util import OperationStatus
from executor.packet_factory.packet_factory.packet_factory_env.Job.Operation import Operation
from executor.packet_factory.packet_factory.packet_factory_env.Job.Job import Job
from executor.packet_factory.packet_factory.packet_factory_env.Graph.Graph import Point, Link, Graph
import dataset


# 仿真环境创建前的初始化
@register_component("base_callback.MapLoader")
class EnvMapLoader(EnvCallback):
    def __init__(self, _relative_file_path):
        super().__init__()
        self.relative_file_path = _relative_file_path

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        prefix = dataset.AGV_DATA_DIR
        file_path = prefix + self.relative_file_path
        file_content = open(file_path, 'r').read()
        data = file_content.split()
        idx = 0

        n = int(data[idx])
        idx += 1
        m = int(data[idx])
        idx += 1
        k = int(data[idx])
        idx += 1

        jobs: List[Job] = []
        operation_count = 0
        for job_id in range(n):
            num_operations = int(data[idx])
            idx += 1
            operations: List[Operation] = []
            for _ in range(num_operations):
                num_machines = int(data[idx])
                idx += 1
                durations: List[Tuple[int, float]] = []
                for _ in range(num_machines):
                    machine_id = int(data[idx])
                    idx += 1
                    duration = float(data[idx])
                    idx += 1
                    durations.append((machine_id, duration))
                operations.append(Operation(operation_count, OperationStatus.WAITING, durations))
                operation_count += 1
            jobs.append(Job(job_id, operations))

        machines: List[Machine] = []
        points: List[Point] = []
        for i in range(m):
            x = float(data[idx])
            idx += 1
            y = float(data[idx])
            idx += 1
            points.append(Point(i, x, y))
            machines.append(Machine(i, x, y, i))
        
        links: List[Link] = []
        link_count = 0
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                links.append(Link(link_count, i, j))
        
        graph = Graph(points, links)

        agvs: List[AGV] = []
        for i in range(k):
            x = float(data[idx])
            idx += 1
            y = float(data[idx])
            idx += 1
            velocity = float(data[idx])
            idx += 1
            agvs.append(AGV(i, x, y, i, velocity, graph))

        return jobs, machines, agvs, graph


if __name__ == '__main__':
    mapLoader = EnvMapLoader()
    print(mapLoader("/brandimarte/simple_agv.txt"))
