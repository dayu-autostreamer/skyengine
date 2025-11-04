"""
@Project ：SkyEngine
@File    ：grid_factory_env.py
@IDE     ：PyCharm
@Author  ：Skyrim
@Date    ：2025/1/15 10:00
"""

from typing import List, Tuple, Dict, Any, Optional
import yaml
from pathlib import Path

from pettingzoo import ParallelEnv
from pogema.grid import Grid
from pogema import pogema_v0, GridConfig, AnimationMonitor
from pogema_toolbox.registry import ToolboxRegistry
from pogema_toolbox.create_env import MultiMapWrapper
from pogema.envs import PogemaLifeLong, GridConfig

import config
from sky_executor.grid_factory.factory.Agent.BaseAgent import GridBaseAgent

from sky_executor.utils.registry import register_component
from sky_executor.grid_factory.factory.grid_factory_env.Utils.structure import (
    MachineConfig,
    JobConfig,
)
from sky_executor.grid_factory.factory.grid_factory_env.Utils.machine import (
    generate_machines,
    revert_to_pogema,
)
from sky_executor.grid_factory.factory.grid_factory_env.Utils.job import generate_jobs
from sky_logs.logger import LOGGER

# 禁用 ToolboxRegistry 日志输出
ToolboxRegistry.setup_logger(level="CRITICAL", sink=None)


