import os
import random
import json

from typing import List, Optional, Tuple
from sky_simulator.packet_factory.packet_factory_env.Graph.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Graph.Node import Node
from sky_simulator.packet_factory.packet_factory_env.Graph.AGV import AGV
from sky_simulator.packet_factory.packet_factory_env.Graph.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Graph.Job import Job
from sky_simulator.packet_factory.packet_factory_env.Graph.util import OperationStatus
import dataset


def read_agv_instance_data(relative_file_path):
    prefix = dataset.AGV_DATA_DIR
    file_path = prefix + relative_file_path
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
    for i in range(m):
        x = float(data[idx])
        idx += 1
        y = float(data[idx])
        idx += 1
        machines.append(Machine(i, x, y))

    agvs: List[AGV] = []
    for i in range(k):
        x = float(data[idx])
        idx += 1
        y = float(data[idx])
        idx += 1
        velocity = float(data[idx])
        idx += 1
        agvs.append(AGV(i, x, y, velocity))

    return jobs, machines, agvs


def generate_structured_job_config(
        num_jobs: int = 1,
        num_operations_per_job: int = 5,
        max_dependencies: int = 2,
        min_cpu: int = 1,
        max_cpu: int = 4,
        min_mem: int = 1,
        max_mem: int = 8,
        min_duration: int = 2,
        max_duration: int = 6,
        seed: int = None
):
    """
    随机生成一个Job配置，包括Operation信息和运行时间的信息。
    """
    if seed is not None:
        random.seed(seed)

    jobs = []

    for job_index in range(num_jobs):
        job_id = f"job_{job_index + 1}"
        operations = []
        op_ids = []
        dependencies = []

        for i in range(num_operations_per_job):
            op_id = f"op_{i + 1}"
            op_ids.append(op_id)
            operations.append({
                "id": op_id,
                "cpu_req": random.randint(min_cpu, max_cpu),
                "mem_req": random.randint(min_mem, max_mem),
                "duration": random.randint(min_duration, max_duration)
            })

        # 构建依赖关系（确保是合法 DAG）
        for i in range(1, num_operations_per_job):
            num_deps = random.randint(0, min(i, max_dependencies))
            from_ops = random.sample(op_ids[:i], num_deps)
            for from_op in from_ops:
                dependencies.append({"from": from_op, "to": op_ids[i]})

        jobs.append({
            "id": job_id,
            "operations": operations,
            "dependencies": dependencies
        })

    return {"jobs": jobs}


def generate_random_node_config(
        num_nodes: int = 5,
        grid_size: tuple = (5, 5),
        max_successors: int = 2,
        min_delay: int = 1,
        max_delay: int = 3,
        min_cpu: int = 2,
        max_cpu: int = 8,
        min_memory: int = 4,
        max_memory: int = 16,
        seed: int = None
):
    """
    随机生成一个物理网络配置，包括节点信息和链路信息。
    """
    if seed is not None:
        random.seed(seed)

    nodes = []
    links = []
    used_positions = set()

    for i in range(num_nodes):
        node_id = f"node_{i + 1}"

        # 避免位置重复
        while True:
            pos = (random.randint(0, grid_size[0] - 1), random.randint(0, grid_size[1] - 1))
            if pos not in used_positions:
                used_positions.add(pos)
                break

        nodes.append({
            "id": node_id,
            "position": list(pos),
            "cpu": random.randint(min_cpu, max_cpu),
            "memory": random.randint(min_memory, max_memory)
        })

    node_ids = [node["id"] for node in nodes]

    # 构建链路：确保图是连通的 + 加一些随机边
    for i in range(num_nodes):
        from_node = node_ids[i]
        successors = random.sample(node_ids[:i] + node_ids[i + 1:],
                                   k=random.randint(1, min(max_successors, num_nodes - 1)))
        for to_node in successors:
            # 避免重复边
            if not any(l["from"] == from_node and l["to"] == to_node for l in links):
                links.append({
                    "from": from_node,
                    "to": to_node,
                    "delay": random.randint(min_delay, max_delay)
                })

    return {
        "nodes": nodes,
        "links": links
    }


def read_file_and_create_json(file_path):
    jobs_data = []
    with open(file_path, 'r') as file:
        lines = file.readlines()
        num_jobs, num_machines = map(int, lines[0].strip().split())

        for job_id, line in enumerate(lines[1:], 1):
            job_info = line.strip().split()
            num_operations = int(job_info[0])
            operations = []
            dependencies = []
            for op_id in range(num_operations):
                start_index = 1 + op_id * 2
                num_machines_for_op = int(job_info[start_index])
                machine_id = int(job_info[start_index + 1])
                processing_time = int(job_info[start_index + 2])
                operation = {
                    "id": f"op_{op_id + 1}",
                    "cpu_req": 1,
                    "mem_req": 1,
                    "duration": processing_time
                }
                operations.append(operation)
                if op_id > 0:
                    dependency = {
                        "from": f"op_{op_id}",
                        "to": f"op_{op_id + 1}"
                    }
                    dependencies.append(dependency)

            job = {
                "id": f"job_{job_id}",
                "operations": operations,
                "dependencies": dependencies
            }
            jobs_data.append(job)

    result = {
        "jobs": jobs_data
    }
    return result

def load_node_graph(self):
    """
    读取并创建underlay图
    :return: None
    """
    with open(self.node_config_path, 'r') as f:
        config = json.load(f)
    for node_cfg in config.get('nodes', []):
        node = Node(
            node_id=node_cfg['id'],
            position=tuple(node_cfg['position']),
            cpu_capacity=node_cfg['cpu'],
            mem_capacity=node_cfg['memory']
        )
        self.nodes[node.id] = node

    for link in config.get('links', []):
        self.nodes[link['from']].connect_to(self.nodes[link['to']], link['delay'])

def load_job_graph(self):
    """
    读取job图的信息
    :return: None
    """
    with open(self.job_config_path, 'r') as f:
        config = json.load(f)

    for job_cfg in config.get('jobs', []):
        job = Job(job_cfg['id'], job_cfg['target_count'])
        op_dict = {}

        # 创建 operation 实例并加入 job
        for op_cfg in job_cfg['operations']:
            op = Operation(
                op_id=op_cfg['id'],
                cpu_req=op_cfg['cpu_req'],
                mem_req=op_cfg['mem_req'],
                duration=op_cfg['duration']
            )
            job.add_operation(op)
            op_dict[op.id] = op
            self.operations.append(op)

        # 建立操作之间的依赖关系
        for dep in job_cfg.get('dependencies', []):
            from_op = op_dict[dep['from']]
            to_op = op_dict[dep['to']]
            from_op.add_dependency(to_op)
            to_op.add_dependency(from_op)

        self.jobs[job.id] = job  # 存储 Job 对象，确保是 Job 类型

if __name__ == '__main__':
    # # 替换为你的实际文件路径
    # cwd = os.getcwd()
    # # 组合当前工作目录和表示上级目录的字符串
    # file_path = os.path.join(os.getcwd(), os.pardir, os.pardir, "dataset/fjsp-instances/barnes/mt10c1.txt")
    # json_data = read_file_and_create_json(file_path)
    # with open('../examples/output.json', 'w') as json_file:
    #     json.dump(json_data, json_file, indent=4)
    read_agv_instance_data()
