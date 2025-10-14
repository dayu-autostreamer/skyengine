import random
import time

from sky_simulator.environment.grid_factory.Agent.BaseAgent import GridBaseAgent
from sky_simulator.environment.grid_factory.grid_factory_env.grid_factory_env import (
    GridFactoryEnv,
)
import config

from backend.service.grid import file_service
from backend.service.grid import agent_service
from backend.environment.utils.thread_pool import ThreadPool

from sky_logs.logger import Logger

LOGGER = Logger(log_path=config.BACKEND_LOG_DIR, name="backend").logger


class GridCore:
    def __init__(self):
        # 环境本身
        self.env: GridFactoryEnv = None
        self.agv_agent = None
        self.system_agent = None
        self.hyper_config = None
        self.thread_pool = ThreadPool()

        self.bootstrap()

    def bootstrap(self):
        # 获取工厂和job配置,暂时还没有实现 todo
        grid_config, job_config, agv_agent_config, system_agent_config, hyper_config = file_service.get_default_config()

        # 创建环境与智能体
        self.env = GridFactoryEnv(grid_config)
        self.agv_agent = agent_service.create_agv_agent(agv_agent_config)
        self.system_agent = agent_service.create_system_policy(system_agent_config)
        self.hyper_config = hyper_config

    def reset(self):
        obs, info = self.env.reset(seed=self.hyper_config.get('seed', random.seed))
        return obs, info

    def run(self):
        # 重置环境
        obs, info = self.env.reset(seed=self.hyper_config.get('seed', random.seed))

        # 开始运行环境
        step_time = self.hyper_config.get('step_time', 1)
        while True:
            time.sleep(step_time)
            agent_actions = self.agv_agent.act(obs['agent_observation'])
            system_actions = self.system_agent.act(obs['machine_observation'])
            obs, reward, terminated, truncated, info = self.env.step({'agent_actions': agent_actions,
                                                                      'machine_actions': system_actions})
            self.env.render()
            if all(terminated) or all(truncated):
                break

        return info

    def render_map(self):
        self.thread_pool.submit(self.run)

    def reset_map(self):
        self.thread_pool.submit(self.run)

    def pause_map(self):
        self.thread_pool.submit(self.run)

    def resume_map(self):
        self.thread_pool.submit(self.run)

    def display_map(self):
        image_bytes = self.env.render()
        return image_bytes
        # return StreamingResponse(image_bytes, media_type="image/png")
