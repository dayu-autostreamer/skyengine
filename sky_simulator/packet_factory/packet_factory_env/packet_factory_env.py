from typing import List, Tuple

from pettingzoo import ParallelEnv

from sky_simulator.packet_factory.Agent import BaseAgent
from sky_simulator.packet_factory.packet_factory_env.Job.Job import Job
from sky_simulator.packet_factory.packet_factory_env.Machine.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Job.Operation import Operation
from sky_simulator.packet_factory.packet_factory_env.Agv.AGV import AGV
from sky_simulator.packet_factory.packet_factory_env.Graph.Graph import Graph
from sky_simulator.packet_factory.packet_factory_env.Utils.logger import LOGGER
from sky_simulator.registry import register_component
from sky_simulator.call_back.callback_manager.CallbackManager import CallbackManager


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
        self.graph = None

        # 环境本身的状态,事件队列,智能体相关的状态等
        self.env_timeline: float = 0
        self.env_visualizer = None
        self.event_queue = None
        self.agent = agent
        self.hash_index={
            'agvs':{},
            'machines':{},
            'jobs':{},
        }

        # 回调管理
        self.callback_manager: CallbackManager = CallbackManager()

    # ---------- 自定义状态更新函数 ----------
    def set_env_timeline(self, env_timeline: float):
        self.env_timeline = env_timeline

    def get_env_timeline(self) -> float:
        return self.env_timeline

    def set_callback_manager(self, callback_manager: CallbackManager):
        self.callback_manager = callback_manager
        LOGGER.info("CallbackManager Created Successfully.")

    def refresh_status(self):
        """
        刷新当前环境的graph和agv
        :return:
        """
        # 环境创建 当场调用即可
        self.jobs, self.machines, self.agvs, self.graph = self.callback_manager.get('load_graph')()
        self.createHashIndex()

        # 可视化组件赋值 不需要当场调用
        self.env_visualizer = self.callback_manager.get('initialize_visualizer')
        self.env_visualizer.visualize_env(env=self)

        # 事件队列 不需要当场调用
        self.event_queue = self.callback_manager.get('event_queue')
        self.event_queue.set_env(env=self)

        LOGGER.info("Environment Initialized Successfully.")

    def action_space(self, agent):
        decisions, step_time = agent.sample(self.agvs, self.machines,
                                            self.jobs)  # type: List[Tuple[Operation, AGV,  Machine]], float
        return {
            "decisions": decisions,
            "step_time": step_time
        }

    def deal_event(self):
        """
        调用event_queue取出队列中current_time之前的事件并调用.
        """
        # todo：event有个函数判断是否有不确定事件发生过（包括三类：agv停止/释放，机器停止/释放，额外增加订单）
        # 启动：bool变量变成True，暂停：bool变量变成False，
        # 重启：从这里break出去，一路break到最外面，重置agent和env（可以设计状态，每个step的地方都检测状态，一路break出去）
        # while (bool变量) sleep

        ready_event = self.event_queue.pop_ready_events(self.env_timeline)
        for event in ready_event:
            print(event)
            self.event_queue.event_manager.deal_event(event,self)

        if len(ready_event) == 0:
            return False
        else:
            return True

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

        # ---------- 检测事件 ----------
        event_happen = self.deal_event()

        # 更新可视化（每env_step更新一次）
        self.env_visualizer.visualize_env()

        # === 处理全局时间 ===
        self.env_timeline += step_time

        return event_happen

        # 判断是否有不确定事件发生过，若有则返回True

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
        # rewards = {self.agent.agent_id: self.agent.reward(self.critic_vector)}
        rewards = {self.agent.agent_id: self.agent.reward({})}
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

    # ---------- 渲染函数 ----------
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

    def createHashIndex(self):
        """
        创建高效获取组件的结构
        """
        for agv in self.agvs:
            self.hash_index['agvs'][agv.id]=agv
        for job in self.jobs:
            self.hash_index['jobs'][job.id]=job
        for machine in self.machines:
            self.hash_index['machines'][machine.id]=machine

    def getJobs(self) -> List[Job]:
        return self.jobs

    def getMachines(self) -> List[Machine]:
        return self.machines

    def getAGVs(self) -> List[AGV]:
        return self.agvs

    def getGraph(self) -> Graph:
        return self.graph



if __name__ == '__main__':
    pass
