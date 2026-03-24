import asyncio
from enum import Enum
from os import makedirs
from typing import Dict, Any, List, Optional, Protocol, runtime_checkable
import json

from joint_sim.component.Coordinator.coordinator import Coordinator
from joint_sim.io.use_io import create_env_from_config
from joint_sim.utils.pic_drawer import (
    draw_svg_with_machines_and_targets,
)
from enum import Enum
from collections import deque, Counter


class ExecutionStatus(str, Enum):
    """Factory execution status"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


ALGORITHM_PRESETS = [
    {
        "label": "贪心调度 + A*路由 + 最近分配",
        "value": "greedy+astar+nearest",
        "description": "贪心调度 + A*路由 + 最近分配",
    },
    # {
    #     "label": "最优调度 + A*路由 + 负载均衡",
    #     "value": "best+astar+load_balance",
    #     "description": "最优调度 + A*路由 + 负载均衡",
    # },
    # {
    #     "label": "贪心调度 + GPT路由 + 随机分配",
    #     "value": "greedy+mapf_gpt+random",
    #     "description": "贪心调度 + GPT路由 + 随机分配",
    # },
]


class GridFactoryProxy:
    """
    GridFactoryEnv 的 Proxy 实现
    """

    def __init__(self):
        self.inner_properties: Dict[str, Any] = {
            "algorithm": ALGORITHM_PRESETS.copy(),
        }
        self.status: ExecutionStatus = ExecutionStatus.IDLE
        self.current_step: int = 0
        self._total_steps: int = 0
        self._max_steps: int = 1000

        self._config: dict | None = None
        self._algorithm: str = "default"

        self.env = None
        self.coordinator = None
        self.initialized = False
        self.same_frame_count = 0
        self.latest_frames = deque(maxlen=10)
        # Data Streaming - 使用 asyncio.Queue
        self._state_queue: asyncio.Queue = asyncio.Queue()
        self._metrics_queue: asyncio.Queue = asyncio.Queue()
        self._control_queue: asyncio.Queue = asyncio.Queue()

    # ====================================
    # 配置方法
    # ====================================

    def set_config(self, config: dict) -> None:
        print(f"[GridFactoryProxy] 设置 config: {config}")
        self._config = config

    def set_algorithm(self, algorithm: str) -> None:
        self._algorithm = algorithm
        # print(f"Algorithm set to: {self._algorithm}")

    def get_algorithm(self) -> str:
        return self._algorithm

    def get_initialized(self) -> bool:
        return self.initialized

    # ====================================
    # 生命周期方法
    # ====================================

    async def initialize(self) -> None:
        self.initialized = True
        if self._config is None:
            raise RuntimeError("FactoryProxy 未设置 config")

        self.env = create_env_from_config(self._config, random_target=False)
        print(
            f"[GridFactoryProxy] 环境初始化成功，算法预设: {self.inner_properties['algorithm']}"
        )
        # 创建协调器
        job_algo, route_algo, assign_algo = self._algorithm.split("+")
        self.coordinator = Coordinator(
            job_solver=job_algo,
            route_solver=route_algo,  # RouteSolverFactory.create(route_algo),
            assigner=assign_algo,  # AssignerFactory.create(assign_algo)
        )
        # 之前 reset的时候把自定义的设定全清了，现在使用预定配置
        obs, info = self.env.reset()

        self.inner_properties["obs"] = obs
        self.inner_properties["info"] = info

        self.status = ExecutionStatus.IDLE
        self.current_step = 0

    async def cleanup(self) -> None:
        self.env = None
        self.coordinator = None
        self.status = ExecutionStatus.IDLE

    async def start(self) -> None:
        if self.env is None:
            raise RuntimeError("Env 未初始化")

        self.status = ExecutionStatus.RUNNING

        asyncio.create_task(self._run_loop())

    async def pause(self) -> None:
        if self.status == ExecutionStatus.RUNNING:
            self.status = ExecutionStatus.PAUSED

    async def reset(self) -> None:
        obs, info = self.env.reset()

        self.inner_properties["obs"] = obs
        self.inner_properties["info"] = info

        self.current_step = 0
        self.status = ExecutionStatus.IDLE

    async def stop(self) -> None:
        self.status = ExecutionStatus.STOPPED

    # ====================================
    # 主循环
    # ====================================
    def _build_frame(self) -> dict:
        pogema = self.env.pogema_env
        agv_list = pogema.get_agv_info()

        return {
            "timestamp": f"T+{self.current_step}s",
            "grid_state": {
                "positions_xy": [list(agv.pos) for agv in agv_list],
                "is_active": [agv.current_task is not None for agv in agv_list],
            },
            "machines": [
                {"id": m.id, "location": list(m.location), "current_op": m.current_op}
                for m in pogema.machines
            ],
            "active_transfers": [
                {
                    "task_id": t.task_id,
                    "job_id": t.job_id,
                    "op_id": t.op_id,
                    "source": list(t.source),
                    "destination": list(t.destination) if t.destination else None,
                }
                for t in pogema.active_transfers
            ],
        }

    async def _run_loop(self):

        while self.status == ExecutionStatus.RUNNING:

            obs = self.inner_properties["obs"]
            # print(f"[GridFactoryProxy] obs:{obs}")

            actions = self.coordinator.decide(obs)

            obs, rewards, terminations, truncations, infos = self.env.step(actions)

            res = draw_svg_with_machines_and_targets(
                self.env.pogema_env, self.env.env_timeline
            )
            makedirs("temp", exist_ok=True)
            with open(f"temp/{self.env.env_timeline}.svg", "w") as f:
                f.write(res)

            self.inner_properties["obs"] = obs

            self.current_step += 1

            if self.current_step > self._max_steps:
                self.status = ExecutionStatus.STOPPED

            frame = self._build_frame()
            # print(f"[GridFactoryProxy] Step {self.current_step}: Frame built {frame}")
            # 只检测 AGV 位置是否停滞
            positions_hash = hash(
                json.dumps(frame["grid_state"]["positions_xy"], sort_keys=True)
            )

            self.latest_frames.append(positions_hash)
            # 检查 AGV 位置，如果最近10帧中相同位置出现>=3次，认为停滞
            counter = Counter(self.latest_frames)
            if counter[positions_hash] >= 3:
                print(
                    f"[GridFactoryProxy] AGV 位置停滞检测触发，位置hash={positions_hash}"
                )
                self.status = ExecutionStatus.STOPPED

            await self._state_queue.put(
                ("state", {"status": self.status.name, "frame": frame})
            )
            # metrics
            await self._metrics_queue.put(
                ("metrics", {"status": self.status.name, "reward": rewards})
            )

            await asyncio.sleep(0.5)

    # ====================================
    # 事件接口
    # ====================================

    async def get_state_events(self) -> list:
        events = []
        while not self._state_queue.empty():
            events.append(await self._state_queue.get())
        # print(f"[GridFactoryProxy] 状态事件: {len(events)}")
        return events

    async def get_metrics_events(self) -> list:
        events = []
        while not self._metrics_queue.empty():
            events.append(await self._metrics_queue.get())
        return events

    async def get_control_events(self) -> list:
        events = self._control_queue
        self._control_queue = []
        return events

    # ====================================
    # Snapshot接口
    # ====================================

    async def get_state_snapshot(self) -> dict:
        return {
            "step": self.current_step,
            "status": self.status.name,
            "obs": self.inner_properties.get("obs"),
        }

    async def get_metrics_snapshot(self) -> dict:
        return {"step": self.current_step}

    async def get_control_status(self) -> dict:
        return {"status": self.status.name, "algorithm": self._algorithm}

    # ====================================
    # 状态判断
    # ====================================

    def is_running(self) -> bool:
        return self.status == ExecutionStatus.RUNNING

    def is_paused(self) -> bool:
        return self.status == ExecutionStatus.PAUSED

    def is_idle(self) -> bool:
        return self.status == ExecutionStatus.IDLE
