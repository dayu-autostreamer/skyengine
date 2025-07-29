import os
import threading
from typing import List
from typing import Callable

import yaml

from sky_simulator.lifecycle.bootstrap import bootstrap
from sky_simulator.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
from sky_simulator.packet_factory.packet_factory_env.Job.Job import Job
from sky_simulator.packet_factory.packet_factory_env.Machine.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Agv.AGV import AGV
import config

from backend.service import file_service

from sky_logs.logger import Logger

LOGGER = Logger(log_path=config.BACKEND_LOG_DIR, name="backend").logger


class ThreadPool:
    def __init__(self):
        self.threads = []
        self.stop_event = threading.Event()

    def __len__(self):
        return len(self.threads)

    def submit(self, func: Callable, *args, **kwargs):
        """提交任务到线程池,确保当前只有单个在修改env"""
        if len(self.threads) >= 1:
            self.shutdown()
        try:
            thread = threading.Thread(target=func, args=(self.stop_event, *args), kwargs=kwargs)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
        except Exception as e:
            LOGGER.error(e)

    def shutdown(self, wait=False):
        """请求线程退出（通过事件标志）"""
        self.stop_event.set()  # 通知线程退出
        if wait:
            for thread in self.threads:
                thread.join()
        self.threads = []  # 清空缓冲池
        self.stop_event.clear()  # 清除退出标志
        LOGGER.info("[INFO] 线程池已关闭")


class BackendCore:
    def __init__(self):
        # 环境本身
        self.env: PacketFactoryEnv = None
        # 线程池,但是实际按照当前的core实现大概只能有单个线程(受到env限制)...后续再修改吧!
        self.thread_pool = ThreadPool()

    def bootstrap(self, stop_event: threading.Event, target_factory: str):
        specific_config = file_service.get_new_config_file(target_factory)
        # 创建环境与智能体
        env, agent = bootstrap(specific_config)

        self.env = env

        # 重置环境
        observations = env.reset()

        # 运行一个 episode（直到结束）
        while not env.env_is_finished() and not stop_event.is_set():
            # 输入获得环境状态并决策
            actions = env.action_space(agent)

            # agent在外部决策
            observations, rewards, terminations, truncations, infos = env.step(actions)

            # 渲染当前状态（控制台打印）
            env.render()

            # 更新 done 状态
            done = terminations

        LOGGER.info(f"total makespan: {env.env_timeline}s")

    def factory_start(self):
        print("factory_start")
        self.env.env_visualizer.run()

    def factory_pause(self):
        print("factory_pause")
        self.env.env_visualizer.pause()

    def factory_reset(self):
        print("factory_reset")
        self.env.env_visualizer.restart()

    def change_factory_speed(self, speed_level: int):
        print(f"change_factory_speed: {speed_level}")
        self.env.env_visualizer.change_speed(speed_level)

    def get_agvs(self):
        agvs: List[AGV] = self.env.getAGVs()
        agv_list = [{"id": agv.id} for agv in agvs]
        return agv_list

    def pause_agv(self, agv_id):
        print("pause_agv")
        self.env.env_visualizer.pause_agv(agv_id)

    def resume_agv(self, agv_id):
        print("resume_agv")
        self.env.env_visualizer.resume_agv(agv_id)

    def get_machines(self):
        machines: List[Machine] = self.env.getMachines()
        machine_list = [{"id": machine.id} for machine in machines]
        return machine_list

    def pause_machine(self, machine_id):
        print("pause_machine")
        self.env.env_visualizer.pause_machine(machine_id)

    def resume_machine(self, machine_id):
        print("resume_machine")
        self.env.env_visualizer.resume_machine(machine_id)

    def get_jobs(self):
        jobs: List[Job] = self.env.getJobs()
        job_list = [{"id": job.id} for job in jobs]
        return job_list

    def add_job(self, job_id: int):
        print(f"Job {job_id} added")
        self.env.env_visualizer.add_job(job_id)

    def get_jobs_progress(self):
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
            print(e)
        return pic
