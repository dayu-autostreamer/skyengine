from typing import Union, List, Tuple

from pettingzoo import ParallelEnv
import numpy as np

from sky_simulator.packet_factory.Agent import BaseAgent
from sky_simulator.packet_factory.packet_factory_env.Graph.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Graph.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Graph.AGV import AGV
from sky_simulator.packet_factory.packet_factory_env.Event.Event import Event, EventQueue
from sky_simulator.packet_factory.packet_factory_env.Utils.logger import LOGGER
from sky_simulator.registry import register_component
from sky_simulator.call_back.base_callback.EnvVisualizer import EnvVisualizer
from sky_simulator.call_back.base_callback.EnvMapLoader import EnvMapLoader
from sky_simulator.call_back.EnvCallback import EnvCallback


@register_component("packet_factory")
class PacketFactoryEnv(ParallelEnv):
    metadata = {"render_modes": ["human"], "name": "packet_factory_env"}

    def __init__(self,
                 agent: BaseAgent
                 ):
        # 物料仓库与目标存储仓库
        self.source = []
        self.destination = []

        # 系统状态
        self.jobs = []
        self.machines = []
        self.agvs = []
        self.points = []
        self.links = []

        # 环境本身的状态,向量指标,事件队列等
        self.env_timeline: float = 0

        self.env_visualizer = None

        self.limit = 200
        self.critic_vector = {}  # 评价指标

        # 智能体相关的状态
        self.agent = agent

        # env的回调函数组 
        self.callback = {
            "load_graph": EnvMapLoader("/brandimarte/simple_agv.txt"),
            "initialize_visualizer": EnvVisualizer(self)
        }

    # ---------- 自定义状态更新函数 ----------
    def set_env_timeline(self, env_timeline: float):
        self.env_timeline = env_timeline

    def get_env_timeline(self) -> float:
        return self.env_timeline

    def add_callback(self, callback_name: str, callback_function: EnvCallback):
        assert callback_name in self.callback.keys()
        self.callback[callback_name] = callback_function

    def refresh_status(self):
        """
        刷新当前环境的graph和agv
        :return:
        """
        self.jobs, self.machines, self.agvs, self.points, self.links = self.callback['load_graph']()
        # 可视化
        self.env_visualizer = self.callback['initialize_visualizer']
        self.env_visualizer.visualize_env()
        LOGGER.info("Environment Initialized Successfully.")

    def action_space(self, agent):
        decisions, step_time = agent.sample(self.agvs, self.machines,
                                            self.jobs)  # type: List[Tuple[Operation, AGV,  Machine]], float
        return {
            "decisions": decisions,
            "step_time": step_time
        }

    def deal_event(self, event_list):
        for event in event_list:
            if event.event_type == "just_test":
                LOGGER.info(event.payload)
            elif event.event_type == "task_finish":
                op = event.payload
            elif event.event_type == "machine_fail":
                pass

    def env_step(self, actions: List[Tuple[Operation, AGV, Machine]], step_time: float) -> bool:
        # ---------- 当前轮次时间 ----------
        current_time = self.env_timeline
        final_time = current_time + step_time

        # ---------- machine执行已分配的工作 ----------
        for machine in self.machines:
            if len(machine.input_queue) > 0:
                machine.work(final_time)
            machine.set_timer(final_time)

        if len(actions) > 0:
            # ---------- 清空已调度但未执行的策略 ----------
            for agv in self.agvs:
                agv.todo_queue_clear()

            # ---------- 分配调度策略 ----------
            for operation, agv, machine in actions:
                agv.work(final_time, action=(operation, machine))

        # ---------- 执行调度策略 ----------
        for agv in self.agvs:
            agv.work(final_time)
            agv.set_timer(final_time)

        # ---------- 查看状态 ----------
        self.render_observation()

        # 更新可视化（每env_step更新一次）
        self.env_visualizer.visualize_env()

        # === 处理全局时间 ===
        self.env_timeline += step_time

        # 判断是否有不确定事件发生过，若有则返回True
        for machine in self.machines:
            if machine.uncertainty_simulator.uncertain_event_occurred():
                return True
        for agv in self.agvs:
            if agv.uncertainty_simulator.uncertain_event_occurred():
                return True

        return False

    def step(self, actions=None):
        LOGGER.info(f"--------- 当前循环步为{self.env_timeline} ---------")
        # === 0. Agent 决策动作（支持 Job 或 Central）===
        decisions = actions['decisions']

        # todo: Agent的执行时间不再决定要step多久，而是不确定性事件发生时才重新决策
        # step_time = actions['step_time']
        step_time = 1

        LOGGER.info(f"step_time: {step_time}")
        LOGGER.info(f"decisions: {decisions}")

        # === 2. 提取state,发送给状态转移函数并返回 ===
        while True:
            # 轮询，直到不确定性事件发生才重新决策
            if self.env_step(decisions, step_time):
                break
            else:
                # 分配完任务后，没有不确定性发生，那么仍执行原决策，不传入新决策
                decisions = []
                # 当全部任务执行完成时，也应该退出循环
                cnt = 0
                for job in self.jobs:
                    if job.is_finished():
                        cnt += 1
                if cnt == len(self.jobs):
                    self.agent.alive = False
                    break

        # === 3. 统计完成状态，计算奖励 ===
        # todo 计算状态/动作完成reward计算
        rewards = {self.agent.agent_id: self.agent.reward(self.critic_vector)}
        terminations = {self.agent}

        obs = self._get_obs()
        LOGGER.info(f"--------- 结束当前循环步 ---------")

        return obs, rewards, terminations, {}, {}

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
        LOGGER.info(f"\n🌍 环境状态:")
        LOGGER.info(f"  - 当前时间: {self.env_timeline}")

    def render_observation(self):
        # 展示作业、机器和AGV数量
        # LOGGER.info(f"\n📊 系统资源状态:")
        LOGGER.info(f"  - 作业: {self.jobs}")
        LOGGER.info(f"  - 机器: {self.machines}")
        LOGGER.info(f"  - AGV: {self.agvs}")

    def render_event(self):
        # 展示事件队列
        LOGGER.info(f"\n📋 事件队列 ({len(self.event_queue)} 个待处理事件):")

    def render_critic(self):
        # 展示critic向量
        LOGGER.info(f"\n📈 Critic向量 ({len(self.critic_vector)} 维):")
        if len(self.critic_vector) > 0:
            # 缩短长向量显示
            vec_display = np.array(self.critic_vector)
            if len(self.critic_vector) > 10:
                vec_display = np.concatenate([vec_display[:5], [np.nan], vec_display[-5:]])
            LOGGER.info(f"  {np.array2string(vec_display, precision=2, max_line_width=100)}")
        else:
            LOGGER.info("  Critic向量为空")

    def render_agent(self):
        # 展示智能体状态
        LOGGER.info(f"\n🤖 智能体状态:")
        if hasattr(self.agent, 'name'):
            LOGGER.info(f"  - 智能体名称: {self.agent.name}")
        if hasattr(self.agent, 'step_count'):
            LOGGER.info(f"  - 执行步数: {self.agent.step_count}")
        if hasattr(self.agent, 'epsilon'):
            LOGGER.info(f"  - 探索率 (ε): {self.agent.epsilon:.4f}")

    def render(self):
        """可视化系统当前状态 功能拆分到不同函数中"""
        pass


if __name__ == '__main__':
    pass
