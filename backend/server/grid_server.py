'''
@Project ：SkyEngine 
@File    ：grid_server.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/11 14:57
'''
import os

from fastapi import FastAPI
from fastapi.routing import APIRouter
from starlette.responses import JSONResponse, FileResponse, StreamingResponse, Response
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware

import config
from backend.core.lib.network.api import GridAPI

from backend.environment.grid_core import GridCore

# service引入
from backend.service.grid import agent_service, file_service

from sky_logs.logger import BACKEND_LOGGER as LOGGER
from sky_logs.dc_helper import DiskCacheHelper

monitor_router = APIRouter(tags=["Monitor"])
agent_router = APIRouter(tags=["Agent"])
component_router = APIRouter(tags=["Component"])
config_router = APIRouter(tags=["Config"])
normal_router = APIRouter(tags=["Normal"])


class BackendServer:
    def __init__(self):
        # 初始化 FastAPI 实例
        handler = APIHandler()

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            LOGGER.info("[Startup] 后端服务已启动成功 ✅")
            yield
            LOGGER.info("[Closedown] 后端服务已成功关闭 ✅")

        # 每次开始运行时,刷新缓存区
        self.dc_helper = DiskCacheHelper(expire=600)
        self.dc_helper.clear()

        self.app = FastAPI(rlog_level='trace', timeout=6000, lifespan=lifespan)

        self.app.add_middleware(
            CORSMiddleware, allow_origins=["*"], allow_credentials=True,
            allow_methods=["*"], allow_headers=["*"],
        )

        self.app.include_router(agent_router)
        self.app.include_router(monitor_router)
        self.app.include_router(component_router)
        self.app.include_router(config_router)
        self.app.include_router(normal_router)


class APIHandler:
    def __init__(self):
        self.core = GridCore()

        # ========== 测试相关代码 ==========
        @normal_router.api_route(
            path=GridAPI.AGV_MONITOR.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.AGV_MONITOR.method],  # 从GridAPI获取HTTP请求方法
            response_class=StreamingResponse,
        )
        async def test():
            print(233)
            return

        # ========== 监控相关代码 ==========
        @monitor_router.api_route(
            path=GridAPI.AGV_MONITOR.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.AGV_MONITOR.method],  # 从GridAPI获取HTTP请求方法
            response_class=StreamingResponse,
        )
        async def agv_monitor():
            return

        # ========== 工厂组件相关代码 ==========
        @component_router.api_route(
            path=GridAPI.FACTORY_START.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.FACTORY_START.method],  # 从GridAPI获取HTTP请求方法
            response_class=JSONResponse,
        )
        async def factory_start():
            self.core.render_map()
            return {"message": "启动成功"}

        @component_router.api_route(
            path=GridAPI.FACTORY_PAUSE.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.FACTORY_PAUSE.method],  # 从GridAPI获取HTTP请求方法
            response_class=JSONResponse,
        )
        async def factory_pause():
            self.core.pause_map()
            return {"message": "暂停成功"}

        @component_router.api_route(
            path=GridAPI.FACTORY_RESET.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.FACTORY_RESET.method],  # 从GridAPI获取HTTP请求方法
            response_class=JSONResponse,
        )
        async def factory_reset():
            self.core.reset()
            return {"message": "渲染成功"}

        # ========== 智能体组件相关代码 ==========
