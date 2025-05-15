from typing import Union, List, Tuple

from pettingzoo import ParallelEnv
import numpy as np

from sky_dag_rl.sky_dag.Agent import BaseAgent
from .Graph.Node import Node
from .Graph.Job import Job
from .Graph.Operation import Operation
from .Graph.AGV import AGV
from .Utils import util
from .Event.Event import Event, EventQueue
import json


class SkyDagEnv(ParallelEnv):
    metadata = {"render_modes": ["human"], "name": "sky_dag_env"}

    def __init__(self,
                 agent: BaseAgent = None,
                 ):
        # 模拟源点和终点
        self.source = None
        self.destination = None

        # 系统状态
        self.jobs = []
        self.machines = []
        self.agvs = []

        # 环境本身的状态,向量指标,事件队列等
        self.env_timeline = 0
        self.reward = 0
        self.event_queue = EventQueue()
        self.critic_vector = []

        # 智能体相关的状态
        self.agent = agent

    # ---------- 自定义状态更新函数 ----------
    def set_env_timeline(self, count):
        assert count >= 0 and isinstance(count, int)
        self.env_timeline = count

    def get_env_timeline(self) -> int:
        return self.env_timeline

    def refresh_status(self):
        """
        刷新当前环境的graph和agv
        :return:
        """
        self.jobs,self.machines,self.agvs=util.read_agv_instance_data()
        print("Environment Initialized Successfully.")

    def deal_event(self, event_list):
        for event in event_list:
            if event.event_type == "just_test":
                print(event.payload)
            elif event.event_type == "task_finish":
                op = event.payload
            elif event.event_type == "machine_fail":
                for node_id in event.payload['nodes']:
                    self.nodes[node_id].fail()

    def env_step(self, actions: List[Tuple[AGV, Operation, Machine]], step_time: int) -> None:
        current_time = self.env_timeline
        final_time = current_time + step_time
        # todo: 限制Timer不能超过final_time
        for agv, operation, machine in actions:
            last_machine = operation.get_current_machine()
            if last_machine is None:
                agv.set_operation(operation)
                agv.unload(machine)
            else:
                agv.load(last_machine)
                agv.unload(machine)

            print(f"Operation {operation.id}: AGV={agv.get_id()}, Machine={machine.get_id()}, Duration={operation.get_duration(machine.get_id())}")

        # todo: 将所有的AGV和Machine的Timer更新到final_time

    def step(self, actions=None):
        rewards = {}
        terminations = {}
        truncations = {}
        infos = {}

        # === 0. 处理全局时间 ===
        self.env_timeline += 1
        obs = self._get_obs()

        # === 1. Agent 动作处理（支持 Job 或 Central）===
        if actions:
            self.apply_agent_actions()

        # === 2. 处理 EventQueue 中的事件 ===
        current_event_list = self.event_queue.pop_ready_events(self.env_timeline)
        self.deal_event(current_event_list)

        # === 3. 提取state,发送给状态转移函数并返回 ===
        actions: List[Tuple[AGV, Operation, Machine]] = self.agent.step()
        env_step(actions, step_time)

        finished_ops = get_finished_ops(self.operations)
        for op in finished_ops:
            self.event_queue.add_event(Event(
                timestamp=self.env_timeline,
                event_type="task_finish",
                payload=op
            ))

        # === 4. 统计 Job 完成状态，计算奖励 ===
        for job in self.jobs:
            done = job.is_finished()
            job_id = job.id
            rewards[job_id] = 1.0 if done and not self.done_flags.get(job_id, False) else 0.0
            terminations[job_id] = done
            truncations[job_id] = False
            infos[job_id] = {}
            if done:
                self.done_flags[job_id] = True

        return obs, rewards, terminations, truncations, infos

    def _get_obs(self):
        """
        获得环境观察的信息
        :return: 物理节点的观察信息
        """
        obs = {}
        for name, node in self.nodes.items():
            cpu_load = sum(o.cpu_req for o in node.running_operations) / node.cpu_capacity
            mem_load = sum(o.mem_req for o in node.running_operations) / node.mem_capacity
            obs[name] = np.array([
                min(cpu_load, 1.0),
                min(mem_load, 1.0),
                len(node.running_operations)
            ], dtype=np.float32)
        return obs

    def reset(self, seed=None, options=None):
        """
        返回环境初始状态下智能体的观察值,使环境整体的状态回到开始时的样子。
        :param seed: 随机种子,复现实验
        :param options:选项
        :return:
        """
        # ---------- 清理重建阶段 ----------
        self.set_env_timeline(0)
        self.refresh_status()
        obs = self._get_obs()
        return obs

    def render(self):
        """可视化系统当前状态"""
        print("\n" + "=" * 50)
        print(f"系统状态渲染 @ 时间点: {self.env_timeline}")
        print("=" * 50)

        # 1. 展示作业、机器和AGV数量
        print(f"\n📊 系统资源状态:")
        print(f"  - 作业数量: {len(self.jobs)}")
        print(f"  - 机器数量: {len(self.machines)}")
        print(f"  - AGV数量: {len(self.agvs)}")

        # 2. 展示环境状态
        print(f"\n🌍 环境状态:")
        print(f"  - 当前时间: {self.env_timeline}")
        print(f"  - 累计奖励: {self.reward:.4f}")

        # 3. 展示事件队列
        print(f"\n📋 事件队列 ({len(self.event_queue)} 个待处理事件):")
        if len(self.event_queue) > 0:
            for i, event in enumerate(list(self.event_queue)[:5]):  # 只显示前5个事件
                print(f"  {i + 1}. {str(event)[:70]}{'...' if len(str(event)) > 70 else ''}")
            if len(self.event_queue) > 5:
                print(f"  ... 和其他 {len(self.event_queue) - 5} 个事件")
        else:
            print("  事件队列为空")

        # 4. 展示critic向量
        print(f"\n📈 Critic向量 ({len(self.critic_vector)} 维):")
        if len(self.critic_vector) > 0:
            # 缩短长向量显示
            vec_display = np.array(self.critic_vector)
            if len(self.critic_vector) > 10:
                vec_display = np.concatenate([vec_display[:5], [np.nan], vec_display[-5:]])
            print(f"  {np.array2string(vec_display, precision=2, max_line_width=100)}")
        else:
            print("  Critic向量为空")

        # 5. 展示智能体状态
        print(f"\n🤖 智能体状态:")
        if hasattr(self.agent, 'name'):
            print(f"  - 智能体名称: {self.agent.name}")
        if hasattr(self.agent, 'step_count'):
            print(f"  - 执行步数: {self.agent.step_count}")
        if hasattr(self.agent, 'epsilon'):
            print(f"  - 探索率 (ε): {self.agent.epsilon:.4f}")

        # 6. 展示详细资源状态 (如果有具体对象)
        if len(self.jobs) > 0 or len(self.machines) > 0 or len(self.agvs) > 0:
            print(f"\n🔍 详细资源状态:")

            if len(self.jobs) > 0:
                print(f"\n  📦 作业 ({len(self.jobs)}):")
                for i, job in enumerate(self.jobs[:3]):  # 只显示前3个
                    status = getattr(job, 'status', '未知')
                    progress = getattr(job, 'progress', 0)
                    print(f"    {i + 1}. 作业#{getattr(job, 'id', '?')} - 状态: {status}, 进度: {progress:.0%}")
                if len(self.jobs) > 3:
                    print(f"    ... 和其他 {len(self.jobs) - 3} 个作业")

            if len(self.machines) > 0:
                print(f"\n  🏭 机器 ({len(self.machines)}):")
                for i, machine in enumerate(self.machines[:3]):
                    status = getattr(machine, 'status', '未知')
                    current_job = getattr(machine, 'current_job', None)
                    job_info = f"作业#{current_job.id}" if current_job else "空闲"
                    print(f"    {i + 1}. 机器#{getattr(machine, 'id', '?')} - 状态: {status}, 当前: {job_info}")
                if len(self.machines) > 3:
                    print(f"    ... 和其他 {len(self.machines) - 3} 个机器")

            if len(self.agvs) > 0:
                print(f"\n  🚚 AGV ({len(self.agvs)}):")
                for i, agv in enumerate(self.agvs[:3]):
                    status = getattr(agv, 'status', '未知')
                    location = getattr(agv, 'location', '?')
                    task = getattr(agv, 'current_task', '无')
                    print(
                        f"    {i + 1}. AGV#{getattr(agv, 'id', '?')} - 状态: {status}, 位置: {location}, 任务: {task}")
                if len(self.agvs) > 3:
                    print(f"    ... 和其他 {len(self.agvs) - 3} 个AGV")

        print("=" * 50)

    def observation_space(self, agent):
        return self.observation_spaces[agent]

    def action_space(self, agent):
        return self.action_spaces[agent]

    def get_op_by_id(self, op_id):
        for job in self.jobs:
            for op in job.operations:
                if op.id == op_id:
                    return op
        return None

    def apply_agent_actions(self, actions):
        """
        执行 agent 提供的动作，支持集中式与 Job 式调度。
        actions 格式：
            - job-based: {"job_id1": {"op_id": "op1", "target_node": "node1"}, ...}
            - centralized: {"scheduler": [{"op_id": "op1", "target_node": "node1"}, ...]}
        """
        pass


if __name__ == '__main__':
    pass