@register_component("factory")
class GridFactoryEnv(PogemaLifeLong):
    """
    基于Pogema的网格工厂环境

    功能特性:
    1. 使用Pogema作为底层网格环境
    2. 支持多智能体路径规划
    3. 集成事件系统和回调机制
    4. 支持工厂任务调度
    """

    metadata = {"render_modes": ["human"], "name": "grid_factory_env"}

    def __init__(
        self,
        grid_config: Optional[GridConfig] = None,
        machine_config: Optional[MachineConfig] = None,
        job_config: Optional[JobConfig] = None,
        agent: Optional[GridBaseAgent] = None,
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
        # self.pogema_env = None
        self.grid_config = grid_config or self._create_default_grid_config()

        # 机器组件 也就是路由的起始点和终止点
        self.machines = []
        self.machine_config = machine_config or self._create_default_machine_config()
        self.activated_machines = []

        # 任务组件
        self.jobs = []
        self.pending_transfers = []  # Job层给的任务
        self.active_transfers = []  # 当前执行中的运输任务
        self.job_config = job_config or self._create_default_job_config()

        # 智能体组件
        self.agents = []

        # 索引结构
        self.hash_index = {
            "agents": {},
            "machines": {},
            "jobs": {},
        }

        self.register_maps()

    def register_maps(self):
        ToolboxRegistry._maps = {}
        for maps_file in Path(config.MAPF_GPT_DIR).rglob("maps.yaml"):
            with open(maps_file, "r") as f:
                maps = yaml.safe_load(f)
            ToolboxRegistry.register_maps(maps)

    @property
    def machine_possible_positions(self):
        return self.grid_config.possible_targets_xy

    @property
    def current_targets(self):
        return self.grid.finishes_xy

    def machine_reset(self, seed=42):
        # 获得可能的位置，修改config
        # todo machine seed need to add.
        grid: Grid = Grid(grid_config=self.grid_config)
        grid.get_obstacles()

        self.machines = revert_to_pogema(
            generate_machines(grid.get_obstacles(), self.machine_config)
        )
        """获得机器的位置"""
        self.grid_config.possible_targets_xy = [m.location for m in self.machines]

        LOGGER.info(
            f"[GridFactoryEnv] 创建了 {self.machine_config.num_machines} 个机器"
        )
        observations = {}
        infos = {}
        return observations, infos

    def get_maps(self):
        res = ToolboxRegistry.get_maps()
        map_name = []
        for _map in res:
            map_name.append(_map)
        return map_name

    def get_jobs(self):
        return self.jobs

    def _create_default_grid_config(self) -> GridConfig:
        """创建默认的网格配置"""
        return GridConfig(
            num_agents=4,
            size=20,
            density=0.3,
            seed=42,
            max_episode_steps=256,
            obs_radius=5,
            on_target="restart",
        )

    def _create_default_machine_config(self):
        """创建默认的机器配置"""
        return MachineConfig(
            num_machines=4,
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

    def create_hash_index(self):
        """创建高效获取组件的索引结构"""
        for agent in self.agents:
            self.hash_index["agents"][agent.id] = agent
        for job in self.jobs:
            self.hash_index["jobs"][job.id] = job
        for machine in self.machines:
            self.hash_index["machines"][machine.id] = machine

    def set_env_timeline(self, env_timeline: int):
        """设置环境时间线"""
        self.env_timeline = env_timeline

    def get_env_timeline(self) -> int:
        """获取环境时间线"""
        return self.env_timeline

    def job_step(self, actions=None):
        """
        Job 层获取routing tasks,更新环境本身的相关信息,后续交给assigner层指派。
        """
        observations, rewards, terminations, infos = {}, {}, {}, {}

        # 当前仿真时刻
        t = self.env_timeline

        # === 1️⃣ 接收 JobSolver 的决策 ===
        if actions is not None:
            # 新的转运请求加入 pending_transfers
            new_transfers = actions.get("transfer_requests", [])
            self.pending_transfers.extend(new_transfers)

        # === 2️⃣ 推进加工状态 ===
        finished_ops = []
        for m in self.machines:
            active_op = getattr(m, "active_op", None)
            if active_op is not None and t >= active_op["end"]:
                # 工序完成
                finished_ops.append(active_op)
                m.active_op = None

        # === 5️⃣ 奖励与完成判定 ===
        # 简单策略：奖励 = 已完成工序数 - 待转运数
        rewards = {"job_reward": len(finished_ops) - len(self.pending_transfers)}

        done = len(self.pending_transfers) == 0 and all(
            getattr(m, "active_op", None) is None for m in self.machines
        )
        terminations = {"job_done": done}
        truncations = {"job_truncation": False}
        # === 6️⃣ 汇总信息 ===
        infos = {
            "finished_ops": finished_ops,
        }

        # === 7️⃣ 输出观测 ===
        observations = {
            "machines": self.machines,
            "pending_transfers": self.pending_transfers,
            "active_transfers": self.active_transfers,
            "finished_ops": finished_ops,
        }

        return observations, rewards, terminations, truncations, infos

    def job_reset(self, seed=42):
        """
        初始化 Job 层任务系统：
        1. 创建机器和 Job
        2. 调用调度器生成加工计划
        3. 存储初始调度结果
        """
        LOGGER.info("[GridFactoryEnv] 初始化 Job 层任务...")

        # 2️⃣ 创建 Jobs
        self.job_config = self._create_default_job_config()
        self.jobs = generate_jobs(self.job_config)

        # # 3️⃣ 调用离线调度器生成初步排程
        from SkyEngine.sky_executor.grid_factory.factory.grid_factory_env.Component.JobSolver.utils.op_priority_greedy import (
            priority_greedy,
        )

        res = priority_greedy(
            self.jobs,
            self.machines,
            priority_rule="SPT",
            transfer_time_estimator=lambda a, b: 0.0,
        )

        # 4️⃣ 存储调度结果
        self.job_schedule = res.machine_schedule
        self.pending_transfers = res.transfer_requests  # 下一步交给 AGV
        self.job_stats = res.stats

        # 5️⃣ 构建初始观察信息
        observations = {
            "job_schedule": self.job_schedule,
            "pending_transfers": self.pending_transfers,
        }

        infos = {"makespan_est": res.stats["makespan"]}

        # LOGGER.info(f"[GridFactoryEnv] 初始化调度完成，共生成 {len(self.jobs)} 个Job")
        return observations, infos

    def activate_task(self):
        """
        上层只负责：pending / active 任务列表、激活任务、接收完成任务回调
        """
        ready_tasks = [
            t for t in self.pending_transfers if t["ready_time"] <= self.env_timeline
        ]
        for task in ready_tasks:
            self.assigner_env.add_task(task)  # 上层只把任务提交给 assign 环境
            self.pending_transfers.remove(task)

    def update_transfer_status(self, assigner_info):
        """同步 Pogema-Assign 环境完成任务状态"""
        finished_tasks = assigner_info.get("finished_tasks", [])
        for task in finished_tasks:
            if task in self.active_transfers:
                LOGGER.info(f"[GridFactoryEnv] 任务完成：Job {task['job_id']}")
                self.active_transfers.remove(task)

    def step(self, actions=None):
        LOGGER.info(f"[GridFactoryEnv] 当前环境时间: {self.env_timeline}")
        self.env_timeline += 1

        self.activate_task()

        agent_actions, job_actions = self.unpack_input(actions)

        j_obs, j_reward, j_terminated, j_truncated, j_info = self.job_step(job_actions)

        a_obs, a_reward, a_terminated, a_truncated, a_info = self.pogema_env.step(
            agent_actions
        )

        self.update_transfer_status(a_info)

        agent_info = [a_obs, a_reward, a_terminated, a_truncated, a_info]
        job_info = [j_obs, j_reward, j_terminated, j_truncated, j_info]
        LOGGER.info(f"[GridFactoryEnv] 结束当前循环步")

        # 合并输出
        observations, rewards, terminations, truncated, info = self.pack_output(
            job_info, agent_info
        )

        # todo 当前的obs尚未和job job版本对齐 请将job相关的观察结果实现
        return observations, rewards, terminations, truncated, info

    def reset(self, seed=None):
        LOGGER.info("[GridFactoryEnv] 重置环境")

        self.set_env_timeline(0)

        # --- 重置机器相关，使用可能位置 ---
        m_observations, m_infos = self.machine_reset(seed=seed)

        # --- 重置任务相关，使用任务列表 ---
        j_observations, j_infos = self.job_reset(seed=seed)

        # --- 重置 Pogema 相关 ---
        a_observations, a_infos = self.pogema_env.reset(seed=seed)

        # --- 打包输出 ---
        obs, rwd, term, trunc, info = self.pack_output(
            [m_observations, m_infos], [a_observations, a_infos]
        )

        self.pending_transfers.clear()
        self.active_transfers.clear()
        # reset之后才能看这里
        # print(f"请看这里：{self.pogema_env.grid.get_obstacles().astype(int).tolist()}")

        return obs, info

    def _distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

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

    # todo 这些agent的信息可以通过env获取 可以修改一下
    def get_agents(self) -> List:
        """获取AGV列表"""
        return self.agents

    # def get_agents_info(self) -> List[Dict[str, Any]]:
    #     """获取智能体信息"""
    #     return self.agents_info

    def get_agent_positions(self) -> List[Tuple[int, int]]:
        """获取智能体位置"""
        return self.pogema_env.grid.get_agents_xy()

    # def get_agent_targets(self) -> List[Tuple[int, int]]:
    #     """获取智能体目标"""
    #     return self.agent_targets

    def get_pogema_env(self):
        """获取Pogema环境实例"""
        return self.pogema_env

    def get_grid_config(self) -> GridConfig:
        """获取网格配置"""
        return self.grid_config

    def update_grid_config(self, new_config: GridConfig):
        """更新网格配置"""
        self.grid_config = new_config
        self._initialize_pogema_env()

    def unpack_input(self, actions):
        """将输入的 actions 拆分为机器与智能体两部分"""
        # 假设 self.input_actions 是外部传入的总动作字典
        job_actions = actions.get("job_actions", {})
        agent_actions = actions.get("agent_actions", {})
        return agent_actions, job_actions

    def pack_output(self, job_info, agent_info):
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

        # 动态解包
        m_obs, m_reward, m_term, m_trunc, m_info = unpack(job_info)
        a_obs, a_reward, a_term, a_trunc, a_info = unpack(agent_info)

        # 合并为标准输出结构
        observations = {"job_observation": m_obs, "agent_observation": a_obs}
        rewards = {"job_reward": m_reward, "agent_reward": a_reward}
        terminations = {"job_done": m_term, "agent_done": a_term}
        truncations = {"job_truncated": m_trunc, "agent_truncated": a_trunc}
        infos = {"job_info": m_info, "agent_info": a_info}

        return observations, rewards, terminations, truncations, infos
