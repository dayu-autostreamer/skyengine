'''
@Project ：SkyEngine 
@File    ：grid_factory_env.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/1/15 10:00 
'''
from typing import List, Tuple, Dict, Any, Optional
import config
from sky_executor.grid_factory.grid_factory.Agent.BaseAgent import GridBaseAgent
from sky_logs.logger import LOGGER
from sky_executor.utils.registry import register_component
import yaml
from pathlib import Path

from sky_executor.grid_factory.grid_factory.grid_factory_env.Utils.single_step_svg import SingleStepAnimationMonitor
from pettingzoo import ParallelEnv
from pogema import GridConfig, pogema_v0, AnimationMonitor
from pogema_toolbox.registry import ToolboxRegistry
from pogema_toolbox.create_env import MultiMapWrapper

# 禁用 ToolboxRegistry 日志输出
ToolboxRegistry.setup_logger(level="CRITICAL", sink=None)


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
                 agent: Optional[GridBaseAgent] = None):
        """
        初始化网格工厂环境
        Args:
            grid_config: Pogema网格配置
            agent: 智能体实例
            env_config: 环境配置
        """
        super().__init__()

        # 基础配置
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

        # 动画保存路径
        self.svg_pic = None
        self._initialize_pogema_env()

        self.register_maps()

    def register_maps(self):
        ToolboxRegistry._maps = {}
        for maps_file in Path(config.MAPF_GPT_DIR).rglob('maps.yaml'):
            with open(maps_file, 'r') as f:
                maps = yaml.safe_load(f)
            ToolboxRegistry.register_maps(maps)

    def get_maps(self):
        res = ToolboxRegistry.get_maps()
        map_name = []
        for _map in res:
            map_name.append(_map)
        return map_name

    def get_jobs(self):
        return []

    def _create_default_grid_config(self) -> GridConfig:
        """创建默认的网格配置"""
        return GridConfig(
            num_agents=4,
            size=20,
            density=0.3,
            seed=42,
            max_episode_steps=256,
            obs_radius=5,
            # collision_system='priority',
            # observation_type='POMAPF',
            on_target='restart'
        )

    def _initialize_pogema_env(self):
        """初始化Pogema环境"""
        try:
            # 创建Pogema环境
            self.pogema_env = pogema_v0(grid_config=self.grid_config)

            # 添加包装器 todo 当前这些没进行测试
            # self.pogema_env = AgentsDensityWrapper(self.pogema_env)
            self.pogema_env = MultiMapWrapper(self.pogema_env)  # 支持多地图
            # self.pogema_env = RuntimeMetricWrapper(self.pogema_env)

            # 日志记录
            # self.pogema_env = LogActions(self.pogema_env)
            # self.pogema_env = ProvideFutureTargetsWrapper(self.pogema_env)

            # 添加图像记录包装器,包括单步的和多步的
            self.pogema_env = SingleStepAnimationMonitor(self.pogema_env)
            self.pogema_env = AnimationMonitor(self.pogema_env)
            print(f"请看这里：{self.pogema_env.get_obstacles().astype(int).tolist()}")
            LOGGER.info(f"[GridFactoryEnv] Pogema环境初始化成功，智能体数量: {self.grid_config.num_agents}")

        except Exception as e:
            LOGGER.error(f"[GridFactoryEnv] Pogema环境初始化失败: {e}")
            self.use_pogema = False

    def refresh_status(self):
        """刷新Agent状态"""
        try:
            # 初始化智能体信息
            if self.pogema_env:
                num_agents = self.grid_config.num_agents
                self.agents_info = [{'id': i, 'status': 'active'} for i in range(num_agents)]
                self.agent_positions = [(0, 0)] * num_agents
                self.agent_targets = [(0, 0)] * num_agents
            LOGGER.info("[GridFactoryEnv] 环境状态刷新成功")
        except Exception as e:
            LOGGER.error(f"[GridFactoryEnv] 环境状态刷新失败: {e}")

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

    def action_space(self, agent: GridBaseAgent):
        """智能体动作空间"""
        if self.pogema_env:
            # 使用Pogema的动作空间
            return self.pogema_env.action_space(agent.agent_id)
        else:
            # 自定义动作空间
            decisions, step_time = agent.sample(
                self.agents, self.machines, self.jobs, self.env_timeline
            )
            return {
                "decisions": decisions,
                "step_time": step_time
            }

    def machine_step(self, actions=None):
        # 计算奖励和终止条件
        rewards = {}
        terminations = {}
        observations = {}
        return observations, rewards, terminations, {}, {}

    def machine_reset(self):
        observations = {}
        infos = {}
        return observations, infos

    def step(self, actions=None):
        LOGGER.info(f"[GridFactoryEnv] 当前环境时间: {self.env_timeline}")
        self.env_timeline += 1

        # 存储输入动作，用于 unpack
        agent_actions, machine_actions = self.unpack_input(actions)

        # 执行 machine 层步进
        m_obs, m_reward, m_terminated, m_truncated, m_info = \
            self.machine_step(machine_actions)

        # 执行 AGV 层步进
        a_obs, a_reward, a_terminated, a_truncated, a_info = \
            self.pogema_env.step(agent_actions)

        machine_info = [m_obs, m_reward, m_terminated, m_truncated, m_info]
        agent_info = [a_obs, a_reward, a_terminated, a_truncated, a_info]
        LOGGER.info(f"[GridFactoryEnv] 结束当前循环步")

        # 合并输出
        observations, rewards, terminations, truncated, info = self.pack_output(machine_info, agent_info)

        return observations, rewards, terminations, truncated, info

    def reset(self, seed=None, options=None):
        """重置环境"""
        LOGGER.info("[GridFactoryEnv] 重置环境")

        # 清理和重建
        self.set_env_timeline(0)
        m_list = []
        a_list = []

        # 重置Job-Machine相关环境
        try:
            m_observations, m_infos = self.machine_reset()
            m_list = [m_observations, m_infos]
            LOGGER.info("[GridFactoryEnv] Machine重置成功")
        except Exception as e:
            LOGGER.error(f"[GridFactoryEnv] Machine重置失败: {e}")

        # 重置Map-AGV相关环境
        try:
            a_observations, a_infos = self.pogema_env.reset(seed=seed)
            a_list = [a_observations, a_infos]
            LOGGER.info("[GridFactoryEnv] Pogema环境重置成功")
        except Exception as e:
            LOGGER.error(f"[GridFactoryEnv] Pogema环境重置失败: {e}")

        # 重置Agent相关状态
        self.refresh_status()

        obs, rew, term, trunc, info = self.pack_output(m_list, a_list)

        return obs, info

    def render(self):
        """渲染环境"""
        self.pogema_env.render()

    # ---------- 获取器方法 ----------
    def get_jobs(self) -> List:
        """获取作业列表"""
        return self.jobs

    def get_machines(self) -> List:
        """获取机器列表"""
        return self.machines

    def get_agents(self) -> List:
        """获取AGV列表"""
        return self.agents

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

    def unpack_input(self, actions):
        """将输入的 actions 拆分为机器与智能体两部分"""
        # 假设 self.input_actions 是外部传入的总动作字典
        machine_actions = actions.get("machine_actions", {})
        agent_actions = actions.get("agent_actions", {})
        return agent_actions, machine_actions

    def pack_output(self, machine_info, agent_info):
        """动态合并 machine 和 agent 输出"""

        def unpack(info):
            """支持 (obs, reward, term, trunc, info) 或 (obs, info)"""
            if len(info) == 5:
                obs, reward, term, trunc, inf = info
            elif len(info) == 2:
                obs, inf = info
                reward, term, trunc = {}, {}, {}
            else:
                raise ValueError(f"Unexpected tuple length: {len(info)}")
            return obs, reward, term, trunc, inf

        # 动态解包
        m_obs, m_reward, m_term, m_trunc, m_info = unpack(machine_info)
        a_obs, a_reward, a_term, a_trunc, a_info = unpack(agent_info)

        # 合并为标准输出结构
        observations = {
            "machine_observation": m_obs,
            "agent_observation": a_obs
        }
        rewards = {
            "machine_reward": m_reward,
            "agent_reward": a_reward
        }
        terminations = {
            "machine_done": m_term,
            "agent_done": a_term
        }
        truncations = {
            "machine_truncated": m_trunc,
            "agent_truncated": a_trunc
        }
        infos = {
            "machine_info": m_info,
            "agent_info": a_info
        }

        return observations, rewards, terminations, truncations, infos
