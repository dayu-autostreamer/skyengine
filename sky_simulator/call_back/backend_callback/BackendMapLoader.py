from typing import List, Tuple

from sky_simulator.call_back.EnvCallback import EnvCallback
from sky_simulator.registry import register_component
from sky_simulator.packet_factory.packet_factory_env.Machine.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Agv.AGV import AGV
from sky_simulator.packet_factory.packet_factory_env.Utils.util import OperationStatus
from sky_simulator.packet_factory.packet_factory_env.Job.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Job.Job import Job
from sky_simulator.packet_factory.packet_factory_env.Graph.Graph import Point, Link, Graph
import dataset
import yaml
import config
from sky_simulator.registry import component_registry
from sky_logs.logger import LOGGER

@register_component("backend_callback.MapLoader")
class FactoryMapLoader(EnvCallback):
    def __init__(self):
        super().__init__()
        self.env_type=component_registry.get('config').get('env_type')
        self.config=component_registry.get('config').get(self.env_type)
        self.job_config_file_path =  self.config.get("task_config").get('file')    # 对应 job_config.yaml
        self.map_config_file_path =  self.config.get("factory_config").get('file') # 对应 map_config.yaml

        self.jobs: List[Job] = []
        self.machines: List[Machine] = []
        self.agvs: List[AGV] = []
        self.graph: List[Graph] = []

        self.create_jobs()
        self.create_graph()
        self.create_machines()
        self.create_agvs()

    def create_jobs(self):
        job_file =self.job_config_file_path
        print(job_file)
        job_yaml = yaml.safe_load(open(job_file, 'rb'))
        job_config = job_yaml['config']

        self.jobs = []
        operation_count = 0
        for job_entry in job_config.get('jobs', []):
            job_data = job_entry['job']
            operations: List[Operation] = []
            for op_data in job_data.get('operations', []):
                durations = [
                    (int(m['id']), float(m['time']))
                    for m in op_data.get('machines', [])
                ]
                operations.append(Operation(operation_count, OperationStatus.WAITING, durations))
                operation_count += 1
            self.jobs.append(Job(job_data['id'], operations))

    def create_graph(self):
        map_file = self.map_config_file_path
        map_yaml = yaml.safe_load(open(map_file, 'rb'))
        map_config = map_yaml['config']

        points = []
        for point in map_config.get('points', []):
            p = point['point']
            points.append(Point(p['id'], p['coordinate'][0], p['coordinate'][1]))

        links = []
        for link in map_config.get('links', []):
            l = link['link']
            links.append(Link(l['id'], l['begin'], l['end']))

        self.graph = Graph(points, links)
        self.map_config = map_config  # 存起来供其他方法使用

    def create_machines(self):
        self.machines = []
        for machine in self.map_config.get('machines', []):
            m = machine['machine']
            point = self.graph.get_point_by_id(m['point_id'])
            if point is None:
                LOGGER.error(f"Machine Point ID {m['point_id']} not found in the graph")
                continue
            self.machines.append(Machine(m['id'], point.x, point.y, m['point_id']))

    def create_agvs(self):
        self.agvs = []
        for agv in self.map_config.get('agvs', []):
            a = agv['agv']
            point = self.graph.get_point_by_id(a['point_id'])
            if point is None:
                LOGGER.error(f"AGV Point ID {a['point_id']} not found in the graph")
                continue
            self.agvs.append(AGV(a['id'], point.x, point.y, a['point_id'], a['velocity'], self.graph))

    def __call__(self):
        """返回构建好的结构"""
        return self.jobs, self.machines, self.agvs, self.graph

if __name__ == '__main__':
    mapLoader = FactoryMapLoader()
    print(mapLoader())
