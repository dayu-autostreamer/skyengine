"""
DockerProxy — 通过 docker compose 按需启停 SkyEngine 在线仿真服务

调用 docker compose CLI 管理容器生命周期，无需 Docker SDK。
所有容器/网络/卷的定义都在 docker-compose-online.yaml 中。

两阶段启动:
  1. initialize() — docker compose up engine     → 等待就绪
  2. start()      — docker compose up mapf fjsp  → POST /sim/create → POST /sim/play
  3. stop()       — docker compose down
"""

import os
import re
import asyncio
import json
import logging
import datetime
import subprocess
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


# ==================== 算法 → 镜像名映射 ====================

ALGORITHM_MAP = {
    "fjsp": {
        "pso":  "skyengine-fjsp-pso:latest",
        "de":   "skyengine-fjsp-de:latest",
        "drl":  "skyengine-fjsp-drl:latest",
        "best": "skyengine-fjsp-best:latest",
    },
    "mapf": {
        "astar":    "skyengine-mapf-astar:latest",
        "mapf_gpt": "skyengine-mapf-gpt:latest",
    },
}


# ==================== 批处理：日志解析 + 默认 ENV（参考 experiment/exp0503/run_experiments.py）====================

# 批处理默认 ENV（与 exp0503 BASE_ENV 对齐）
BATCH_BASE_ENV = {
    "FJSP_INSTANCE": "J10P5M6.json",
    # 格式：<实例名>@<文件名>。medium_maps.yaml 是 dataset/mapf/ 下实际存在的多实例文件，
    # 内含 medium-mazes-seed-0000 等多个 seed。原 10-medium-mazes-part1.yaml 已不存在。
    "MAPF_INSTANCE": "medium-mazes-seed-0000@medium_maps.yaml",
    "NUM_MACHINES": "5",
    "NUM_AGV": "8",
    "NUM_SIZE": "16",
    "NUM_DENSE": "0.1",
    "NUM_RADIUS": "5",
    "NUM_STEPS": "500",
    "OBS_TYPE": "default",
    "HTTP_TIMEOUT": "6",
    "MAPF_SERVICE_URL": "http://mapf:8001",
    "FJSP_SERVICE_URL": "http://fjsp:8002",
    "SOLVER_ASSIGN": "random",
}

# 从 run.py stdout 抓取的指标字段（正则匹配 metric_key: number）
METRIC_KEYS = [
    # FJSP
    "machine_utilization",
    "machine_non_processing_time_mean",
    "machine_load_variance",
    "operation_queue_waiting_time_mean",
    # MAPF
    "swap_conflict_count",
    "tasked_stationary_count",
    "agv_loaded_utilization",
    "agv_busy_utilization",
    "agv_travel_time_total",
    "agv_waiting_time_total",
    # Coupling
    "transport_delay_ratio",
    "transport_blocking_delay_mean",
    "machine_waiting_for_inbound_transfer_ratio",
    # Episode
    "completed_makespan",
    "full_makespan",
    "success_rate",
    "job_completion_rate",
]


def parse_metrics(log: str) -> dict:
    """从 run.py 输出抓取指标。复制自 experiment/exp0503/run_experiments.py:parse_metrics。
    匹配 `metric_key: <number>` 形式；terminated_reason 走关键词匹配。"""
    metrics = {}
    for key in METRIC_KEYS:
        m = re.search(
            rf"{re.escape(key)}:\s*(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
            log,
        )
        metrics[key] = float(m.group(1)) if m else ""

    m = re.search(r"terminated_reason:\s*([A-Za-z0-9_\-]+)", log)
    if m:
        metrics["terminated_reason"] = m.group(1)
    elif re.search(r"Episode ended", log):
        metrics["terminated_reason"] = "done"
    elif re.search(r"\bmax_steps\b", log):
        metrics["terminated_reason"] = "max_steps"
    else:
        metrics["terminated_reason"] = "unknown"

    return metrics


