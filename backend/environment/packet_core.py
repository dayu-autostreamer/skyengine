import threading
from typing import List

from sky_simulator.lifecycle.bootstrap import bootstrap
from sky_simulator.environment.packet_factory.Agent import BaseAgent
from sky_simulator.environment.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
from sky_simulator.environment.packet_factory.packet_factory_env.Job.Job import Job
from sky_simulator.environment.packet_factory.packet_factory_env.Machine.Machine import Machine
from sky_simulator.environment.packet_factory.packet_factory_env.Agv.AGV import AGV
import config

from backend.service.packet import file_service
from backend.environment.utils.thread_pool import ThreadPool

from sky_logs.logger import Logger

LOGGER = Logger(log_path=config.BACKEND_LOG_DIR, name="backend").logger


class BackendCore:
    def __init__(self):
        # 环境本身
        self.env: PacketFactoryEnv = None
        self.agent: BaseAgent = None
        # 线程池,但是实际按照当前的core实现大概只能有单个线程(受到env限制)...后续再修改吧!
        self.thread_pool = ThreadPool()

    def bootstrap(self, stop_event: threading.Event, target_factory: str):
        specific_config = file_service.get_new_config_file(target_factory)
        # 创建环境与智能体
        env, agent = bootstrap(specific_config)

        self.env = env
        self.agent = agent

        # 重置环境
        env.reset()

        # 运行一个 episode（直到结束）
        while not self.env.env_is_finished() and not stop_event.is_set():
            # 输入获得环境状态并决策
            actions = self.env.action_space(self.agent)

            # agent在外部决策
            observations, rewards, terminations, truncations, infos = self.env.step(actions)

            # 渲染当前状态（控制台打印）
            self.env.render()

            # 更新 done 状态
            done = terminations

        LOGGER.info(f"total makespan: {self.env.env_timeline}s")

    def is_factory_alive(self):
        return self.env is not None

    def factory_start(self):
        LOGGER.info("factory_start")
        self.env.env_visualizer.run()

    def factory_pause(self):
        LOGGER.info("factory_pause")
        self.env.env_visualizer.pause()

    def factory_reset(self):
        LOGGER.info("factory_reset")
        self.env.env_visualizer.restart()

    def change_factory_speed(self, speed_level: int):
        LOGGER.info(f"change_factory_speed: {speed_level}")
        self.env.env_visualizer.change_speed(speed_level)

    def get_agvs(self):
        if self.env is None:
            return []
        agvs: List[AGV] = self.env.getAGVs()
        agv_list = [{"id": agv.id} for agv in agvs]
        return agv_list

    def pause_agv(self, agv_id):
        LOGGER.info("pause_agv")
        self.env.env_visualizer.pause_agv(agv_id)

    def resume_agv(self, agv_id):
        LOGGER.info("resume_agv")
        self.env.env_visualizer.resume_agv(agv_id)

    def get_machines(self):
        if self.env is None:
            return []
        machines: List[Machine] = self.env.getMachines()
        machine_list = [{"id": machine.id} for machine in machines]
        return machine_list

    def pause_machine(self, machine_id):
        LOGGER.info("pause_machine")
        self.env.env_visualizer.pause_machine(machine_id)

    def resume_machine(self, machine_id):
        LOGGER.info("resume_machine")
        self.env.env_visualizer.resume_machine(machine_id)

    def get_job_templates(self):
        if self.env is None:
            return []
        jobs: List[Job] = self.env.getJobTemplates()
        job_list = [{"id": job.id} for job in jobs]
        return job_list

    def add_job(self, job_id: int):
        LOGGER.info(f"Job {job_id} added")
        self.env.env_visualizer.add_job(job_id)

    def get_jobs_progress(self):
        if self.env is None:
            return []
        jobs: List[Job] = self.env.getJobs()
        job_list = [{"id": job.id, "status": job.get_status().name, "progress": round(job.get_progress() * 100.0, 2)}
                    for job in jobs]
        return job_list

    def render_map(self, target_factory):
        """插入配置文件,启动当前渲染地图"""
        # 启动系统!
        self.thread_pool.submit(self.bootstrap, target_factory)

    def get_map_current(self):
        pic = b''
        try:
            pic = self.env.env_visualizer.get_map()
        except Exception as e:
            LOGGER.info(e)
        return pic

    def set_agent(self, new_agent):
        self.agent = new_agent
