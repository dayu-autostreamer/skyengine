"""
@Project ：SkyEngine
@File    ：grid_factory_env.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2025/1/15 10:00
"""

from typing import List, Tuple, Optional

from pettingzoo import ParallelEnv
from pogema.grid import Grid
from pogema import GridConfig, AnimationMonitor

from joint_sim.utils.structure import (
    MachineConfig,
    JobConfig,
)

from joint_sim.assign_env import (
    PogemaLifeLongWithAssign,
)
from joint_sim.utils.machine import (
    generate_machines,
)
from joint_sim.utils.job import generate_jobs
from joint_sim.utils.logger import LOGGER


class GridFactoryEnv(ParallelEnv):
    """
    基于Pogema的网格工厂环境

    功能特性:
    1. 使用Pogema作为底层网格环境
    2. 支持多智能体路径规划
    3. 集成事件系统和回调机制
    4. 支持工厂任务调度

    注意环境reset之后才能有grid相关结构
    """

    metadata = {"render_modes": ["human"], "name": "grid_factory_env"}

    def __init__(
        self,
        grid_config: Optional[GridConfig] = None,
        machine_config: Optional[MachineConfig] = None,
        job_config: Optional[JobConfig] = None,
        random_target=False,
    ):
        """
        初始化网格工厂环境
        Args:
            grid_config: Pogema网格配置
            agent: 智能体实例
            env_config: 环境配置
        """
        super().__init__()

        # 环境状态
        self.env_timeline = 0  # 离散化的环境时间

        # Pogema环境
        self.pogema_env: PogemaLifeLongWithAssign | None = None
        self.grid_config = grid_config or self._create_default_grid_config()

        # 机器组件 也就是路由的起始点和终止点
        self.machine_config = machine_config or self._create_default_machine_config()

        # 任务组件
        self.job_config = job_config or self._create_default_job_config()

        # 动画保存路径
        self.svg_pic = None
        self.initialize_pogema_env(random_target)
        self.init_machines = self.initialize_machine_env()
        self.init_jobs = self.initialize_job_env()
        
    def _create_default_grid_config(self) -> GridConfig:
        """创建默认的网格配置"""
        return GridConfig(
            num_agents=4,
            size=8,
            density=0.1,
            seed=42,
            max_episode_steps=256,
            obs_radius=5,
            on_target="restart",
        )

    def _create_default_machine_config(self):
        """创建默认的机器配置"""
        return MachineConfig(
            num_machines=8,
            strategy="random",
            seed=42,
            zones=4,
            grid_spacing=5,
            noise=1.0,
        )

    def _create_default_job_config(self):
        """创建默认的任务配置"""
        return JobConfig(
            num_jobs=6,
            min_ops_per_job=2,
            max_ops_per_job=3,
            min_proc_time=2,
            max_proc_time=7,
            machine_choices=2,
            total_machines=self.machine_config.num_machines,
            seed=42,
        )

    @property
    def machine_possible_positions(self):
        return self.grid_config.possible_targets_xy

    @property
    def current_targets(self):
        return self.pogema_env.grid.finishes_xy

    def add_metrics_wrapper(self, wrappers):
        for wrapper in wrappers:
            self.pogema_env = wrapper(self.pogema_env)
        LOGGER.info(f"[GridFactoryEnv] Pogema环境添加了{len(wrappers)}个包装指标收集器")

    def initialize_machine_env(self):
        grid: Grid = Grid(grid_config=self.grid_config)
        grid.get_obstacles()
        machines = generate_machines(grid.get_obstacles(), self.machine_config)
        self.grid_config.possible_targets_xy = [m.location for m in machines]
        return machines

    def initialize_pogema_env(self, random_target=False):
        """初始化Pogema环境"""
        # 创建Pogema环境
        self.pogema_env = PogemaLifeLongWithAssign(
            grid_config=self.grid_config, random_target=random_target
        )
        # 添加包装器
        self.pogema_env = AnimationMonitor(self.pogema_env)
        LOGGER.info(
            f"[GridFactoryEnv] Pogema环境初始化成功，智能体数量: {self.grid_config.num_agents}"
        )

    def initialize_job_env(self):
        """
        初始化 Job 层任务系统：
        1. 创建机器和 Job
        2. 调用调度器生成加工计划
        3. 存储初始调度结果
        """
        LOGGER.info("[GridFactoryEnv] 初始化 Job 层任务...")

        self.job_config = self._create_default_job_config()
        jobs = generate_jobs(self.job_config)

        return jobs

    def set_env_timeline(self, env_timeline: int):
        """设置环境时间线"""
        self.env_timeline = env_timeline

    def show_actions(self, actions):
        from joint_sim.utils.pic_drawer import pretty_print_step

        pretty_print_step(self.env_timeline, actions)

    
    def show_jobs(self,):
        from joint_sim.utils.pic_drawer import pretty_print_jobs
        pretty_print_jobs(self.pogema_env.jobs)
    
    def step(self, actions=None):
        self.env_timeline += 1

        (
            job_actions,
            task_actions,
            agent_actions,
        ) = self.unpack_input(actions)

        j_obs, j_reward, j_terminated, j_truncated, j_info = self.pogema_env.job_step(
            job_actions
        )
        t_obs, t_reward, t_terminated, t_truncated, t_info = self.pogema_env.task_step(
            task_actions
        )
        a_obs, a_reward, a_terminated, a_truncated, a_info = self.pogema_env.step(
            agent_actions
        )

        # 合并输出
        observations, rewards, terminations, truncated, info = self.pack_output(
            [j_obs, j_reward, j_terminated, j_truncated, j_info],
            [t_obs, t_reward, t_terminated, t_truncated, t_info],
            [a_obs, a_reward, a_terminated, a_truncated, a_info],
        )

        return observations, rewards, terminations, truncated, info

    def reset(self, seed=None):
        LOGGER.info("[GridFactoryEnv] 重置环境")

        self.set_env_timeline(0)
        # --- 重置 Pogema 相关 ---
        a_observations, a_infos = self.pogema_env.reset(seed=seed)

        # --- 重置任务相关，使用可能位置 ---
        t_observations, t_infos = self.pogema_env.machine_reset(self.init_machines)

        # --- 重置任务相关，使用任务列表 ---
        j_observations, j_infos = self.pogema_env.job_reset(self.init_jobs)

        # --- 打包输出 ---
        obs, rwd, term, trunc, info = self.pack_output(
            [j_observations, j_infos],
            [t_observations, t_infos],
            [a_observations, a_infos],
        )

        return obs, info

    def render(self):
        """渲染环境"""
        self.pogema_env.render()

    # ---------- 获取器方法 ----------
    def get_jobs(self) -> List:
        """获取作业列表"""
        return self.pogema_env.jobs

    def job_all_done(self):
        return self.pogema_env.job_all_done()

    def get_machines(self) -> List:
        """获取机器列表"""
        return self.pogema_env.machines

    def get_agents(self) -> List:
        """获取AGV列表"""
        return self.agents

    def get_agent_positions(self) -> List[Tuple[int, int]]:
        """获取智能体位置"""
        return self.pogema_env.grid.get_agents_xy()

    def get_agent_targets(self) -> List[Tuple[int, int]]:
        """获取智能体目标"""
        return self.pogema_env.grid.finishes_xy

    def unpack_input(self, actions):
        """将输入的 actions 拆分为机器与智能体两部分"""
        # 假设 self.input_actions 是外部传入的总动作字典
        job_actions = actions.get("job_actions", {})
        task_actions = actions.get("assign_actions", {})
        agent_actions = actions.get("agent_actions", {})
        return (
            job_actions,
            task_actions,
            agent_actions,
        )

    def pack_output(self, job_info, task_info, agent_info):
        """动态合并 job 和 agent 输出"""

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

        j_obs, j_reward, j_term, j_trunc, j_info = unpack(job_info)
        t_obs, t_reward, t_term, t_trunc, t_info = unpack(task_info)
        a_obs, a_reward, a_term, a_trunc, a_info = unpack(agent_info)

        # 合并为标准输出结构
        observations = {
            "job_observation": j_obs,
            "task_observation": t_obs,
            "agent_observation": a_obs,
        }
        rewards = {
            "job_reward": j_reward,
            "task_reward": t_reward,
            "agent_reward": a_reward,
        }
        terminations = {
            "job_done": j_term,
            "task_done": t_term,
            "agent_done": a_term,
        }
        truncations = {
            "job_truncated": j_trunc,
            "task_truncated": t_trunc,
            "agent_truncated": a_trunc,
        }
        infos = {
            "job_info": j_info,
            "task_info": t_info,
            "agent_info": a_info,
        }

        return observations, rewards, terminations, truncations, infos

