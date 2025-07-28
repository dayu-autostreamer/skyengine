import yaml
from typing import List, Tuple

from sky_simulator.call_back.EnvCallback import EnvCallback
from sky_simulator.registry import register_component
from sky_simulator.packet_factory.packet_factory_env.Machine.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Agv.AGV import AGV
from sky_simulator.packet_factory.packet_factory_env.Utils.util import OperationStatus
from sky_simulator.packet_factory.packet_factory_env.Job.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Job.Job import Job
from sky_simulator.packet_factory.packet_factory_env.Graph.Graph import Point, Link, Graph
from sky_logs.logger import LOGGER
import dataset
import config



# 仿真环境创建前的初始化
@register_component("packet_factory_callback.MapLoader")
class FactoryMapLoader(EnvCallback):
    def __init__(self, dataset_file_path, config_file_path):
        super().__init__()
        self.dataset_file_path = dataset_file_path
        self.config_file_path = config_file_path

    def __call__(self):
        """使类的实例可以像函数一样被调用"""
        prefix = dataset.AGV_DATA_DIR
        file_path = prefix + self.dataset_file_path
        file_content = open(file_path, 'r').read()
        data = file_content.split()
        idx = 0

        n = int(data[idx])
        idx += 1
        m = int(data[idx])
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


        prefix = config.MAP_CONFIG_DIR
        file_path = prefix + self.config_file_path
        map_yaml = yaml.safe_load(open(file_path, 'rb'))
        map_config = map_yaml['config']
        
        points = []
        for point in map_config.get('points', []):
            p = point['point']
            points.append(Point(p['id'], p['coordinate'][0], p['coordinate'][1]))
        links = []
        for link in map_config.get('links', []):
            l = link['link']
            links.append(Link(l['id'], l['begin'], l['end']))
        graph = Graph(points, links)

        machines = []
        for machine in map_config.get('machines', []):
            m = machine['machine']
            point = graph.get_point_by_id(m['point_id'])
            if point is None:
                LOGGER.error(f"Point ID {m['point_id']} not found in the graph")
                continue
            machines.append(Machine(m['id'], point.x, point.y, m['point_id']))

        agvs = []
        for agv in map_config.get('agvs', []):
            a = agv['agv']
            point = graph.get_point_by_id(a['point_id'])
            if point is None:
                LOGGER.error(f"Point ID {a['point_id']} not found in the graph")
                continue
            agvs.append(AGV(a['id'], point.x, point.y, a['point_id'], a['velocity'], graph))
        
        return jobs, machines, agvs, graph
       


if __name__ == '__main__':
    mapLoader = FactoryMapLoader()
    print(mapLoader("/brandimarte/mk01.txt", "/map_config.yaml"))
