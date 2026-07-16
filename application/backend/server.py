"""
FastAPI SSE 服务器，提供环境状态和性能指标实时推送
"""

# 启动脚本 uv run uvicorn application.backend.server:app --reload --host 0.0.0.0 --port 8000

from fastapi import FastAPI, Body, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import atexit
import json
import os
import subprocess


def _cleanup_online_stack() -> None:
    """兜底清理:主栈退出时连带关闭 skyengine-online 栈 (engine/mapf/fjsp),释放 GPU。

    触发机制:uvicorn 收到 SIGTERM(docker compose down) / SIGINT(Ctrl+C)做
    graceful shutdown,Python 解释器随后正常退出,atexit 钩子按 LIFO 跑到这里。

    幂等 —— online 栈没起时 `docker compose down` 是 no-op,不会报错。
    """
    compose_file = os.getenv("SKYENGINE_COMPOSE_PATH")
    project_dir = os.getenv("SKYENGINE_PROJECT_DIR")
    if not compose_file or not os.path.exists(compose_file):
        return  # 没配 / 文件不存在,跳过(不阻塞 backend 退出)

    cmd = ["docker", "compose", "-p", "skyengine-online"]
    if project_dir:
        cmd += ["--project-directory", project_dir]
    cmd += ["-f", compose_file, "down", "--remove-orphans", "--timeout", "8"]

    try:
        # 用 print 而非 logger:解释器关闭阶段 logging handler 可能已拆卸,
        # print 直达 stdout,docker logs 可靠捕获
        print(f"[atexit] 清理 skyengine-online 栈: {' '.join(cmd)}", flush=True)
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        if result.returncode == 0:
            print("[atexit] skyengine-online 栈已清理", flush=True)
        else:
            print(f"[atexit] online 栈清理非零退出(rc={result.returncode}): "
                  f"{result.stderr.decode().strip()}", flush=True)
    except Exception as e:
        # 任何失败都不能阻塞 backend 自身退出
        print(f"[atexit] online 栈清理失败(忽略): {e}", flush=True)


atexit.register(_cleanup_online_stack)

# Import factory proxies (must import all to ensure registration)
from application.backend.core.BaseFactoryProxy import (
    ExecutionStatus,
    FactoryProxyProtocol,  # 协议接口 - 支持非继承式复用
)
from application.backend.core.ProxyFactory import ProxyFactory
from application.backend.core.RouteRegistry import RouteRegistry
from application.backend.core.DockerProxy import DockerProxy

# 批处理专用 DockerProxy 实例（与当前工厂 current_factory_proxy 解耦）
# 这样前端从任何页面（首页、StaticFactory、DockerFactory）都能直接发起批处理
_batch_proxy: DockerProxy | None = None


def _get_batch_proxy() -> DockerProxy:
    """懒加载批处理专用 DockerProxy 单例。"""
    global _batch_proxy
    if _batch_proxy is None:
        _batch_proxy = DockerProxy()
        print("[Batch] 批处理专用 DockerProxy 已创建")
    return _batch_proxy

# History 模块
from application.backend.history.routes import router as history_router
from application.backend.history.manager import HistoryManager

# Analysis 模块（工厂无关的 Run 持久化仓库，dataset/run/）
from application.backend.analysis.routes import router as analysis_router


app = FastAPI()

# 存储当前加载的配置
current_config = None

# 存储当前的工厂代理实例（任何实现了 FactoryProxyProtocol 的对象都可以）
current_factory_proxy: FactoryProxyProtocol = None

# 存储当前的工厂类型
current_factory_type: str = "base_factory"

# 当前运行 ID（由 history 模块分配）
current_run_id: str = None

# History 管理器
history_manager = HistoryManager()

# 注册 history 路由
app.include_router(history_router)

# 注册 analysis 路由（Run 持久化仓库，工厂无关）
app.include_router(analysis_router)

