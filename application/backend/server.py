"""
FastAPI SSE 服务器，提供环境状态和性能指标实时推送
"""

# 启动脚本 uv run uvicorn application.backend.server:app --reload --port 8000

from fastapi import FastAPI, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

# Import factory proxies (must import all to ensure registration)
from application.backend.core.BaseFactoryProxy import BaseFactoryProxy, ExecutionStatus
from application.backend.core.ProxyFactory import ProxyFactory


app = FastAPI()

# 存储当前加载的配置
current_config = None

# 存储当前的工厂代理实例
current_factory_proxy: BaseFactoryProxy = None

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
# 工厂状态流（简化路由，不使用 factory_id）
@app.get("/stream/state")
async def stream_state():
    """
    工厂状态流 SSE 端点
    """

    async def generate():
        if current_factory_proxy is None:
            yield format_sse_message("state", {"status": "no_factory"})
            return

        while True:
            try:
                # 只在工厂运行时发送数据
                if current_factory_proxy.is_running():
                    # 从工厂代理获取事件列表（支持多事件类型）
                    events = await current_factory_proxy.get_state_events()
                    for event_type, data in events:
                        yield format_sse_message(event_type, data)
                else:
                    # 工厂未运行时，发送空闲状态
                    yield format_sse_message("state", {
                        "status": "idle",
                        "message": "Factory is not running"
                    })
                
                await asyncio.sleep(1.5)
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
        if current_factory_proxy is None:
            yield format_sse_message("metrics", {"status": "no_factory"})
            return

        while True:
            try:
                # 只在工厂运行时发送数据
                if current_factory_proxy.is_running():
                    # 从工厂代理获取事件列表（支持多事件类型）
                    events = await current_factory_proxy.get_metrics_events()
                    for event_type, data in events:
                        yield format_sse_message(event_type, data)
                else:
                    # 工厂未运行时，发送空闲状态
                    yield format_sse_message("metrics", {
                        "status": "idle",
                        "message": "Factory is not running"
                    })
                
                await asyncio.sleep(1.5)
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


# 工厂控制流（简化路由，不使用 factory_id）
@app.get("/stream/control")
async def stream_control():
    """
    工厂控制流 SSE 端点
    """

    async def generate():
        if current_factory_proxy is None:
            yield format_sse_message("control", {"status": "no_factory"})
            return

        while True:
            try:
                # 控制流始终发送状态（包括 idle/running/paused）
                events = await current_factory_proxy.get_control_events()
                for event_type, data in events:
                    yield format_sse_message(event_type, data)
                
                await asyncio.sleep(2.0)  # 控制状态更新频率较低
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


@app.post("/factory/config/upload")
async def upload_factory_config(filename: str = None, config: dict = None):
    """上传工厂配置端点"""
    global current_config, current_factory_proxy, current_factory_type

    try:
        if not config:
            return {"status": "error", "message": "配置数据不能为空"}

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
    global current_factory_proxy

    if current_factory_proxy is None:
        return {"status": "error", "message": "No factory loaded"}

    try:
        # 如果没有初始化，先初始化
        if current_factory_proxy.status == ExecutionStatus.IDLE and current_factory_proxy.current_step == 0:
            await current_factory_proxy.initialize()
            print("[Reset] Factory initialized")
        
        await current_factory_proxy.reset()
        print(f"[Reset] Factory reset, status: {current_factory_proxy.status.value}")
        return {
            "status": "ok",
            "message": "Factory control reset successfully",
            "current_status": current_factory_proxy.status.value
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
            "current_status": current_factory_proxy.status.value
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
