"""
FastAPI SSE 服务器，提供环境状态和性能指标实时推送
"""

# 启动脚本 uv run uvicorn application.backend.server:app --reload --host 0.0.0.0 --port 8000

from fastapi import FastAPI, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

# Import factory proxies (must import all to ensure registration)
from application.backend.core.BaseFactoryProxy import (
    ExecutionStatus,
    FactoryProxyProtocol,  # 协议接口 - 支持非继承式复用
)
from application.backend.core.ProxyFactory import ProxyFactory
from application.backend.core.RouteRegistry import RouteRegistry


app = FastAPI()

# 存储当前加载的配置
current_config = None

# 存储当前的工厂代理实例（任何实现了 FactoryProxyProtocol 的对象都可以）
current_factory_proxy: FactoryProxyProtocol = None

# 存储当前的工厂类型
current_factory_type: str = "base_factory"

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
                    # ✅ 不要 return，继续循环等待工厂加载
                    yield format_sse_message("state", {"status": "no_factory"})
                    await asyncio.sleep(2.0)
                    continue
                # 只在工厂运行时发送数据
                if current_factory_proxy.is_running():
                    # 从工厂代理获取事件列表（支持多事件类型）
                    events = await current_factory_proxy.get_state_events()
                    for event_type, data in events:
                        yield format_sse_message(event_type, data)
                else:
                    # 工厂未运行时，发送空闲状态
                    yield format_sse_message(
                        "state", {"status": "idle", "message": "Factory is not running"}
                    )
                    await asyncio.sleep(2.0)

                await asyncio.sleep(0.1)  # 减少轮询间隔，避免状态丢失
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
            yield format_sse_message("state", {"status": "idle"})
            await asyncio.sleep(1.5)  # 确保是 asyncio.sleep 不是 time.sleep

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
    # async def generate():
    #     while True:
    #         try:
    #             if current_factory_proxy is None:
    #                 # ✅ 不要 return，继续循环等待工厂加载
    #                 yield format_sse_message("state", {"status": "no_factory"})
    #                 await asyncio.sleep(2.0)
    #                 continue
    #             # 只在工厂运行时发送数据
    #             if current_factory_proxy.is_running():
    #                 # 从工厂代理获取事件列表（支持多事件类型）
    #                 events = await current_factory_proxy.get_metrics_events()
    #                 for event_type, data in events:
    #                     yield format_sse_message(event_type, data)
    #             else:
    #                 # 工厂未运行时，发送空闲状态
    #                 yield format_sse_message(
    #                     "metrics",
    #                     {"status": "idle", "message": "Factory is not running"},
    #                 )
    #                 await asyncio.sleep(2.0)

    #         except Exception as e:
    #             yield format_sse_message(
    #                 "metrics", {"status": "error", "message": str(e)}
    #             )
    #             break

    # return StreamingResponse(
    #     generate(),
    #     media_type="text/event-stream",
    #     headers={
    #         "Cache-Control": "no-cache",
    #         "X-Accel-Buffering": "no",
    #         "Connection": "keep-alive",
    #     },
    # )


# 工厂控制流（简化路由，不使用 factory_id）
@app.get("/stream/control")
async def stream_control():
    """
    工厂控制流 SSE 端点
    """

    async def generate():
        while True:
            yield format_sse_message("control", {"status": "idle"})
            await asyncio.sleep(2.0)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
    # async def generate():
    #     while True:
    #         try:
    #             if current_factory_proxy is None:
    #                 # ✅ 不要 return，继续循环等待工厂加载
    #                 yield format_sse_message("state", {"status": "no_factory"})
    #                 await asyncio.sleep(2.0)
    #                 continue
    #             # 控制流始终发送状态（包括 idle/running/paused）
    #             events = await current_factory_proxy.get_control_events()
    #             for event_type, data in events:
    #                 yield format_sse_message(event_type, data)

    #             await asyncio.sleep(2.0)  # 控制状态更新频率较低
    #         except Exception as e:
    #             yield format_sse_message(
    #                 "control", {"status": "error", "message": str(e)}
    #             )
    #             break

    # return StreamingResponse(
    #     generate(),
    #     media_type="text/event-stream",
    #     headers={
    #         "Cache-Control": "no-cache",
    #         "X-Accel-Buffering": "no",
    #         "Connection": "keep-alive",
    #     },
    # )


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
        print(config)

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

    global current_factory_proxy
    print("开始执行初始化逻辑0")
    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded"}
    print("开始执行初始化逻辑1")
    try:
        # 如果没有初始化，先初始化
        if (
            current_factory_proxy.status == ExecutionStatus.IDLE
            and current_factory_proxy.current_step == 0
        ):
            await current_factory_proxy.initialize()
            print("[Reset] Factory initialized")

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

    print(f"Switching factory proxy to {factory_id}...")
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

            # todo 
            if factory_type == "packet_factory":
                # todo fix 不成立，因为现在工厂代理的初始化是异步的，需要上传config之后才能init.不能在这里直接调用 initialize 方法
                await current_factory_proxy.initialize()
                
                # 注册后端路由
                RouteRegistry.register_to_app(app)
                print(f"✅ 已注册 {len(RouteRegistry.get_routes())} 条后端路由")
                
                print("✅ PacketFactoryProxy 已初始化并注册所有路由")
                print(f"📋 可用路由列表：{list(RouteRegistry.get_routes().keys())}")
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
    global current_factory_proxy

    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded"}

    try:
        # 如果还没初始化，先初始化
        if current_factory_proxy._state_queue is None:
            await current_factory_proxy.initialize()
            print("[Play] Factory initialized before starting")

        await current_factory_proxy.start()
        print(f"[Play] Factory started, status: {current_factory_proxy.status.value}")
        return {
            "status": "ok",
            "message": "Factory control started successfully",
            "current_status": current_factory_proxy.status.value,
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


@app.post("/factory/algorithm/set")
async def set_algorithm(algorithm: str = Body(..., embed=True)):
    """
    设置当前工厂的调度算法

    Args:
        algorithm: 算法标识符 (如 'default', 'greedy', 'ortools', 'rl' 等)

    Returns:
        设置结果
    """
    global current_factory_proxy

    if current_factory_proxy is None:
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
