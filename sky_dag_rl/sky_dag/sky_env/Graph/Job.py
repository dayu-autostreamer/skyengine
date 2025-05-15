from typing import List

from .Operation import Operation

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

                
        self.target_count = target_count  # 目标处理工件数，可选

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
            f"ops={op_count} "
            f"first={first_op_id} "
            f"last={last_op_id} "
            f"time={total_time:.1f}{target_str}>"
        )

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
        self.operations.append(op)

    def get_target_count(self):
        return self.target_count

    def update_target_count(self):
        """
        在最后一个 Operation 完成处理后调用，用于统计任务完成度。
        """
        self.target_count+=1