# 添加CORS中间件，支持前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 工具函数 ============
def format_sse_message(event_name: str, data: dict) -> str:
    """格式化SSE消息"""
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ============ 路由函数 ============
# 工厂状态流
@app.get("/stream/state")
async def stream_state():
    """
    工厂状态流 SSE 端点
    """

    async def generate():
        while True:
            try:
                if current_factory_proxy is None:
                    yield format_sse_message("state", {"status": "no_factory"})
                    await asyncio.sleep(2.0)
                    continue

                # DockerProxy 等支持透传的代理：逐事件流式传输
                if hasattr(current_factory_proxy, "state_stream") and current_factory_proxy.is_running():
                    async for event_type, data in current_factory_proxy.state_stream():
                        yield format_sse_message(event_type, data)
                    continue

                # 其他代理：轮询 get_state_events()
                events = await current_factory_proxy.get_state_events()
                if events:
                    for event_type, data in events:
                        yield format_sse_message(event_type, data)
                else:
                    yield format_sse_message(
                        "state", {"status": "idle", "message": "Factory is not running"}
                    )
                    await asyncio.sleep(2.0)
                await asyncio.sleep(0.1)
            except Exception as e:
                yield format_sse_message(
                    "state", {"status": "error", "message": str(e)}
                )
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# 工厂指标流（简化路由，不使用 factory_id）
@app.get("/stream/metrics")
async def stream_metrics():
    """
    工厂指标流 SSE 端点
    """

    async def generate():
        while True:
            try:
                if current_factory_proxy is None:
                    yield format_sse_message("metrics", {"status": "no_factory"})
                    await asyncio.sleep(2.0)
                    continue

                # DockerProxy 等支持透传的代理
                if hasattr(current_factory_proxy, "metrics_stream") and current_factory_proxy.is_running():
                    async for event_type, data in current_factory_proxy.metrics_stream():
                        yield format_sse_message(event_type, data)
                    continue

                # 其他代理：轮询
                if current_factory_proxy.is_running():
                    events = await current_factory_proxy.get_metrics_events()
                    for event_type, data in events:
                        yield format_sse_message(event_type, data)
                else:
                    yield format_sse_message(
                        "metrics",
                        {"status": "idle", "message": "Factory is not running"},
                    )
                    await asyncio.sleep(2.0)
            except Exception as e:
                yield format_sse_message(
                    "metrics", {"status": "error", "message": str(e)}
                )
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# 工厂事件流（简化路由，不使用 factory_id）
@app.get("/stream/events")
async def stream_events():
    """
    工厂事件流 SSE 端点（sim_server 业务事件: machine_start_op / transfer_started 等）
    """

    async def generate():
        while True:
            try:
                if current_factory_proxy is None:
                    yield format_sse_message("event", {"status": "no_factory"})
                    await asyncio.sleep(2.0)
                    continue

                # DockerProxy 透传
                if hasattr(current_factory_proxy, "events_stream") and current_factory_proxy.is_running():
                    async for event_type, data in current_factory_proxy.events_stream():
                        yield format_sse_message(event_type, data)
                    continue

                # 其他代理暂无事件源
                yield format_sse_message(
                    "event",
                    {"status": "idle", "message": "No event source"},
                )
                await asyncio.sleep(2.0)
            except Exception as e:
                yield format_sse_message(
                    "event", {"status": "error", "message": str(e)}
                )
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# 工厂控制流（简化路由，不使用 factory_id）
@app.get("/stream/control")
async def stream_control():
    """
    工厂控制流 SSE 端点
    """

    async def generate():
        while True:
            try:
                if current_factory_proxy is None:
                    yield format_sse_message("control", {"status": "no_factory"})
                    await asyncio.sleep(2.0)
                    continue

                events = await current_factory_proxy.get_control_events()
                for event_type, data in events:
                    yield format_sse_message(event_type, data)
                await asyncio.sleep(2.0)
            except Exception as e:
                yield format_sse_message(
                    "control", {"status": "error", "message": str(e)}
                )
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/factory")
async def factory():
    """根端点，简单欢迎信息"""
    return {"message": "Welcome to the SkyEngine SSE Server"}


