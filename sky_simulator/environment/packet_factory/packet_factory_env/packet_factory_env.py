from typing import List, Tuple
import copy

from pettingzoo import ParallelEnv

from sky_simulator.environment.packet_factory.Agent import BaseAgent
from sky_simulator.environment.packet_factory.packet_factory_env.Job.Job import Job
from sky_simulator.environment.packet_factory.packet_factory_env.Machine.Machine import Machine
from sky_simulator.environment.packet_factory.packet_factory_env.Job.Operation import Operation
from sky_simulator.environment.packet_factory.packet_factory_env.Agv.AGV import AGV
from sky_simulator.environment.packet_factory.packet_factory_env.Graph.Graph import Graph
from sky_simulator.environment.packet_factory.packet_factory_env.Utils.util import EnvStatus
from sky_logs.logger import LOGGER
from sky_simulator.registry import register_component
from sky_simulator.call_back.packet_factory_callback.callback_manager.CallbackManager import CallbackManager


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

        self.job_templates = []

        # 环境本身的状态,事件队列,智能体相关的状态等
        self.env_timeline: float = 0
        self.env_visualizer = None
        self.event_queue = None
        self.agent = agent
        self.hash_index = {
            'agvs': {},
            'machines': {},
            'jobs': {},
        }
        self.status = EnvStatus.PAUSED
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
        刷新当前环境引入的额外组件
        :return:
        """
        # 环境创建 当场调用即可
        self.jobs, self.machines, self.agvs, self.graph = self.callback_manager.get('load_graph')()
        self.job_templates = copy.deepcopy(self.jobs)
        self.createHashIndex()

        # 可视化组件赋值 不需要当场调用
        self.env_visualizer = self.callback_manager.get('initialize_visualizer')
        self.env_visualizer.visualize_env(env=self)

        # 事件队列 不需要当场调用
        self.event_queue = self.callback_manager.get('event_queue')
        self.event_queue.set_env(env=self)

        LOGGER.info("Environment Initialized Successfully.")

    def action_space(self, agent: BaseAgent):
        decisions, step_time = agent.sample(self.agvs,
                                            self.machines,
                                            self.jobs,
                                            self.env_timeline)  # type: List[Tuple[Operation, AGV,  Machine]], float
        return {
            "decisions": decisions,
            "step_time": step_time
        }

    def check_job_finished(self):
        # 检测任务是否执行完成
        if self.status == EnvStatus.FINISHED:
            return True
        else:
            cnt = 0
            for job in self.jobs:
                if job.is_finished(self.env_timeline):
                    cnt += 1
            res = False
            if cnt == len(self.jobs):
                self.agent.alive = False
                self.status = EnvStatus.WAITING
                res = True
        return res

    def deal_event(self):
        """
        调用event_queue取出队列中current_time之前的事件并调用.
        """
        # ---------- 检测事件 ----------
        try:
            command_list = self.env_visualizer.getBuffered()
        except TypeError as e:
            LOGGER.warning("Current Visualizer Don't support Event.")
            return

        # ---------- 翻译创建事件 ----------
        for command in command_list:
            payload = {}
            if command['type'] == 'AGV':
                current_agv: AGV = command['data']
                payload = current_agv.pack()
            elif command['type'] == 'MACHINE':
                current_machine: Machine = command['data']
                payload = current_machine.pack()
            elif command['type'] == 'JOB':
                current_job: Job = command['data']
                payload['job'] = current_job
            else:
                pass

            current_event = self.event_queue.event_manager.create_event(command['event_type'],
                                                                        *[command['event_method'], payload])
            self.event_queue.add_event(self.env_timeline, event=current_event)

        # ---------- 执行事件 ----------
        ready_event = self.event_queue.pop_ready_events(self.env_timeline)
        self.event_queue.deal_event(ready_event, self)

        if len(ready_event) == 0:
            return False
        else:
            return True

    def env_step(self, actions: List[Tuple[Operation, AGV, Machine]], step_time: float) -> bool:
        """
        环境的单时间片执行,返回当前有无事件发生
        """
        event_happen = False
        if self.status == EnvStatus.WAITING:
            # ---------- 更新可视化 ----------
            self.env_visualizer.visualize_env()
            # ---------- 触发事件队列相关机制 ----------
            event_happen = self.deal_event()
        elif self.status == EnvStatus.PAUSED:
            # ---------- 更新可视化 ----------
            self.env_visualizer.visualize_env()
            # ---------- 触发事件队列相关机制 ----------
            event_happen = self.deal_event()
        elif self.status == EnvStatus.RUNNING:
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

            # ---------- 更新可视化 ----------
            self.env_visualizer.visualize_env()

            # ---------- 触发事件队列相关机制 ----------
            event_happen = self.deal_event()

            # ---------- 处理全局时间 ----------
            self.env_timeline += step_time

        return event_happen

    def step(self, actions=None):
        LOGGER.info(f"--------- 当前环境时间为{self.env_timeline} ---------")

        # === 0. Agent 决策动作 ===
        decisions = actions['decisions']

        step_time = 1

        LOGGER.info(f"step_time: {step_time},decisions: {decisions}")

        # === 1. 提取state,发送给状态转移函数并返回 ===
        while True:
            # 确定环境是否执行完毕
            if self.check_job_finished():
                break
            # 执行当前决策,返回是否发生不确定性事件
            res = self.env_step(decisions, step_time)
            if res:
                # 未发生不确定性事件,继续执行
                decisions = []
            else:
                # 发生不确定性事件,弹出再进行决策
                break

        # === 2. 统计完成状态，计算奖励 ===
        # 奖励,看情况设置,感觉实际上当前也不需要设置,因为传入了Agent本身
        rewards = {self.agent.agent_id: self.agent.reward({})}
        # 终止信号,看情况设置,应该还是需要的
        terminations = {self.agent}
        # 注意:实际上这里的obs没啥用了,因为会传入agent进入环境内部,sample时可以直接获取所有数据,获得Agent观察的环境信息
        obs = {}

        #  === 3. 更新可视化 ===
        self.env_visualizer.visualize_env()

        #  === 4. 触发事件队列相关机制 ===
        event_happen = self.deal_event()

        LOGGER.info(f"--------- 结束当前循环步 ---------")

        return obs, rewards, terminations, {}, {}

    def reset(self, seed=None, options=None):
        # ---------- 清理重建阶段 ----------
        self.set_env_timeline(0)
        self.refresh_status()

    def render(self):
        """可视化系统当前状态 功能拆分到不同函数中"""
        pass

    def createHashIndex(self):
        """
        创建高效获取组件的结构
        """
        for agv in self.agvs:
            self.hash_index['agvs'][agv.id] = agv
        for job in self.jobs:
            self.hash_index['jobs'][job.id] = job
        for machine in self.machines:
            self.hash_index['machines'][machine.id] = machine

    def getJobs(self) -> List[Job]:
        return self.jobs

    def getJobTemplates(self) -> List[Job]:
        return self.job_templates

    def getMachines(self) -> List[Machine]:
        return self.machines

    def getAGVs(self) -> List[AGV]:
        return self.agvs

    def getGraph(self) -> Graph:
        return self.graph

    def env_is_finished(self) -> bool:
        return self.status == EnvStatus.FINISHED

    def event_set_paused(self):
        self.status = EnvStatus.PAUSED

    def event_set_running(self):
        self.status = EnvStatus.RUNNING

    def event_set_restart(self):
        self.status = EnvStatus.EXCEPTION


if __name__ == '__main__':
    pass
