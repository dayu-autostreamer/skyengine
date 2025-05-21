from typing import Union, List, Tuple

from pettingzoo import ParallelEnv
import numpy as np

from sky_dag_rl.sky_dag.Agent import BaseAgent
from sky_dag_rl.sky_dag.sky_env.Graph.Machine import Machine
from sky_dag_rl.sky_dag.sky_env.Graph.Operation import Operation
from sky_dag_rl.sky_dag.sky_env.Graph.AGV import AGV
from sky_dag_rl.sky_dag.sky_env.Utils import util
from sky_dag_rl.sky_dag.sky_env.Event.Event import Event, EventQueue


class SkyDagEnv(ParallelEnv):
    metadata = {"render_modes": ["human"], "name": "sky_dag_env"}

    def __init__(self,
                 agent: BaseAgent = None,
                 ):
        # 系统状态
        self.jobs = []
        self.machines = []
        self.agvs = []

        # 环境本身的状态,向量指标,事件队列等
        self.env_timeline: float = 0
        self.event_queue = EventQueue()

        self.limit = 200
        self.critic_vector = []  # 评价指标
        # self.reward = {}  # 每个Agent的奖励
        # self.terminations = {}  # 是否完成任务
        # self.truncations = {}  # 智能体是否提前截断

        # 智能体相关的状态
        self.agent = agent

    # ---------- 自定义状态更新函数 ----------
    def set_env_timeline(self, env_timeline: float):
        self.env_timeline = env_timeline

    def get_env_timeline(self) -> float:
        return self.env_timeline

    def refresh_status(self):
        """
        刷新当前环境的graph和agv
        :return:
        """
        self.jobs, self.machines, self.agvs = util.read_agv_instance_data()
        print("Environment Initialized Successfully.")

    def deal_event(self, event_list):
        for event in event_list:
            if event.event_type == "just_test":
                print(event.payload)
            elif event.event_type == "task_finish":
                op = event.payload
            elif event.event_type == "machine_fail":
                pass

    def env_step(self, actions: List[Tuple[Operation, AGV, Machine]], step_time: float) -> None:
        current_time = self.env_timeline
        final_time = current_time + step_time

        for operation, agv, machine in actions:
            agv.todo_queue_push(("load", operation))
            agv.todo_queue_push(("unload", machine))

            print(
                f"Operation {operation.id}: AGV={agv.get_id()}, Machine={machine.get_id()}, Duration={operation.get_duration(machine.get_id())}")

        for machine in self.machines:
            if machine.get_operation() is not None:
                machine.work(final_time)
            machine.set_timer(final_time)
        for agv in self.agvs:
            if not agv.todo_queue_is_empty():
                agv.work(final_time)
            agv.set_timer(final_time)

    def step(self, actions=None):
        # === 0. Agent 决策动作（支持 Job 或 Central）===
        decisions, step_time = self.agent.sample(self.agvs, self.machines,
                                                self.jobs)  # type: List[Tuple[Operation, AGV,  Machine]], float
        print(f"step_time: {step_time}")
        print(f"decisions: {decisions}")
        
        
        # === 1. 处理 EventQueue 中的事件 ===
        # todo 第一阶段暂时没用到event
        current_event_list = self.event_queue.pop_ready_events(self.env_timeline)
        self.deal_event(current_event_list)

        # === 2. 提取state,发送给状态转移函数并返回 ===
        self.env_step(decision, step_time)

        # === 3. 统计完成状态，计算奖励 ===
        # todo 计算状态/动作完成reward计算
        rewards = {self.agent.agent_id: self.agent.reward()}
        terminations = {self.agent}
        truncations = {self.agent}

        # === 4. 处理全局时间 ===
        self.env_timeline += step_time

        obs = self._get_obs()

        return obs, rewards, terminations, truncations, {}

    def _get_obs(self):
        """
        获得Agent观察的环境信息
        :return: 物理节点的观察信息
        """
        obs = {}
        # todo 构建Agent对全局的观察
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
        # ---------- 获取Agent的观察 ----------
        obs = self._get_obs()  # 本系统agent从外界定义因此不需要从内部获得agent信息
        return obs

    def render_env(self):
        # 展示环境状态
        print(f"\n🌍 环境状态:")
        print(f"  - 当前时间: {self.env_timeline}")

    def render_observation(self):
        # 展示作业、机器和AGV数量
        print(f"\n📊 系统资源状态:")
        print(f"  - 作业数量: {len(self.jobs)}")
        print(f"  - 机器数量: {len(self.machines)}")
        print(f"  - AGV数量: {len(self.agvs)}")

    def render_event(self):
        # 展示事件队列
        print(f"\n📋 事件队列 ({len(self.event_queue)} 个待处理事件):")

    def render_critic(self):
        # 展示critic向量
        print(f"\n📈 Critic向量 ({len(self.critic_vector)} 维):")
        if len(self.critic_vector) > 0:
            # 缩短长向量显示
            vec_display = np.array(self.critic_vector)
            if len(self.critic_vector) > 10:
                vec_display = np.concatenate([vec_display[:5], [np.nan], vec_display[-5:]])
            print(f"  {np.array2string(vec_display, precision=2, max_line_width=100)}")
        else:
            print("  Critic向量为空")

    def render_agent(self):
        # 展示智能体状态
        print(f"\n🤖 智能体状态:")
        if hasattr(self.agent, 'name'):
            print(f"  - 智能体名称: {self.agent.name}")
        if hasattr(self.agent, 'step_count'):
            print(f"  - 执行步数: {self.agent.step_count}")
        if hasattr(self.agent, 'epsilon'):
            print(f"  - 探索率 (ε): {self.agent.epsilon:.4f}")

    def render(self):
        """可视化系统当前状态 功能拆分到不同函数中"""
        pass


if __name__ == '__main__':
    pass
