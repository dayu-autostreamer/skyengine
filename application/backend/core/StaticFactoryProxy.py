"""
@Project ：SkyEngine
@File    ：StaticFactoryProxy.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/1/19 14:50

================================================================================
⚠️  占位实现 / PLACEHOLDER
================================================================================

StaticFactory 的仿真数据 100% 在浏览器内由前端剧本生成，后端不参与任何
frame / metrics / events 的产出与流转：

    StaticFactoryManage.vue (mode="frontend")
       → useSimulationConfig.executeFrontend()
       → runFullSystemTest(store, monitorStore, ...)   # 全在浏览器里
       → store.pushSnapshot() / monitorStore.pushMetrics()

本 Proxy 之所以保留，仅出于两个最小原因：
  1. server.py switch 时仍按 ProxyFactory.create("static_factory"|"northeast_center")
     创建实例并调 initialize()；删掉会让 switch 路由报错。
  2. 注册一条 /analysis/export mock 路由 —— 前端 analysisLog.exportRun/exportLive
     通过它触发浏览器下载（后端只加 Content-Disposition 头原样回吐 JSON）。

所以这里：
  - 所有流式 / 快照 / 控制方法都是 no-op，返回空。
  - 永远不会进入 RUNNING 状态（is_running() 恒为 False），server.py 的 SSE
    分支会走 pull 兜底路径，pull 返回空，不影响前端（前端根本不订阅后端流）。
  - 真实数据契约见 application/frontend/src/scenarios/fullSystemTest.js。

若未来要让 StaticFactory 走后端流（与容器化 SkyEngine 对齐），在此处重新
实现 BaseFactoryProxy 的流式接口即可；当前刻意保持空壳以简化系统。
================================================================================
"""

import json
import logging

from fastapi.responses import Response

from .BaseFactoryProxy import BaseFactoryProxy
from .ProxyFactory import ProxyFactory
from .RouteRegistry import RouteRegistry

logger = logging.getLogger(__name__)


@ProxyFactory.register_proxy("static_factory")
@ProxyFactory.register_proxy("northeast_center")
class StaticFactoryProxy(BaseFactoryProxy):
    """StaticFactory 占位 Proxy（详见模块 docstring）。"""

    def __init__(self):
        super().__init__()
        self.initialized = False

    # ==================== 生命周期 ====================

    async def initialize(self):
        """占位初始化：仅注册 /analysis/export mock 下载路由。"""
        self._register_analysis_routes()
        self.initialized = True
        logger.info("[StaticFactoryProxy] 占位 proxy 已初始化（无仿真数据流）")

    async def cleanup(self):
        """无资源需释放。"""
        self.initialized = False

    async def start(self):
        """no-op：前端模式不通过后端启动。保持 IDLE 不变。"""
        pass

    async def pause(self):
        pass

    async def reset(self):
        pass

    async def stop(self):
        pass

    async def insert_jobs(self, body: dict) -> dict:
        return {
            "status": "error", "phase": "rejected", "inserted": [], "rejected": [],
            "message": "StaticFactory 不支持真实插单，请切换到容器化工厂",
        }

    # ==================== 快照 / 流式（恒空） ====================
    # server.py 的 SSE 路由会调这些方法；前端不订阅，返回空避免异常。

    async def get_state_snapshot(self) -> dict:
        return {}

    async def get_metrics_snapshot(self) -> dict:
        return {}

    async def get_control_status(self) -> dict:
        return {
            "status": self._status.value,
            "current_step": 0,
            "total_steps": 0,
            "config": {},
        }

    # ==================== 配置 ====================

    def get_initialized(self):
        return self.initialized

    def set_config(self, config: dict):
        """StaticFactory 无配置；no-op。"""
        pass

    # ==================== 唯一真实功能：分析导出 mock 路由 ====================

    def _register_analysis_routes(self):
        """模块③ 演示路由：服务端下载接口的 mock 版本。

        前端把内存中的 run 快照 POST 过来，后端加 Content-Disposition: attachment
        头原样回吐，浏览器看到 attachment 头触发下载。等价于真实落盘文件的下载
        链路，未来接真实后端时把这里换成 FileResponse 即可，调用方零改动。
        """

        @RouteRegistry.register_route("/analysis/export", method="POST")
        async def api_analysis_export(payload: dict):
            run_id = (payload or {}).get("id") or f"run_{int(__import__('time').time())}"
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(run_id))
            return Response(
                content=body,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_id}.json"',
                },
            )
