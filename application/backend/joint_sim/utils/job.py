"""
@Project ：SkyEngine
@File    ：job.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/1 10:42
"""

import random
from typing import List
from joint_sim.utils.structure import (
    JobConfig,
    Job,
    Operation,
)

def generate_jobs(job_config: JobConfig) -> List[Job]:
    """
    根据 JobConfig 随机生成一批 Job。
    """
    random.seed(job_config.seed)
    jobs: List[Job] = []

    for j in range(job_config.num_jobs):
        # 随机工序数
        num_ops = random.randint(job_config.min_ops_per_job, job_config.max_ops_per_job)
        ops: List[Operation] = []

        for op_id in range(num_ops):
            # 随机处理时间
            proc_time = random.randint(
                job_config.min_proc_time, job_config.max_proc_time
            )

            # 随机可用机器选项
            machine_options = random.sample(
                range(job_config.total_machines),
                k=min(job_config.machine_choices, job_config.total_machines),
            )

            op = Operation(
                job_id=j,
                op_id=op_id,
                machine_options=machine_options,
                proc_time=proc_time,
                release=0.0,
                due=None,
            )
            ops.append(op)

        jobs.append(Job(job_id=j, ops=ops))

    return jobs

