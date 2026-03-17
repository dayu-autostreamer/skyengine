'''
@Project ：SkyEngine 
@File    ：dt_solver.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/11/20 10:39
'''
from joint_sim.component.JobSolver.template_solver.job_solver import JobSolver
from joint_sim.component.JobSolver.job_solver_factory import JobSolverFactory
import torch


# 假设上面的模型保存在 model_def.py 中
# from .model_def import JSSPDecisionTransformer

@JobSolverFactory.register_solver("decision_transformer")
class DTJobSolver(JobSolver):
    def __init__(self, model_path="checkpoints/dt_best.pth"):
        super().__init__()
        self.initialized = False
        self.transfer_requests = []
        self.time_stamp = 0
        self.task_idx = 0

        # 加载模型 (实际使用时需处理路径和参数)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # self.model = JSSPDecisionTransformer().to(self.device)
        # self.model.load_state_dict(torch.load(model_path))
        # self.model.eval()
        self.target_makespan = 100.0  # 提示 Token：我们期望在这个时间内完成

    def plan(self, obs: dict) -> dict:
        self.time_stamp += 1

        if not self.initialized:
            jobs = obs["jobs"]
            machines = obs["machines"]

            # === 核心：使用 DT 生成调度序列 ===
            # 注意：这里我们在第0时刻，用模型"脑补"完整个流程
            scheduled_tasks = self._generate_schedule_with_dt(jobs, machines)

            self.transfer_requests = [self.create_routing_task(task) for task in scheduled_tasks]
            # 确保按 ready_time 排序
            self.transfer_requests.sort(key=lambda x: x.ready_time)
            self.initialized = True

        # 后续逻辑与 Greedy 相同，只是负责分发
        ready_transfers = self._trigger_ready_transfers(self.time_stamp)
        return {"transfer_requests": ready_transfers}

    def _generate_schedule_with_dt(self, jobs, machines):
        """
        在虚拟环境中运行 DT 模型，生成静态调度表。
        这相当于一个 Simulation Loop。
        """
        # 1. 构建内部状态跟踪 (Shadow State)
        # 我们需要模拟机器占用时间和工序完成状态
        machine_free_time = {m.id: 0.0 for m in machines}
        all_ops = []
        # 展平所有 Job 的 Ops，建立索引映射
        for job in jobs:
            for op in job.operations:
                all_ops.append({
                    "job_id": job.job_id,
                    "op_id": op.op_id,
                    "duration": op.process_time,
                    "machine": op.machine_id,
                    "predecessor_ids": op.pre_op_ids,  # 假设有这个属性
                    "id": f"{job.job_id}_{op.op_id}",
                    "idx": len(all_ops),
                    "status": 0,  # 0:Waiting, 1:Ready, 2:Done (简化状态)
                    "start_time": -1,
                    "end_time": -1
                })

        scheduled_sequence = []
        current_rtg = self.target_makespan

        # 模拟循环，直到所有任务完成
        while len(scheduled_sequence) < len(all_ops):
            # A. 构建 Tensor 输入
            # 找出哪些是 Ready 的 (前置任务已完成且自己未完成)
            durations = []
            machine_ids = []
            statuses = []
            mask = []  # True 代表要 Mask 掉 (不可选)

            finished_ids = set(op["id"] for op in all_ops if op["status"] == 2)

            for op in all_ops:
                durations.append(op["duration"])
                machine_ids.append(op["machine"])

                # 检查前置条件
                is_pre_done = all([pid in finished_ids for pid in op.get("predecessor_ids", [])])

                if op["status"] == 2:  # 已完成
                    s = 3  # Done
                    m = True
                elif is_pre_done:
                    s = 1  # Ready
                    m = False  # 可选
                else:
                    s = 0  # Waiting
                    m = True

                statuses.append(s)
                mask.append(m)

            # 转 Tensor
            t_dur = torch.tensor([durations], dtype=torch.float).to(self.device)
            t_mac = torch.tensor([machine_ids], dtype=torch.long).to(self.device)
            t_sta = torch.tensor([statuses], dtype=torch.long).to(self.device)
            t_rtg = torch.tensor([[current_rtg]], dtype=torch.float).to(self.device)
            t_mask = torch.tensor([mask], dtype=torch.bool).to(self.device)

            # B. 模型推理
            with torch.no_grad():
                # logits: [1, Num_Ops]
                logits = self.model(t_dur, t_mac, t_sta, t_rtg, action_mask=t_mask)
                # 贪婪采样: 选概率最大的
                selected_idx = torch.argmax(logits, dim=1).item()

            # C. 状态更新 (模拟调度执行)
            selected_op = all_ops[selected_idx]

            # 计算时间
            # 开始时间 = max(该工序前置结束时间, 机器空闲时间)
            # 这里简化处理，假设 Job 内前置是严格顺序
            job_prev_end = 0
            # (此处需要更严谨的逻辑查找该 Job 上一个 Op 的结束时间，略)

            m_id = selected_op["machine"]
            start_time = max(machine_free_time[m_id], job_prev_end)
            end_time = start_time + selected_op["duration"]

            # 更新状态
            machine_free_time[m_id] = end_time
            all_ops[selected_idx]["status"] = 2  # Done
            all_ops[selected_idx]["start_time"] = start_time
            all_ops[selected_idx]["end_time"] = end_time

            # 更新 RTG (简单的 rtg - spent_time)
            current_rtg -= (end_time - start_time)  # 粗略估计

            # 添加到结果
            task_dict = {
                "job_id": selected_op["job_id"],
                "op_id": selected_op["op_id"],
                "from_machine": None,  # 需要根据逻辑补充
                "to_machine": m_id,
                "ready_time": start_time  # 关键：模型决定了它什么时候开始
            }
            scheduled_sequence.append(task_dict)

        return scheduled_sequence

    # ... create_routing_task 和 _trigger_ready_transfers 与原代码一致 ...
    def create_routing_task(self, task_dict):
        # (保持你原来的代码不变)
        # 注意：source 和 destination 的逻辑需要根据你的 Grid 实际情况计算
        return super().create_routing_task(task_dict)  # 假设继承或复制了该方法

    def _trigger_ready_transfers(self, t):
        # (保持你原来的代码不变)
        ready = []
        while self.transfer_requests and self.transfer_requests[0].ready_time <= t:
            ready.append(self.transfer_requests.pop(0))
        return ready