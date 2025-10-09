'''
@Project ：SkyEngine 
@File    ：grid_factory_env.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/1/15 10:00 
'''
from typing import List, Tuple, Dict, Any, Optional
import copy
import numpy as np
import os

from pettingzoo import ParallelEnv
from pogema import GridConfig, pogema_v0
from pogema.wrappers.metrics import AgentsDensityWrapper, RuntimeMetricWrapper
from pogema_toolbox.create_env import MultiMapWrapper

from sky_simulator.environment.grid_factory.Agent.BaseAgent import BaseAgent
from sky_simulator.environment.grid_factory.grid_factory_env.Utils.create_env import (
    ProvideFutureTargetsWrapper, LogActions
)
from sky_logs.logger import LOGGER
from sky_simulator.registry import register_component
from sky_simulator.call_back.grid_factory_callback.callback_manager.CallbackManager import CallbackManager


@register_component("grid_factory")
class GridFactoryEnv(ParallelEnv):
    """
    基于Pogema的网格工厂环境
    
    功能特性:
    1. 使用Pogema作为底层网格环境
    2. 支持多智能体路径规划
    3. 集成事件系统和回调机制
    4. 支持工厂任务调度
    """
    metadata = {"render_modes": ["human"], "name": "grid_factory_env"}

    def __init__(self,
                 grid_config: Optional[GridConfig] = None,
                 agent: Optional[BaseAgent] = None):
        """
        初始化网格工厂环境
        Args:
            grid_config: Pogema网格配置
            agent: 智能体实例
            env_config: 环境配置
        """
        super().__init__()

        # 基础配置
        self.env_config = env_config or {}
        self.agent = agent

        # 环境状态
        self.env_timeline = 0  # 离散化的环境时间

        # Pogema环境
        self.pogema_env = None
        self.grid_config = grid_config or self._create_default_grid_config()

        # 工厂组件
        self.agents = []
        self.machines = []
        self.jobs = []

        # 索引结构
        self.hash_index = {
            'agents': {},
            'machines': {},
            'jobs': {},
        }

        # 智能体信息
        self.agent_positions = []
        self.agent_targets = []

        self._initialize_pogema_env()
        # 渲染相关
        self._last_observations = None

    def _create_default_grid_config(self) -> GridConfig:
        """创建默认的网格配置"""
        return GridConfig(
            num_agents=4,
            size=20,
            density=0.3,
            seed=42,
            max_episode_steps=256,
            obs_radius=5,
            collision_system='priority',
            observation_type='POMAPF',
            on_target='restart'
        )

    def _initialize_pogema_env(self):
        """初始化Pogema环境"""
        try:
            # 创建Pogema环境
            self.pogema_env = pogema_v0(grid_config=self.grid_config)

            # 添加包装器
            self.pogema_env = AgentsDensityWrapper(self.pogema_env)
            self.pogema_env = MultiMapWrapper(self.pogema_env)
            self.pogema_env = RuntimeMetricWrapper(self.pogema_env)

            # 日志记录
            self.pogema_env = LogActions(self.pogema_env)
            self.pogema_env = ProvideFutureTargetsWrapper(self.pogema_env)

            LOGGER.info(f"[GridFactoryEnv] Pogema环境初始化成功，智能体数量: {self.grid_config.num_agents}")

        except Exception as e:
            LOGGER.error(f"[GridFactoryEnv] Pogema环境初始化失败: {e}")
            self.use_pogema = False

    def refresh_status(self):
        """刷新环境状态"""
        try:
            # 初始化智能体信息
            self._initialize_agents_info()
            LOGGER.info("[GridFactoryEnv] 环境状态刷新成功")

        except Exception as e:
            LOGGER.error(f"[GridFactoryEnv] 环境状态刷新失败: {e}")

    def _initialize_agents_info(self):
        """初始化智能体信息"""
        if self.use_pogema and self.pogema_env:
            num_agents = self.grid_config.num_agents
            self.agents_info = [{'id': i, 'status': 'active'} for i in range(num_agents)]
            self.agent_positions = [(0, 0)] * num_agents
            self.agent_targets = [(0, 0)] * num_agents

    def create_hash_index(self):
        """创建高效获取组件的索引结构"""
        for agent in self.agents:
            self.hash_index['agents'][agent.id] = agent
        for job in self.jobs:
            self.hash_index['jobs'][job.id] = job
        for machine in self.machines:
            self.hash_index['machines'][machine.id] = machine

    def set_env_timeline(self, env_timeline: float):
        """设置环境时间线"""
        self.env_timeline = env_timeline

    def get_env_timeline(self) -> float:
        """获取环境时间线"""
        return self.env_timeline

    def action_space(self, agent: BaseAgent):
        """智能体动作空间"""
        if self.use_pogema and self.pogema_env:
            # 使用Pogema的动作空间
            return self.pogema_env.action_space(agent.agent_id)
        else:
            # 自定义动作空间
            decisions, step_time = agent.sample(
                self.agvs, self.machines, self.jobs, self.env_timeline
            )
            return {
                "decisions": decisions,
                "step_time": step_time
            }

    def _update_agent_positions_from_pogema(self, observations):
        """从Pogema观察更新智能体位置"""
        if observations and len(observations) > 0:
            for i, obs in enumerate(observations):
                if 'global_xy' in obs:
                    self.agent_positions[i] = tuple(obs['global_xy'])
                if 'target_xy' in obs:
                    self.agent_targets[i] = tuple(obs['target_xy'])

    def step(self, actions=None):
        """环境步进"""
        LOGGER.info(f"[GridFactoryEnv] 当前环境时间: {self.env_timeline}")

        # 处理动作
        if actions is None:
            actions = {'decisions': []}

        decisions = actions.get('decisions', [])
        step_time = actions.get('step_time', 1.0)

        LOGGER.info(f"[GridFactoryEnv] 步长时间: {step_time}, 决策数量: {len(decisions)}")

        # 执行环境步进
        while True:
            # 检查任务是否完成
            if self.check_job_finished():
                break

            # 执行当前决策
            res = self.env_step(decisions, step_time)
            if res:
                # 发生事件，继续执行
                decisions = []
            else:
                # 无事件，跳出循环
                break

        # 计算奖励和终止条件
        rewards = {}
        terminations = {}
        observations = {}

        if self.agent:
            rewards[self.agent.agent_id] = self.agent.reward({})
            terminations[self.agent] = False

        LOGGER.info(f"[GridFactoryEnv] 结束当前循环步")

        return observations, rewards, terminations, {}, {}

    def reset(self, seed=None, options=None):
        """重置环境"""
        LOGGER.info("[GridFactoryEnv] 重置环境")

        # 清理和重建
        self.set_env_timeline(0.0)

        # 重置Pogema环境
        if self.pogema_env:
            try:
                observations, infos = self.pogema_env.reset(seed=seed)
                self._update_agent_positions_from_pogema(observations)
                LOGGER.info("[GridFactoryEnv] Pogema环境重置成功")
            except Exception as e:
                LOGGER.error(f"[GridFactoryEnv] Pogema环境重置失败: {e}")

        # 刷新状态
        self.refresh_status()

        return {}, {}

    def render_observation(self):
        """渲染观察信息"""
        LOGGER.info(f"[GridFactoryEnv] 系统资源状态:")
        LOGGER.info(f"  - 作业数量: {len(self.jobs)}")
        LOGGER.info(f"  - 机器数量: {len(self.machines)}")
        LOGGER.info(f"  - AGV数量: {len(self.agvs)}")
        LOGGER.info(f"  - 智能体位置: {self.agent_positions}")
        LOGGER.info(f"  - 智能体目标: {self.agent_targets}")

    def render(self):
        """渲染环境（使用SVG输出，基于最近一次Pogema观测）"""
        if not self.use_pogema:
            LOGGER.info("[GridFactoryEnv] 非Pogema模式，暂不支持SVG渲染")
            return

        # 生成输出目录与文件名
        output_dir = self.env_config.get('render_svg_dir', 'renders')
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"frame_{int(self.env_timeline):06d}.svg")

        # 优先使用最近一次观测；若无，则尝试reset一次拿初始观测
        observations = self._last_observations
        if observations is None and self.pogema_env is not None:
            try:
                observations, _ = self.pogema_env.reset(seed=self.grid_config.seed)
                self._last_observations = observations
            except Exception as e:
                LOGGER.error(f"[GridFactoryEnv] 获取观测用于渲染失败: {e}")
                return

        # 渲染为SVG
        try:
            self._render_svg_from_observations(observations, file_path)
            LOGGER.info(f"[GridFactoryEnv] 已输出SVG渲染: {file_path}")
        except Exception as e:
            LOGGER.error(f"[GridFactoryEnv] SVG渲染失败: {e}")

    # ---------- 获取器方法 ----------
    def get_jobs(self) -> List:
        """获取作业列表"""
        return self.jobs

    def get_job_templates(self) -> List:
        """获取作业模板列表"""
        return self.job_templates

    def get_machines(self) -> List:
        """获取机器列表"""
        return self.machines

    def get_agvs(self) -> List:
        """获取AGV列表"""
        return self.agvs

    def get_graph(self):
        """获取图结构"""
        return self.graph

    def get_agents_info(self) -> List[Dict[str, Any]]:
        """获取智能体信息"""
        return self.agents_info

    def get_agent_positions(self) -> List[Tuple[int, int]]:
        """获取智能体位置"""
        return self.agent_positions

    def get_agent_targets(self) -> List[Tuple[int, int]]:
        """获取智能体目标"""
        return self.agent_targets

    def get_pogema_env(self):
        """获取Pogema环境实例"""
        return self.pogema_env

    def get_grid_config(self) -> GridConfig:
        """获取网格配置"""
        return self.grid_config

    def update_grid_config(self, new_config: GridConfig):
        """更新网格配置"""
        self.grid_config = new_config
        if self.use_pogema:
            self._initialize_pogema_env()


if __name__ == '__main__':
    # 测试代码
    from pogema import GridConfig

    # 创建测试配置
    config = GridConfig(
        num_agents=4,
        size=10,
        density=0.2,
        seed=42
    )

    # 创建环境
    env = GridFactoryEnv(grid_config=config)
    env.render()
    print("网格工厂环境创建成功")
