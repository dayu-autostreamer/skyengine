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
