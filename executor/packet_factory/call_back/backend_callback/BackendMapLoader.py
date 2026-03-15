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
import yaml
import config
from executor.packet_factory.registry import component_registry
from executor.packet_factory.logger.logger import LOGGER

@register_component("backend_callback.MapLoader")
class FactoryMapLoader(EnvCallback):
    def __init__(self):
        super().__init__()
        self.env_type=component_registry.get('config').get('env_type')
        self.config=component_registry.get('config').get(self.env_type)
        self.job_config_file_path =  self.config.get("task_config").get('file')    # 对应 job_config.yaml
        self.map_config_file_path =  self.config.get("factory_config").get('file') # 对应 map_config.yaml
        
        map_file = self.map_config_file_path
        map_yaml = yaml.safe_load(open(map_file, 'rb'))
        self.map_config = map_yaml['config']


    def create_jobs(self):
        job_file = self.job_config_file_path
        job_yaml = yaml.safe_load(open(job_file, 'rb'))
        job_config = job_yaml['config']

        jobs = []
        operation_count = 0
        for job_entry in job_config.get('jobs', []):
            job_data = job_entry['job']
            operations: List[Operation] = []
            for op_entry in job_data.get('operations', []):
                op_data = op_entry['operation']
                durations = [
                    (int(m['id']), float(m['time']))
                    for m in op_data.get('machines', [])
                ]
                operations.append(Operation(operation_count, OperationStatus.WAITING, durations))
                operation_count += 1
            jobs.append(Job(job_data['id'], operations))
        
        return jobs

    def create_graph(self):
        map_config = self.map_config

        points = []
        for point in map_config.get('points', []):
            p = point['point']
            points.append(Point(p['id'], p['coordinate'][0], p['coordinate'][1]))

        links = []
        for link in map_config.get('links', []):
            l = link['link']
            links.append(Link(l['id'], l['begin'], l['end']))

        graph = Graph(points, links)
        return graph

    def create_machines(self, graph: Graph):
        machines = []
        for machine in self.map_config.get('machines', []):
            m = machine['machine']
            point = graph.get_point_by_id(m['point_id'])
            if point is None:
                LOGGER.error(f"Machine Point ID {m['point_id']} not found in the graph")
                continue
            machines.append(Machine(m['id'], point.x, point.y, m['point_id']))
        return machines

    def create_agvs(self, graph: Graph):
        agvs = []
        for agv in self.map_config.get('agvs', []):
            a = agv['agv']
            point = graph.get_point_by_id(a['point_id'])
            if point is None:
                LOGGER.error(f"AGV Point ID {a['point_id']} not found in the graph")
                continue
            agvs.append(AGV(a['id'], point.x, point.y, a['point_id'], a['velocity'], graph))
        return agvs

    def __call__(self):
        jobs: List[Job] = self.create_jobs()
        graph: Graph = self.create_graph()
        machines: List[Machine] =self.create_machines(graph=graph)
        agvs: List[AGV] = self.create_agvs(graph=graph)

        return jobs, machines, agvs, graph

if __name__ == '__main__':
    mapLoader = FactoryMapLoader()
    print(mapLoader())
