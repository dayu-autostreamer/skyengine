from typing import List

from sky_simulator.environment.packet_factory.packet_factory_env.Job.Operation import Operation
from sky_simulator.environment.packet_factory.packet_factory_env.Utils.util import JobStatus, OperationStatus
from sky_simulator.registry import register_component
from sky_simulator.call_back.packet_factory_callback.callback_manager.JobCallbackManager import JobCallbackManager
from sky_logs.logger import JOB_LOGGER as LOGGER


@register_component("packet_factory.Job")
class Job:
    def __init__(self, job_id: int, operations: List[Operation], target_count=None):
        """
        :param operations: 构成作业的操作列表
        """
        self.id = job_id
        self.operations: List[Operation] = operations
        for i in range(len(self.operations)):
            if i + 1 < len(self.operations):
                self.operations[i].set_next_operation(self.operations[i + 1])
            else:
                self.operations[i].set_next_operation(None)
        if len(self.operations) >= 1:
            self.operations[0].set_status(OperationStatus.READY)

        self.begin_time: float = 0.0
        self.timer: float = 0.0
        self.status = JobStatus.B4START
        self.target_count = target_count  # 目标处理工件数，可选
        # 需要记录的数据
        self.data_pool = {

        }
        # 事件回调机制
        self.callback_manager: JobCallbackManager = JobCallbackManager()

    def __repr__(self):
        # 获取操作数量
        op_count = len(self.operations)

        # 获取第一个和最后一个操作的ID（如果有操作）
        first_op_id = self.operations[0].id if op_count > 0 else "None"
        last_op_id = self.operations[-1].id if op_count > 0 else "None"

        # 计算总处理时间（所有操作的process_time之和）
        total_time = sum(op.process_time for op in self.operations) if op_count > 0 else 0

        # 显示目标工件数（如果设置了）
        target_str = f", target={self.target_count}" if self.target_count is not None else ""

        return (
            f"<{self.__class__.__name__} "
            f"id={self.id} "
            f"operation_count={op_count} "
            f"first={first_op_id} "
            f"last={last_op_id} "
            f"time={total_time:.1f}{target_str}> "
            f"status={self.status}> "
            f"operations={self.operations} "
        )

    def set_begin_time(self, timer: float):
        self.begin_time = timer

    def set_callback_manager(self, callback_manager: JobCallbackManager):
        self.callback_manager = callback_manager
        LOGGER.info("CallbackManager Created Successfully.")

    def get_id(self) -> int:
        return self.id

    def get_operation_count(self) -> int:
        return len(self.operations)

    def get_operation(self, index: int) -> Operation:
        """
        :param index: 操作索引
        :return: 对应索引的操作，如果越界则返回 None
        """
        assert index >= 0 and index < len(self.operations), "Invalid index"

        return self.operations[index]

    def add_operation(self, op):
        if self.get_operation_count() > 0:
            self.operations[-1].set_next_operation(op)
        self.operations.append(op)

    def set_status(self, status: JobStatus):
        self.status = status

    def get_status(self):
        if self.is_finished(self.timer):
            self.status = JobStatus.FINISHED
        return self.status

    def get_progress(self):
        """
        计算当前Job的进度
        """
        count = 0
        for operation in self.operations:
            if operation.get_status() == OperationStatus.FINISHED:
                count += 1
        return count / len(self.operations)

    def is_finished(self, current_env_time: float):
        """
        计算当前Job是否已经完成
        """
        # todo: 待完善job状态转移
        self.timer = max(self.timer,current_env_time)
        # return self.status == JobStatus.FINISHED
        if self.operations[self.get_operation_count() - 1].get_status() == OperationStatus.FINISHED:
            # 传入自己,计算所有指标
            self.callback_manager.use_all_after_work(self)
            return True
        return False

    # 赋值一个新的Job，状态完全处于最新状态
    def clone(self):
        operations = [op.clone() for op in self.operations]
        job = Job(self.id, operations)
        return job
