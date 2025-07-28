import os
import threading
from typing import List

from sky_simulator.lifecycle.bootstrap import bootstrap
from sky_logs.logger import LOGGER
from sky_simulator.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
from sky_simulator.packet_factory.packet_factory_env.Job.Job import Job
from sky_simulator.packet_factory.packet_factory_env.Machine.Machine import Machine
from sky_simulator.packet_factory.packet_factory_env.Agv.AGV import AGV
import config


class BackendCore:
    def __init__(self):
        self.env: PacketFactoryEnv = None

    def bootstrap(self):
        # todo 动态挂载
        config_path = os.path.join(config.CONFIG_DIR, 'application_config.yaml')

        # 创建环境与智能体
        env, agent = bootstrap(config_path)

        self.env = env

        # 重置环境
        observations = env.reset()

        # 运行一个 episode（直到结束）
        while not env.env_is_finished():
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

    def render_map(self):
        """插入配置文件,启动当前渲染地图"""
        # 配置文件插入
        # todo
        print("系统启动!")
        # 启动系统
        threading.Thread(target=self.bootstrap).start()

    def get_map_current(self):
        pic = None
        try:
            pic = self.env.env_visualizer.get_map()
        except Exception as e:
            print(e)
        return pic
