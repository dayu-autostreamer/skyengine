from typing import List, Optional, Tuple

# from .Machine import Machine

class Operation:

    def __init__(self, op_id: int, process_time: float, durations: List[Tuple[int, float]], cpu_req=0, mem_req=0):
        """
        :param process_time: 操作的处理时间
        :param durations: 列表，每个元素是 (machine_id, duration) 表示该机器上执行所需时间
        """
        # operation本身的属性
        self.id: int = op_id
        self.process_time: float = process_time
        self.durations: List[Tuple[int, float]] = durations
        self.next_operation: Optional['Operation'] = None
        self.current_machine = None
        self.finished = False
        self.status = "ready"

        self.cpu_req = cpu_req
        self.mem_req = mem_req

        # operation本身的状态
        self.progress = 0.0
        self.dependencies = []
        self.successors = []
        self.assigned_node = None
        # self.duration = duration # 当前产品需要加工的进度条

        # operation处理item相关的状态
        self.processed_item_list = []
        self.current_progress = 0  # 当前物品的加工进度
        self.current_start_time = None


    def __repr__(self):
        # 格式化持续时间列表（最多显示前3个）
        durations_str = "[...]"
        if self.durations:
            durations_short = self.durations[:3]
            durations_str = ", ".join([f"({m_id}, {dur:.1f})" for m_id, dur in durations_short])
            if len(self.durations) > 3:
                durations_str += ", ..."
            durations_str = f"[{durations_str}]"

        # # 获取已处理物品数量
        # items_count = len(self.processed_item_list)

        # # 格式化状态信息
        # progress_str = f"{self.progress:.1%}"
        # assigned_node = self.assigned_node if self.assigned_node is not None else "None"

        return (
            f"<{self.__class__.__name__} "
            f"id={self.id} "
            f"time={self.process_time:.1f} "
            f"durations={durations_str} "
            f"state={self.status} "
            # f"progress={progress_str} "
            # f"items={items_count} "
            # f"node={assigned_node}>"
        )


    def get_process_time(self) -> float:
        return self.process_time

    def set_process_time(self, process_time: float) -> None:
        self.process_time = process_time

    def is_machine_capable(self, machine_id: int) -> bool:
        """
        :param machine_id: 要检查的机器 ID
        :return: 是否该操作可以在该机器上执行
        """
        for m_id, _ in self.durations:
            if m_id == machine_id:
                return True
        return False

    def get_duration(self, machine_id: int) -> float:
        """
        :param machine_id: 机器 ID
        :return: 该操作在该机器上的执行时间
        """
        for m_id, duration in self.durations:
            if m_id == machine_id:
                return duration
        print(f"Operation {self.id}: Machine {machine_id} not found")
        return 0.0
    
    def is_finished(self) -> bool:
        """
        :return: 该操作是否完成
        """
        return self.finished
    
    def set_finished(self, finished: bool) -> None:
        """
        :param finished: 该操作是否完成
        """
        self.finished = finished

    def get_next_operation(self) -> Optional['Operation']:
        return self.next_operation

    def set_next_operation(self, next_operation: Optional['Operation']) -> None:
        self.next_operation = next_operation

    def get_current_machine(self):
        return self.current_machine
    
    def set_current_machine(self, current_machine) -> None:
        self.current_machine = current_machine

    def get_status(self):
        return self.status
    
    def set_status(self, status):
        self.status = status


    def add_dependency(self, op):
        """
        添加依赖节点
        :param op:
        :return:
        """
        self.dependencies.append(op)

    def add_successor(self, op):
        """
        添加依赖节点
        :param op:
        :return:
        """
        self.successors.append(op)

    def is_ready(self):
        return all(dep.state == "finished" for dep in self.dependencies)

    # ----------正常运行阶段----------
    def get_feature(self):
        return {
            "id": self.id,
            "state": self.state,
            "cpu": self.cpu_req,
            "mem": self.mem_req,
            "processed_item_list": self.processed_item_list,
            "assigned_node": self.assigned_node.id if self.assigned_node else None
        }
    
    def pause(self):
        """
        暂停operation运行
        :return:
        """
        self.state = "paused"
        self.save_status()

    def resume(self):
        """
        重启运行
        :return:
        """
        self.state = self.load_status()

    def fail(self):
        """
        operation报错
        :return:
        """
        self.state = "fail"

    def step(self, node_speed, env_time, packet=None, error_chance=0.0):
        """
        Operation 的执行周期逻辑。
        每次 step 表示推进一个时间片。

        :param node_speed: 当前节点加工速度 (单位进度/时间)
        :param env_time: 当前环境时间
        :param packet: 传入的工件（可为空）
        :param error_chance: 故障概率（用于模拟）
        :return: 是否完成一个工件（True/False/None）
        """

        # 故障状态不执行任何操作
        if self.state == "failed":
            return None

        # 暂停状态等待外部 resume
        if self.state == "paused":
            return None

        # 尚未满足依赖条件
        if self.state == "blocked":
            if self.is_ready():
                self.state = "ready"
            else:
                return None

        # 准备状态，等待输入工件
        if self.state == "ready":
            if packet:
                self.current_progress = 0.0
                self.current_start_time = env_time
                self.state = "active"
            else:
                return None  # 无输入继续等待

        # 主加工阶段
        if self.state == "active":
            self.current_progress += node_speed

            # 加工完成
            if self.current_progress >= self.duration:
                self.processed_item_list.append({
                    "start_time": self.current_start_time,
                    "end_time": env_time,
                })
                self.current_progress = 0.0
                self.state = "ready"
                return True

        # 空闲状态，等待下一轮调度
        if self.state == "ready":
            return False


    def check_dependencies(self):
        """
        判断前置条件是否满足
        :return:
        """
        if self.state == "pending" and self.is_ready():
            self.state = "ready"

    def cal_qos(self, current_time):
        """
        查看运行质量
        :return:
        """
        if hasattr(self, "deadline"):
            return 1 if current_time <= self.deadline else 0
        return 1  # 默认不罚分

    # ----------重调度阶段----------
    def request(self):
        """
        请求资源
        :return:
        """
        return {"cpu": self.cpu_req, "mem": self.mem_req}

    def choose(self, candidate_nodes):
        """
        进行物理机的选择
        :return:
        """
        # 默认选择资源最多的节点，或在外部策略中完成
        sorted_nodes = sorted(candidate_nodes, key=lambda n: n.cpu_capacity + n.mem_capacity, reverse=True)
        return sorted_nodes[0] if sorted_nodes else None

    def assign_to_node(self, node, time):
        """
        分配到节点上
        :param node:
        :return:
        """
        self.assigned_node = node
        self.state = "paused"