@app.post("/algo")
async def algo():
    """
    算法端点，返回当前工厂支持的调度算法列表

    从 current_factory_proxy.inner_properties['algorithm'] 获取算法配置
    返回格式: [{ label: '算法名称', value: 'algorithm_id' }, ...]
    """
    # 默认算法选项（当没有工厂或未配置时使用）
    default_algorithms = [
        {"label": "默认生产运输", "value": "default"},
        {"label": "贪心算法优化", "value": "greedy"},
        {"label": "强化学习 (PPO)", "value": "rl_ppo"},
        {"label": "多代理协同 (MAPF)", "value": "mapf_v2"},
    ]

    # 如果没有加载工厂代理，返回默认选项
    if current_factory_proxy is None:
        return default_algorithms

    # 尝试从 inner_properties 获取算法配置
    if current_factory_proxy.inner_properties is None:
        return default_algorithms

    # 获取算法配置
    algorithm_config = current_factory_proxy.inner_properties.get("algorithm")

    # 如果没有配置算法，返回默认选项
    if algorithm_config is None:
        return default_algorithms

    # 如果 algorithm 是列表格式，直接返回
    if isinstance(algorithm_config, list):
        return algorithm_config

    # 如果 algorithm 是字典格式，转换为前端期望的格式
    if isinstance(algorithm_config, dict):
        # 支持多种格式：
        # 1. { "options": [{ "label": "...", "value": "..." }, ...] }
        # 2. { "assigners": [...], "route_solvers": [...], ... } -> 取第一个可用的
        if "options" in algorithm_config:
            return algorithm_config["options"]
        elif "assigners" in algorithm_config:
            # 返回 assigners 作为算法选项
            assigners = algorithm_config.get("assigners", [])
            return [
                {
                    "label": a.get("name", a.get("id", str(a))),
                    "value": a.get("id", str(a)),
                }
                for a in assigners
            ]

    # 其他情况返回默认选项
    return default_algorithms


