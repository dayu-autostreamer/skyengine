'''
@Project ：SkyEngine 
@File    ：control_server.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/10/21 11:53 
'''
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware


from backend.controller.api_handler import (
    manage_router,
    monitor_router,
    config_router,
    agent_router,
    component_router,
    normal_router,
    api_handler
)

from sky_logs.logger import BACKEND_LOGGER as LOGGER
from sky_logs.dc_helper import DiskCacheHelper

class BackendServer:
    def __init__(self):
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

        self.app.include_router(manage_router)
        self.app.include_router(agent_router)
        self.app.include_router(monitor_router)
        self.app.include_router(component_router)
        self.app.include_router(config_router)
        self.app.include_router(normal_router)