class DockerProxy:
    """通过 docker compose 联动 SkyEngine 在线服务的工厂代理"""

    def __init__(self):
        logger.info("[DockerProxy] __init__ 被调用")
        # ---- 普通实例属性 (与 GridFactoryProxy 风格一致) ----
        self.inner_properties: dict = {
            "algorithm": [
                {"label": "PSO调度 + A*路由 + 最近分配", "value": "pso+astar+nearest"},
                {"label": "DE调度 + A*路由 + 最近分配", "value": "de+astar+nearest"},
                {"label": "DRL调度 + A*路由 + 最近分配", "value": "drl+astar+nearest"},
                {"label": "PSO调度 + MAPF-GPT路由 + 随机分配", "value": "pso+mapf_gpt+random"},
            ],
        }
        self.status: ExecutionStatus = ExecutionStatus.IDLE
        self.current_step: int = 0
        self._total_steps: int = 0

        # ---- compose 配置 ----
        self._project_dir: str = os.getenv(
            "SKYENGINE_PROJECT_DIR",
            "",
        )
        if not self._project_dir and os.name == "nt":
            self._project_dir = self._default_windows_project_dir()

        self._compose_file: str = self._resolve_windows_host_path(
            os.getenv(
                "SKYENGINE_COMPOSE_PATH",
                "/opt/skyengine/docker-compose-online.yaml",
            ),
            fallback_filename="docker-compose-online.yaml",
        )
        self._batch_compose_file: str = self._resolve_windows_host_path(
            os.getenv(
                "SKYENGINE_BATCH_COMPOSE_PATH",
                "/opt/skyengine/docker-compose-batch.yaml",
            ),
            fallback_filename="docker-compose.yaml",
        )
        self._project_name: str = "skyengine-online"
        self._engine_url: str = os.getenv(
            "ENGINE_URL",
            f"http://localhost:{os.getenv('ENGINE_PORT', '8080')}",
        )
        if os.name == "nt" and self._engine_url == "http://engine:8080":
            self._engine_url = "http://localhost:8080"

        self._config: dict = {}
        self._algorithm: str = "pso+astar+nearest"
        self._algorithm_parts: dict = {}
        self.initialized: bool = False

        # SSE 透传
        self._streaming = False

        # ---- 批处理模式（参考 experiment/exp0503/run_experiments.py）----
        # 用实验 compose（docker-compose.yaml）跑 run.py，串行多 episode
        # 与在线模式互斥（GPU + project name 不冲突，但同时跑会资源争用）
        # 宿主机上 dataset 目录路径（compose 把它以 :ro 挂到容器 /dataset）。
        # 上传的实例文件写到此处，容器内即可见。默认指向 finalpro/SkyEngine/dataset。
        self._batch_dataset_host_dir: str = os.getenv(
            "SKYENGINE_BATCH_DATASET_HOST_DIR",
            "/data1/home/wuhao/project/finalpro/SkyEngine/dataset",
        )
        self._batch_project_name: str = "skyengine-batch"
        self._batch_queue: asyncio.Queue | None = None
        self._batch_task: asyncio.Task | None = None
        self._batch_cancel_event: asyncio.Event = asyncio.Event()
        self._batch_status: dict = {
            "running": False,
            "idx": 0,
            "total": 0,
            "results": [],
        }

    @staticmethod
    def _default_windows_project_dir() -> str:
        """Windows 本地开发默认使用 skyengine-frontend 的兄弟目录 SkyEngine-dev。"""
        frontend_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        candidate = os.path.join(os.path.dirname(frontend_root), "SkyEngine-dev")
        return candidate if os.path.isdir(candidate) else ""

    def _resolve_windows_host_path(self, path: str, fallback_filename: str) -> str:
        """把容器内 /opt/skyengine 路径转换为 Windows 宿主机真实路径。"""
        if os.name != "nt" or not path:
            return path

        normalized = path.replace("\\", "/")
        candidates: list[str] = []
        if normalized.startswith("/opt/skyengine/") and self._project_dir:
            tail = normalized.removeprefix("/opt/skyengine/")
            if tail == "docker-compose-batch.yaml":
                candidates.append(os.path.join(self._project_dir, "docker-compose.yaml"))
            candidates.append(os.path.join(self._project_dir, tail))

        if self._project_dir:
            candidates.append(os.path.join(self._project_dir, fallback_filename))

        for candidate in candidates:
            if os.path.exists(candidate):
                return os.path.normpath(candidate)

        return os.path.normpath(candidates[0]) if candidates else path

    # ==================== docker compose 辅助 ====================

    async def _compose(self, *args: str, env: dict | None = None) -> str:
        """执行 docker compose 命令并返回输出"""
        cmd = [
            "docker", "compose",
            "-p", self._project_name,
        ]
        if self._project_dir:
            cmd += ["--project-directory", self._project_dir]
        cmd += ["-f", self._compose_file, *args]
        logger.debug(f"[DockerProxy] $ {' '.join(cmd)}")

        merged_env = {**os.environ}
        if env:
            merged_env.update(env)

        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=merged_env,
        )

        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            logger.error(f"[DockerProxy] compose 失败 (rc={result.returncode}): {err}")
            raise RuntimeError(f"docker compose failed: {err}")

        return result.stdout.strip()

    # ==================== 配置方法 ====================

    def set_config(self, config: dict):
        self._config = config

    def set_algorithm(self, algorithm: str) -> None:
        logger.info(f"[DockerProxy] set_algorithm: {algorithm}")
        if not algorithm:
            return
        self._algorithm = algorithm
        parts = algorithm.split("+")
        if len(parts) == 3:
            self._algorithm_parts = {
                "fjsp": parts[0],
                "mapf": parts[1],
                "assigner": parts[2],
            }
        self.inner_properties["current_algorithm"] = algorithm

    def get_algorithm(self) -> str:
        return self._algorithm

    def get_initialized(self) -> bool:
        logger.debug(f"[DockerProxy] get_initialized: {self.initialized}")
        return self.initialized

    # ==================== 生命周期方法 ====================

    async def initialize(self) -> None:
        """Phase 1: docker compose up engine + 等待就绪"""
        logger.info("[DockerProxy] Phase 1: 启动 engine ...")

        # 清理可能残留的旧容器
        try:
            await self._compose("down", "--remove-orphans")
        except Exception:
            pass

        # 启动 engine
        await self._compose("up", "-d", "engine")

        # 等待 engine 健康检查
        await self._wait_for_health()

        self.initialized = True
        self.status = ExecutionStatus.IDLE
        logger.info(f"[DockerProxy] Phase 1 完成: engine 就绪 @ {self._engine_url}")

    async def cleanup(self) -> None:
        try:
            await self._compose("down", "--remove-orphans")
        except Exception as e:
            logger.error(f"[DockerProxy] cleanup 失败: {e}")
        self.initialized = False
        self._engine_url = None

    async def start(self) -> None:
        """Phase 2: docker compose up mapf fjsp + 发送仿真配置 + 启动仿真"""
        if not self.initialized:
            raise RuntimeError("请先调用 initialize()")
        if not self._algorithm_parts:
            raise RuntimeError("未设置算法配置")

        logger.info(f"[DockerProxy] Phase 2: 启动算法容器, 算法={self._algorithm}")

        # 1. 确定镜像，通过环境变量传给 docker compose
        fjsp_algo = self._algorithm_parts.get("fjsp", "pso")
        mapf_algo = self._algorithm_parts.get("mapf", "astar")
        mapf_image = ALGORITHM_MAP["mapf"].get(mapf_algo, "skyengine-mapf-gpt:latest")
        fjsp_image = ALGORITHM_MAP["fjsp"].get(fjsp_algo, "skyengine-fjsp-pso:latest")

        compose_env = {
            "MAPF_IMAGE": mapf_image,
            "FJSP_IMAGE": fjsp_image,
        }
        logger.info(f"[DockerProxy] mapf={mapf_image}, fjsp={fjsp_image}")

        # 2. 启动算法容器。每轮仿真强制重建算法服务，避免上轮 MAPF/FJSP 内部缓存残留。
        await self._compose("up", "-d", "--force-recreate", "mapf", "fjsp", env=compose_env)

        # 2.5 等待 fjsp/mapf 的 Flask 就绪（避免 play 时 Connection refused）
        await self._wait_for_service("fjsp", 8002)
        await self._wait_for_service("mapf", 8001)

        # 3. 发送仿真配置到 engine（前端 JSON 原样转发 + 算法参数）
        sim_config = {
            "config": self._config,
            "fjsp_algorithm": fjsp_algo,
            "mapf_algorithm": mapf_algo,
            "solver_assign": self._algorithm_parts.get("assigner", "nearest"),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{self._engine_url}/sim/create", json=sim_config)
            await client.post(f"{self._engine_url}/sim/play")

        # 4. 标记流式传输就绪
        self._streaming = True
        self.status = ExecutionStatus.RUNNING
        logger.info("[DockerProxy] Phase 2 完成: 仿真已启动")

    async def pause(self) -> None:
        if self._engine_url:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{self._engine_url}/sim/pause")
        self.status = ExecutionStatus.PAUSED

    async def insert_jobs(self, body: dict) -> dict:
        """转发到 engine POST /sim/insert_jobs（v2 FJSP 格式）。
        透传 engine 响应：{status: ok|partial|error, inserted, rejected?, message?}。
        timeout=30s 给足批量插单 + engine 校验时间。"""
        if not self._engine_url:
            return {"status": "error", "message": "engine 未就绪"}
        url = f"{self._engine_url}/sim/insert_jobs"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=body)
                return resp.json()
        except Exception as e:
            logger.error(f"[DockerProxy] insert_jobs 失败: {e}")
            return {"status": "error", "message": str(e)}

    async def inject_exception(self, body: dict) -> dict:
        """转发运行时 Exception 注入请求到 engine。"""
        if not self._engine_url:
            return {"status": "error", "message": "engine 未就绪"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self._engine_url}/sim/exception/inject", json=body)
                if resp.status_code == 404:
                    await self._refresh_engine_after_missing_exception_api()
                    resp = await client.post(f"{self._engine_url}/sim/exception/inject", json=body)
                return resp.json()
        except Exception as e:
            logger.error(f"[DockerProxy] inject_exception 失败: {e}")
            return {"status": "error", "message": str(e)}

    async def clear_exceptions(self, body: dict) -> dict:
        """转发运行时 Exception 清理请求到 engine。"""
        if not self._engine_url:
            return {"status": "error", "message": "engine 未就绪"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self._engine_url}/sim/exception/clear", json=body or {})
                if resp.status_code == 404:
                    await self._refresh_engine_after_missing_exception_api()
                    resp = await client.post(f"{self._engine_url}/sim/exception/clear", json=body or {})
                return resp.json()
        except Exception as e:
            logger.error(f"[DockerProxy] clear_exceptions 失败: {e}")
            return {"status": "error", "message": str(e)}

    async def _refresh_engine_after_missing_exception_api(self) -> None:
        """旧 engine 容器不含运行时 Exception API 时，重建 engine 后再重试。"""
        logger.warning("[DockerProxy] engine 缺少 Exception API，尝试重建 engine 容器")
        self._streaming = False
        await self._compose("up", "-d", "--force-recreate", "engine")
        await self._wait_for_health(timeout=60.0)
        self.initialized = True
        self.status = ExecutionStatus.IDLE

    async def reset(self) -> None:
        if self._engine_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(f"{self._engine_url}/sim/reset")
        self.status = ExecutionStatus.IDLE
        self.current_step = 0

    async def stop(self) -> None:
        self._streaming = False
        if self._engine_url:
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    await client.post(f"{self._engine_url}/sim/stop")
                except Exception:
                    pass
        try:
            await self._compose("down", "--remove-orphans")
        except Exception:
            pass
        self.status = ExecutionStatus.STOPPED
        self.initialized = False

    # ==================== SSE 流接口 ====================

    async def get_state_events(self) -> list:
        return [("state", {"status": self.status.value, "step": self.current_step})]

    async def get_metrics_events(self) -> list:
        return [("metrics", {"status": self.status.value})]

    async def get_control_events(self) -> list:
        return [("control", {"status": self.status.value, "algorithm": self._algorithm})]

    async def get_state_snapshot(self) -> dict:
        return {"status": self.status.value, "step": self.current_step}

    async def get_metrics_snapshot(self) -> dict:
        return {"status": self.status.value}

    async def get_control_status(self) -> dict:
        return {"status": self.status.value, "algorithm": self._algorithm}

    # ==================== 健康检查 ====================

    async def _wait_for_health(self, timeout: float = 60.0):
        logger.info(f"[DockerProxy] 等待 {self._engine_url}/health ...")
        async with httpx.AsyncClient() as client:
            for i in range(int(timeout)):
                try:
                    resp = await client.get(f"{self._engine_url}/health", timeout=2.0)
                    if resp.status_code == 200:
                        logger.info(f"[DockerProxy] engine 就绪 (耗时 {i}s)")
                        return
                except Exception:
                    pass
                await asyncio.sleep(1.0)
        raise TimeoutError(f"Engine not ready within {timeout}s")

    async def _wait_for_service(self, host: str, port: int, timeout: float = 30.0):
        """等待算法容器（fjsp/mapf）的 Flask 服务 listen 就绪。

        docker compose up -d 是异步的——容器启动了但 Flask 可能还在初始化。
        如果不等待就 /sim/play，engine 的 _run_loop 第一步 coordinator.decide()
        会撞上 Connection refused，仿真线程直接崩溃。
        """
        logger.info(f"[DockerProxy] 等待 {host}:{port} 就绪 ...")
        if os.name == "nt" and host in {"fjsp", "mapf"}:
            await self._wait_for_compose_service_from_engine(host, port, timeout)
            return

        async with httpx.AsyncClient() as client:
            for i in range(int(timeout)):
                try:
                    # 根路径返回 404 也算 ready（只要 TCP 连上了就说明 Flask 在 listen）
                    resp = await client.get(f"http://{host}:{port}/", timeout=2.0)
                    logger.info(f"[DockerProxy] {host}:{port} 就绪 (耗时 {i}s, status={resp.status_code})")
                    return
                except Exception:
                    pass
                await asyncio.sleep(1.0)
        raise TimeoutError(f"Service {host}:{port} not ready within {timeout}s")

    async def _wait_for_compose_service_from_engine(self, host: str, port: int, timeout: float) -> None:
        """Windows 宿主机无法解析 Compose 服务名，借 engine 容器在内部网络探测。"""
        script = (
            "import sys, urllib.error, urllib.request\n"
            f"url='http://{host}:{port}/'\n"
            "try:\n"
            "    resp=urllib.request.urlopen(url, timeout=2)\n"
            "    print(resp.status)\n"
            "except urllib.error.HTTPError as e:\n"
            "    print(e.code)\n"
            "except Exception as e:\n"
            "    print(e, file=sys.stderr)\n"
            "    sys.exit(1)\n"
        )
        for i in range(int(timeout)):
            try:
                status = await self._compose("exec", "-T", "engine", "python", "-c", script)
                logger.info(f"[DockerProxy] {host}:{port} 就绪 (耗时 {i}s, status={status})")
                return
            except Exception:
                await asyncio.sleep(1.0)
        raise TimeoutError(f"Service {host}:{port} not ready within {timeout}s")

    # ==================== SSE 透传 ====================

    async def state_stream(self):
        """直接透传 sim_server 的 /stream/state SSE 事件，零队列缓冲"""
        if not self._engine_url or not self._streaming:
            return
        url = f"{self._engine_url}/stream/state"
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url) as resp:
                    async for line in resp.aiter_lines():
                        if not self._streaming:
                            break
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                frame = data.get("frame")
                                if frame and "timestamp" in frame:
                                    ts = frame["timestamp"]
                                    if ts.startswith("T+"):
                                        try:
                                            self.current_step = int(ts[2:].rstrip("s"))
                                        except ValueError:
                                            pass
                                yield ("state", data)
                                if data.get("status") == "stopped":
                                    self._streaming = False
                                    self.status = ExecutionStatus.STOPPED
                                    break
                            except (json.JSONDecodeError, KeyError):
                                pass
        except Exception as e:
            logger.error(f"[DockerProxy] state_stream 结束: {e}")
            if self._streaming:
                self.status = ExecutionStatus.ERROR

    async def metrics_stream(self):
        """直接透传 sim_server 的 /stream/metrics SSE 事件"""
        if not self._engine_url or not self._streaming:
            return
        url = f"{self._engine_url}/stream/metrics"
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url) as resp:
                    async for line in resp.aiter_lines():
                        if not self._streaming:
                            break
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                yield ("metrics", data)
                            except (json.JSONDecodeError, KeyError):
                                pass
        except Exception as e:
            logger.error(f"[DockerProxy] metrics_stream 结束: {e}")

    async def events_stream(self):
        """直接透传 sim_server 的 /stream/events SSE 事件"""
        if not self._engine_url or not self._streaming:
            return
        url = f"{self._engine_url}/stream/events"
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url) as resp:
                    async for line in resp.aiter_lines():
                        if not self._streaming:
                            break
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                yield ("event", data)
                            except (json.JSONDecodeError, KeyError):
                                pass
        except Exception as e:
            logger.error(f"[DockerProxy] events_stream 结束: {e}")

    # ==================== 状态判断 ====================

    def is_running(self) -> bool:
        return self.status == ExecutionStatus.RUNNING

    def is_paused(self) -> bool:
        return self.status == ExecutionStatus.PAUSED

    def is_idle(self) -> bool:
        return self.status == ExecutionStatus.IDLE

    # ==================== 批处理模式（参考 experiment/exp0503/run_experiments.py）====================
    #
    # 用实验 compose（docker-compose.yaml）跑 run.py，串行执行多组配置。
    # 与在线模式（start/pause/stop）完全解耦：用不同的 compose 文件 + project name。
    # 前端通过 SSE /batch/stream 收：
    #   batch_progress  → 当前 episode 进度 (idx/total)
    #   batch_log       → run.py stdout 实时输出
    #   batch_metric    → 单 episode 跑完后的解析指标
    #   batch_done      → 全部完成
    #   batch_error     → 异常
    # 不挂载卷、不落盘，所有信息从 docker compose stdout 抓。

    async def _batch_compose(self, *args: str, env: dict | None = None) -> str:
        """批处理专用 compose 命令（用 _batch_compose_file + _batch_project_name）。
        与 _compose 区分：在线模式用 online.yaml + skyengine-online；
        批处理用 docker-compose.yaml + skyengine-batch。"""
        cmd = ["docker", "compose", "-p", self._batch_project_name]
        if self._project_dir:
            cmd += ["--project-directory", self._project_dir]
        cmd += ["-f", self._batch_compose_file, *args]
        merged_env = {**os.environ}
        if env:
            merged_env.update(env)

        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=merged_env,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"batch compose failed: {err}")
        return result.stdout.strip()

    def get_batch_status(self) -> dict:
        """查询批处理状态。"""
        return dict(self._batch_status)

    def save_batch_instance(self, filename: str, content: bytes, kind: str) -> str:
        """把前端上传的实例文件写到宿主机 dataset/{kind}/ 下，返回纯文件名。

        compose 把 dataset 挂载到容器 /dataset:ro，写入后容器可见。
        kind: "fjsp" 或 "mapf"。fjsp 接受 .json；mapf 接受 .yaml/.yml。
        """
        kind = kind.lower()
        if kind not in ("fjsp", "mapf"):
            raise ValueError("kind 必须是 fjsp 或 mapf")
        # 仅保留文件名，禁止路径穿越
        bare = os.path.basename(filename)
        if not bare:
            raise ValueError("文件名非法")
        ext = os.path.splitext(bare)[1].lower()
        if kind == "fjsp" and ext != ".json":
            raise ValueError("FJSP 实例必须是 .json")
        if kind == "mapf" and ext not in (".yaml", ".yml"):
            raise ValueError("MAPF 实例必须是 .yaml/.yml")

        target_dir = os.path.join(self._batch_dataset_host_dir, kind)
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, bare)
        with open(target_path, "wb") as f:
            f.write(content)
        logger.info(
            f"[DockerProxy] 实例上传：{bare} ({len(content)}B) → {target_path}"
        )
        return bare

    async def start_batch(self, experiments: list[dict], base_env: dict | None = None) -> dict:
        """启动批处理 worker。立即返回，后台串行执行。
        experiments: 每项形如 {solver_job, solver_route, fjsp_image, mapf_image, mapf_obs_type, seed}
                     （参考 exp0503 FJSP_CONFIGS × MAPF_CONFIGS × seeds）
        base_env: 覆盖 BATCH_BASE_ENV 默认值（可选）
        """
        if self._batch_status["running"]:
            raise RuntimeError("批处理已在运行")
        if self.is_running():
            raise RuntimeError("在线仿真运行中，无法启动批处理")
        if not experiments:
            raise ValueError("experiments 不能为空")

        self._batch_status = {
            "running": True,
            "idx": 0,
            "total": len(experiments),
            "results": [],
            "cancelled": False,
            "started_at": datetime.datetime.now().isoformat(),
        }
        self._batch_cancel_event.clear()
        self._batch_queue = asyncio.Queue(maxsize=500)
        self._batch_task = asyncio.create_task(
            self._batch_worker(experiments, base_env or {})
        )
        logger.info(
            f"[DockerProxy] 批处理启动：{len(experiments)} 个 episode，"
            f"compose={self._batch_compose_file}, project={self._batch_project_name}"
        )
        return {"status": "started", "total": len(experiments)}

    async def cancel_batch(self) -> dict:
        """取消批处理：docker compose down + 停 worker。"""
        was_running = self._batch_status["running"]
        self._batch_cancel_event.set()

        # 立即 down 容器（中止正在跑的 episode）
        try:
            await self._batch_compose("down", "--remove-orphans")
        except Exception as e:
            logger.error(f"[DockerProxy] batch cancel down 失败: {e}")

        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
            try:
                await self._batch_task
            except (asyncio.CancelledError, Exception):
                pass

        self._batch_status["running"] = False
        self._batch_status["cancelled"] = True
        logger.info(f"[DockerProxy] 批处理已取消（之前 running={was_running}）")
        return {"status": "cancelled"}

    async def batch_stream(self):
        """SSE 生成器：从 _batch_queue 读事件 yield。
        事件类型：batch_progress / batch_log / batch_metric / batch_done / batch_error。
        收到 done/error 或 worker 结束时退出。"""
        if self._batch_queue is None:
            return
        while True:
            try:
                event_type, data = await asyncio.wait_for(
                    self._batch_queue.get(), timeout=1.0
                )
                yield (event_type, data)
                if event_type in ("batch_done", "batch_error"):
                    break
            except asyncio.TimeoutError:
                # worker 已结束但队列可能还有事件；都消费完就退出
                if (self._batch_task is None) or self._batch_task.done():
                    if self._batch_queue.empty():
                        break
                continue
            except asyncio.CancelledError:
                break

    async def _batch_emit(self, event_type: str, data: dict) -> None:
        """推一个事件到队列。满了丢最旧。"""
        if self._batch_queue is None:
            return
        try:
            self._batch_queue.put_nowait((event_type, data))
        except asyncio.QueueFull:
            try:
                self._batch_queue.get_nowait()
                self._batch_queue.put_nowait((event_type, data))
            except Exception:
                pass

    async def _batch_worker(self, experiments: list[dict], base_env_override: dict) -> None:
        """串行跑每个 episode。每个 episode = 一次 docker compose up --abort-on-container-exit。
        每个 episode 跑完 docker compose down --remove-orphans 清理。
        """
        try:
            # 清理可能残留的容器
            try:
                await self._batch_compose("down", "--remove-orphans")
            except Exception:
                pass

            merged_base = {**BATCH_BASE_ENV, **base_env_override}
            total = len(experiments)

            for idx, cfg in enumerate(experiments, 1):
                if self._batch_cancel_event.is_set():
                    logger.info(f"[DockerProxy] 批处理取消信号触发，跳过 episode {idx}")
                    break

                self._batch_status["idx"] = idx
                await self._batch_emit("batch_progress", {
                    "idx": idx, "total": total, "cfg": cfg,
                })
                logger.info(
                    f"[DockerProxy] 批处理 [{idx}/{total}] "
                    f"fjsp={cfg.get('fjsp_image')} mapf={cfg.get('mapf_image')} seed={cfg.get('seed')}"
                )

                # 组装 ENV（参考 exp0503 run_once）
                env = {**merged_base}
                env["SOLVER_JOB"] = str(cfg.get("solver_job", "http"))
                env["SOLVER_ROUTE"] = str(cfg.get("solver_route", "http"))
                env["SEED"] = str(cfg.get("seed", 42))
                # 镜像变量（docker compose ${VAR} 替换）
                env["FJSP_IMAGE"] = cfg.get(
                    "fjsp_image", "skyengine-fjsp-pso:latest"
                )
                env["MAPF_IMAGE"] = cfg.get(
                    "mapf_image", "skyengine-mapf-astar:latest"
                )
                env["OBS_TYPE"] = str(cfg.get("mapf_obs_type", "default"))
                # 实例覆盖（前端上传后会传 fjsp_instance / mapf_instance 的纯文件名）
                if cfg.get("fjsp_instance"):
                    env["FJSP_INSTANCE"] = str(cfg["fjsp_instance"])
                if cfg.get("mapf_instance"):
                    env["MAPF_INSTANCE"] = str(cfg["mapf_instance"])

                metrics = await self._run_batch_episode(idx, cfg, env)
                self._batch_status["results"].append(metrics)
                await self._batch_emit("batch_metric", {
                    "idx": idx, "cfg": cfg, "metrics": metrics,
                })

                # 每个 episode 之后清理（避免下次冲突）
                try:
                    await self._batch_compose("down", "--remove-orphans")
                except Exception as e:
                    logger.warning(f"[DockerProxy] episode {idx} 后清理失败: {e}")

            self._batch_status["running"] = False
            await self._batch_emit("batch_done", {
                "total": total,
                "completed": len(self._batch_status["results"]),
                "cancelled": self._batch_cancel_event.is_set(),
            })
            logger.info(
                f"[DockerProxy] 批处理完成：{len(self._batch_status['results'])}/{total}"
            )
        except asyncio.CancelledError:
            self._batch_status["running"] = False
            await self._batch_emit("batch_done", {
                "total": len(experiments),
                "completed": len(self._batch_status["results"]),
                "cancelled": True,
            })
            raise
        except Exception as e:
            logger.error(f"[DockerProxy] batch worker 异常: {e}", exc_info=True)
            self._batch_status["running"] = False
            self._batch_status["error"] = str(e)
            await self._batch_emit("batch_error", {"message": str(e)})

    async def _run_batch_episode(self, idx: int, cfg: dict, env: dict) -> dict:
        """跑一次 docker compose up（不加 -d，attach stdout 实时读），解析指标返回。"""
        log_lines: list[str] = []
        cmd = [
            "docker", "compose",
            "-p", self._batch_project_name,
        ]
        if self._project_dir:
            cmd += ["--project-directory", self._project_dir]
        cmd += [
            "-f", self._batch_compose_file,
            "up",
            "--abort-on-container-exit",   # 任一容器退出即整体退出
            "--exit-code-from", "engine",  # 以 engine 退出码为准
            "--no-color",                  # 便于日志解析
        ]
        merged_env = {**os.environ, **env}

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # 合并 stderr 到 stdout
                env=merged_env,
            )

            # 实时按行读 stdout，推到队列
            while True:
                if self._batch_cancel_event.is_set():
                    proc.kill()
                    break
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode(errors="replace").rstrip()
                log_lines.append(text)
                await self._batch_emit("batch_log", {
                    "line": text, "idx": idx, "cfg": cfg,
                })

            await proc.wait()
            rc = proc.returncode
        except asyncio.CancelledError:
            # 取消时也要解析已有日志
            rc = -1
        except Exception as e:
            logger.error(f"[DockerProxy] episode {idx} 异常: {e}", exc_info=True)
            await self._batch_emit("batch_log", {
                "line": f"[DockerProxy ERROR] episode {idx} failed: {e}",
                "idx": idx, "cfg": cfg,
            })
            return {
                "cfg": cfg,
                "terminated_reason": "error",
                "notes": str(e),
                "run_id": f"run_{idx}",
            }

        # 解析指标（参考 exp0503 parse_metrics）
        full_log = "\n".join(log_lines)
        metrics = parse_metrics(full_log)
        metrics["cfg"] = cfg
        metrics["run_id"] = f"run_{idx}"
        metrics["exit_code"] = rc
        if rc != 0 and not metrics.get("completed_makespan"):
            metrics["terminated_reason"] = "error"
            metrics["notes"] = f"exit={rc}"
        return metrics