@app.post("/factory/config/upload")
async def upload_factory_config(filename: str = None, config: dict = None):
    """上传工厂配置端点"""
    global current_config, current_factory_proxy, current_factory_type

    try:
        if not config:
            return {"status": "error", "message": "配置数据不能为空"}

        # 判断config字段,如果key中有config字段就只保留config
        if "config" in config:
            config = config["config"]

        # 保存配置到全局变量
        current_config = config

        # 初始化工厂
        current_factory_proxy.set_config(config)

        return {
            "status": "ok",
            "message": "Factory configuration uploaded and initialized successfully",
            "config_id": config.get("id", "unknown"),
            "config_name": config.get("name", "unnamed"),
            "factory_type": current_factory_type,
        }
    except Exception as e:
        print(f"❌ 配置上传失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.post("/factory/control/reset")
async def reset_factory_control():
    """重置工厂控制端点"""
    global current_factory_proxy, current_run_id

    print(f"[Reset] 收到请求, 代理: {type(current_factory_proxy).__name__ if current_factory_proxy else 'None'}")
    print(f"[Reset] initialized={current_factory_proxy.get_initialized() if current_factory_proxy else 'N/A'}")

    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded"}
    try:
        # 完成当前历史运行
        if current_run_id:
            try:
                history_manager.complete_run(current_run_id)
                print(f"[Reset] 历史记录已完成: {current_run_id}")
            except Exception as e:
                print(f"[Reset] 完成历史记录失败: {e}")
            current_run_id = None

        # 如果没有初始化，先初始化
        if not current_factory_proxy.get_initialized():
            await current_factory_proxy.initialize()
            print("[Reset] Factory initialized")

        try:
            await current_factory_proxy.reset()
        except AttributeError as e:
            print(f"[Reset] Factory not initialized, initializing...")
            await current_factory_proxy.initialize()
            await current_factory_proxy.reset()


        print(f"[Reset] Factory reset, status: {current_factory_proxy.status.value}")
        return {
            "status": "ok",
            "message": "Factory control reset successfully",
            "current_status": current_factory_proxy.status.value,
        }
    except Exception as e:
        print(f"❌ 重置失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.post("/factory/control/switch")
async def switch_factory_proxy(factory_id: str = Body(..., embed=True)):
    """
    切换工厂代理

    Args:
        factory_id: 工厂ID (packet_factory, grid_factory, huadong_center, southwest_logistics)
    """
    global current_factory_proxy, current_factory_type, current_config

    print(f"===============================")
    print(f"[Switch] 切换工厂代理: {factory_id}")
    print(f"[Switch] 当前代理类型: {current_factory_type}")
    print(f"[Switch] 当前代理实例: {type(current_factory_proxy).__name__ if current_factory_proxy else 'None'}")
    try:
        if not factory_id:
            return {"status": "error", "message": "工厂ID不能为空"}
        # 获取工厂类型
        factory_type = factory_id

        # 如果工厂类型相同，不需要切换
        if current_factory_type == factory_type:
            return {
                "status": "ok",
                "message": f"Factory already switched to {factory_id}",
                "factory_type": factory_type,
            }

        # 清理之前的工厂代理实例
        if current_factory_proxy is not None:
            print(f"🧹 清理之前的工厂代理实例 (type: {current_factory_type})...")
            await current_factory_proxy.cleanup()
            current_factory_proxy = None

        # 创建新的工厂代理实例
        print(f"✅ 切换到工厂: {factory_id} (type: {factory_type})")

        # Handle special case for southwest_logistics
        if factory_type == "southwest_logistics":
            return {
                "status": "ok",
                "message": "Factory coming soon...",
                "factory_id": factory_id,
                "factory_type": factory_type,
            }

        # Create factory proxy using ProxyFactory registry
        try:
            current_factory_proxy = ProxyFactory.create(factory_type)
            print(f"[Switch] 创建成功: {type(current_factory_proxy).__name__}")

            if factory_type == "packet_factory":
                await current_factory_proxy.initialize()
                # 注册后端路由
                RouteRegistry.register_to_app(app)
                print(f"✅ 已注册 {len(RouteRegistry.get_routes())} 条后端路由")

            elif factory_type in ("static_factory", "northeast_center"):
                await current_factory_proxy.initialize()
                RouteRegistry.register_to_app(app)
                print(f"✅ [StaticFactory] 已注册 {len(RouteRegistry.get_routes())} 条路由")

            elif factory_type == "grid_factory_new":
                # DockerProxy: 进页面时立即启动 engine 容器预热
                print("[Switch] DockerProxy: 启动 engine 容器预热...")
                await current_factory_proxy.initialize()
                print("[Switch] DockerProxy: engine 就绪")
        except ValueError as e:
            return {"status": "error", "message": str(e)}

        current_factory_type = factory_type

        return {
            "status": "ok",
            "message": f"Factory switched to {factory_id} successfully",
            "factory_id": factory_id,
            "factory_type": factory_type,
        }
    except Exception as e:
        print(f"❌ 工厂切换失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.post("/factory/control/play")
async def play_factory_control():
    """播放/启动工厂控制端点"""
    global current_factory_proxy, current_run_id

    print(f"[Play] 收到请求, 代理: {type(current_factory_proxy).__name__ if current_factory_proxy else 'None'}")
    print(f"[Play] initialized={current_factory_proxy.get_initialized() if current_factory_proxy else 'N/A'}")

    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded"}

    try:
        # 如果还没初始化，先初始化
        if not current_factory_proxy.get_initialized():
            await current_factory_proxy.initialize()
            print("[Play] Factory initialized before starting")
        try:
            await current_factory_proxy.start()
        except AttributeError as e:
            print(f"[Play] Factory not initialized, initializing...")
            await current_factory_proxy.initialize()
            await current_factory_proxy.reset()
            await current_factory_proxy.start()
        print(f"[Play] Factory started, status: {current_factory_proxy.status.value}")

        # 创建历史运行记录
        algorithm = ''
        try:
            algorithm = current_factory_proxy.get_algorithm()
        except Exception:
            pass
        run_record = history_manager.create_run(
            factory_type=current_factory_type,
            algorithm=algorithm or '',
        )
        current_run_id = run_record.id
        print(f"[Play] 创建历史记录: {current_run_id}")

        return {
            "status": "ok",
            "message": "Factory control started successfully",
            "current_status": current_factory_proxy.status.value,
            "run_id": current_run_id,
        }
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.post("/factory/control/pause")
async def pause_factory_control():
    """暂停工厂控制端点"""
    global current_factory_proxy

    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded"}

    try:
        await current_factory_proxy.pause()
        return {"message": "Factory control paused successfully"}
    except Exception as e:
        print(f"❌ 暂停失败: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.post("/factory/control/insert_jobs")
async def insert_jobs_control(body: dict = Body(...)):
    """运行时批量插单（v2 FJSP 格式）。
    body = {machines?, jobs: [[[{machine, processing}]]], extensions?}
    透传 DockerProxy → engine /sim/insert_jobs。
    非 Docker 工厂返回 unsupported。"""
    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded"}
    if not hasattr(current_factory_proxy, "insert_jobs"):
        return {"status": "error", "message": "Current factory does not support insert_jobs"}
    try:
        return await current_factory_proxy.insert_jobs(body)
    except Exception as e:
        print(f"❌ 插单失败: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.post("/factory/exception/inject")
async def inject_exception_control(body: dict = Body(...)):
    """运行时手动注入 Exception。
    Exception 是环境动力学扰动；前端日志仍通过 /stream/events 展示。"""
    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded"}
    if not hasattr(current_factory_proxy, "inject_exception"):
        return {"status": "error", "message": "Current factory does not support runtime Exception injection"}
    try:
        return await current_factory_proxy.inject_exception(body)
    except Exception as e:
        print(f"❌ Exception 注入失败: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.post("/factory/exception/clear")
async def clear_exception_control(body: dict | None = Body(default=None)):
    """清理运行时手动或仍活跃的 Exception 效果。"""
    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded"}
    if not hasattr(current_factory_proxy, "clear_exceptions"):
        return {"status": "error", "message": "Current factory does not support runtime Exception clearing"}
    try:
        return await current_factory_proxy.clear_exceptions(body or {})
    except Exception as e:
        print(f"❌ Exception 清理失败: {str(e)}")
        return {"status": "error", "message": str(e)}


# ==================== 批处理（DockerProxy 专用）====================
# 设计见 finalpro/SkyEngine/explore/0704批处理前端调用设计.md
# 4 个端点：start / cancel / status / stream
# 非 DockerProxy 工厂（如 StaticFactoryProxy）返回 unsupported

@app.post("/batch/start")
async def batch_start(body: dict = Body(...)):
    """启动批处理。body = {experiments: [...], base_env?: {...}}
    experiments 每项 = {solver_job, solver_route, fjsp_image, mapf_image, mapf_obs_type, seed}
    （参考 experiment/exp0503/run_experiments.py）。
    使用与工厂解耦的批处理专用 DockerProxy 单例，任何页面都可调用。
    """
    proxy = _get_batch_proxy()
    experiments = body.get("experiments")
    if not isinstance(experiments, list) or not experiments:
        return {"status": "error", "message": "experiments 必须是非空数组"}
    base_env = body.get("base_env") or {}
    try:
        return await proxy.start_batch(experiments, base_env)
    except Exception as e:
        print(f"❌ 批处理启动失败: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.post("/batch/cancel")
async def batch_cancel():
    """取消批处理：docker compose down + 停 worker。"""
    proxy = _get_batch_proxy()
    try:
        return await proxy.cancel_batch()
    except Exception as e:
        print(f"❌ 批处理取消失败: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.post("/batch/upload_instance")
async def batch_upload_instance(
    file: UploadFile = File(...),
    kind: str = Form(...),
):
    """上传 FJSP/MAPF 实例文件到宿主机 dataset/{kind}/ 下。
    返回 {status, filename}。批处理 start 时把这个 filename 放到
    experiments[].fjsp_instance / mapf_instance 字段即可让容器使用。
    """
    proxy = _get_batch_proxy()
    try:
        content = await file.read()
        filename = proxy.save_batch_instance(file.filename, content, kind)
        return {"status": "ok", "filename": filename, "size": len(content)}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        print(f"❌ 实例上传失败: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/batch/status")
async def batch_status():
    """查询批处理状态。"""
    proxy = _get_batch_proxy()
    return proxy.get_batch_status()


@app.get("/batch/stream")
async def batch_stream():
    """SSE 流：batch_progress / batch_log / batch_metric / batch_done / batch_error。
    断开连接时自动取消订阅（与 /stream/events 同模式）。"""
    proxy = _get_batch_proxy()

    async def generate():
        try:
            async for event_type, data in proxy.batch_stream():
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            # 客户端断开
            pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/factory/algorithm/set")
async def set_algorithm(algorithm: str = Body(..., embed=True)):
    """
    设置当前工厂的调度算法
    """
    global current_factory_proxy

    print(f"[Algorithm] 收到请求: algorithm={algorithm}")
    print(f"[Algorithm] 当前代理: {type(current_factory_proxy).__name__ if current_factory_proxy else 'None'}")

    if current_factory_proxy is None:
        print(f"[Algorithm] 错误: 无工厂代理")
        return {"status": "error", "message": "No factory loaded"}

    try:
        current_factory_proxy.set_algorithm(algorithm)
        return {
            "status": "ok",
            "message": f"Algorithm set to '{algorithm}' successfully",
            "algorithm": algorithm,
        }
    except Exception as e:
        print(f"❌ 设置算法失败: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/factory/algorithm/get")
async def get_algorithm():
    """
    获取当前工厂的调度算法

    Returns:
        当前算法标识符
    """
    global current_factory_proxy

    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded", "algorithm": None}

    try:
        algorithm = current_factory_proxy.get_algorithm()
        return {
            "status": "ok",
            "algorithm": algorithm,
        }
    except Exception as e:
        print(f"❌ 获取算法失败: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/factory/control/state")
async def get_factory_control_state():
    """获取工厂控制状态端点"""
    global current_factory_proxy

    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded"}

    try:
        status = await current_factory_proxy.get_control_status()
        return {"status": "ok", "data": status}
    except Exception as e:
        print(f"❌ 获取状态失败: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.post("/factory/control/disconnect")
async def disconnect_factory():
    """断开工厂连接，清理代理资源"""
    global current_factory_proxy, current_factory_type, current_config, current_run_id

    print(f"[Disconnect] 清理工厂代理: {current_factory_type}")

    # 完成历史运行记录
    if current_run_id:
        try:
            history_manager.complete_run(current_run_id)
            print(f"[Disconnect] 历史记录已完成: {current_run_id}")
        except Exception as e:
            print(f"[Disconnect] 完成历史记录失败: {e}")
        current_run_id = None

    if current_factory_proxy is not None:
        try:
            await current_factory_proxy.cleanup()
        except Exception as e:
            print(f"[Disconnect] cleanup 失败: {e}")
        current_factory_proxy = None

    current_factory_type = "base_factory"
    current_config = None
    print("[Disconnect] 工厂代理已清理")
    return {"status": "ok", "message": "Factory disconnected"}


@app.get("/dataset/list")
async def list_datasets():
    """列出所有可用的 FJSP 实例和 MAPF 地图"""
    from dataset.helper import list_available_datasets
    import yaml
    from pathlib import Path

    # FJSP: 使用 helper 原生方法（只从 fjsp-instances/ 读取）
    datasets = list_available_datasets(data_dir="./dataset")

    # MAPF: 从 map_dataset/gpt_eval_config/ 读取（本项目实际路径）
    mapf_maps = {}
    map_base = Path("./dataset/map_dataset/gpt_eval_config")
    if map_base.exists():
        for cat_dir in sorted(map_base.iterdir()):
            if not cat_dir.is_dir():
                continue
            maps_yaml = cat_dir / "maps.yaml"
            if maps_yaml.exists():
                try:
                    with open(maps_yaml) as f:
                        maps = yaml.safe_load(f)
                    mapf_maps[cat_dir.name] = list(maps.keys())
                except Exception:
                    pass

    # 合并 fjsp_benchmarks 的 key 已含子目录路径（如 hurink/edata），
    # 直接作为前端 category 使用
    result = {
        "fjsp_instances": datasets.get("fjsp_benchmarks", {}),
        "mapf_maps": mapf_maps,
    }
    return result


@app.post("/dataset/generate")
async def generate_dataset_config(body: dict = Body(...)):
    """根据选择的 FJSP + MAPF 生成工厂配置"""
    from dataset.helper import (
        _find_fjsp, load_fjsp_json, load_fjsp_benchmark,
        load_mapf_yaml, convert_to_grid_factory,
    )
    from pathlib import Path

    fjsp_category = body.get("fjsp_category", "")
    fjsp_instance = body.get("fjsp_instance", "")
    map_category = body.get("map_category", "")
    map_name = body.get("map_name", "")

    try:
        data_dir = Path("./dataset")

        # --- 解析 FJSP ---
        fjsp_name = f"{fjsp_category}/{fjsp_instance}" if fjsp_category else fjsp_instance
        fjsp_path = _find_fjsp(data_dir, fjsp_name)
        if fjsp_path is None:
            return {"status": "error", "message": f"FJSP 实例未找到: {fjsp_name}"}

        if fjsp_path.suffix == ".json":
            fjsp_data = load_fjsp_json(str(fjsp_path))
        else:
            fjsp_data = load_fjsp_benchmark(str(fjsp_path))

        # --- 解析 MAPF 地图 ---
        map_yaml = data_dir / f"map_dataset/gpt_eval_config/{map_category}/maps.yaml"
        if not map_yaml.exists():
            return {"status": "error", "message": f"地图类别不存在: {map_category}"}
        map_data = load_mapf_yaml(str(map_yaml), map_name or None)

        # --- 转换 ---
        config = convert_to_grid_factory(
            fjsp_data=fjsp_data,
            map_data=map_data,
            num_agvs=body.get("num_agvs", 4),
            agv_velocity=body.get("agv_velocity", 1.0),
            seed=body.get("seed", 42),
        )
        return {"status": "ok", "config": config}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok"}


@app.get("/scenario/status")
async def scenario_status():
    """场景状态端点，连接上真实场景才行"""

    if current_factory_proxy is None:
        return {
            "connected": False,
            "scenario": "not_connected",
            "status": None,
            "current_step": None,
        }

    return {
        "connected": True,  # StaticFactoryProxy 已加载，认为连接
        "scenario": "static_factory",
        "status": current_factory_proxy.status.value,
        "current_step": current_factory_proxy.current_step,
    }


@app.on_event("startup")
async def startup_event():
    # 启动时扫描路径注册所有工厂代理
    import importlib
    import pkgutil
    import application.backend.core

    for _, module_name, _ in pkgutil.iter_modules(application.backend.core.__path__):
        importlib.import_module(f"{application.backend.core.__name__}.{module_name}")
