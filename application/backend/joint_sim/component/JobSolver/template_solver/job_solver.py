"""
@Project ：SkyEngine
@File    ：job_solver.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/27 22:49
"""


class JobSolver:
    def __init__(self):
        pass

    def plan(self, obs: dict) -> dict:
        """
        在当前时刻进行一次决策：
        输入:
        {
            'jobs': List[MachineAction],
            'machines': List[TransferRequest]
        }
        输出:
        {
            'machine_actions': List[MachineAction],
            'transfer_requests': List[TransferRequest]
        }

        machine_actions 示例:
        [
            {'machine_id': 0, 'job_id': 2, 'op_id': 1, 'start_time': 10.0, 'expected_end': 18.0},
            ...
        ]

        transfer_requests 示例:
        [
            {'job_id': 2, 'op_id': 1, 'from_machine': 1, 'to_machine': 3, 'ready_time': 12.0}
        ]
        """
        pass
