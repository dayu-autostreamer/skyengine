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
from starlette.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

import config
from backend.core.lib.network.api import GridAPI

from sky_executor.grid_factory.core.core import Core

# service引入

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
        self.core = Core()

        # ========== 预览代码 ==========
        @config_router.api_route(
            path=GridAPI.CASES_PREVIEW.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.CASES_PREVIEW.method],  # 从GridAPI获取HTTP请求方法
            response_class=StreamingResponse,
        )
        async def preview_factory(factory_id: str):
            """
            动态返回工厂布局图片
            """
            # 假设图片存放在 public/images/factory 下
            img_dir = config.BACKEND_ENV_DIR
            img_name = f"{factory_id}"
            img_path = os.path.join(img_dir, img_name)

            if not os.path.exists(img_path):
                return {"error": "Image not found"}

            # 打开文件，返回 StreamingResponse
            def iterfile():
                with open(img_path, mode="rb") as f:
                    yield from f

            return StreamingResponse(iterfile(), media_type="image/png")

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
            if self.core.start():
                return {"message": "仿真启动成功 ✅"}
            return {"message": "仿真已在运行中 ⚠️"}

        @component_router.api_route(
            path=GridAPI.FACTORY_PAUSE.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.FACTORY_PAUSE.method],  # 从GridAPI获取HTTP请求方法
            response_class=JSONResponse,
        )
        async def factory_pause():
            if self.core.pause():
                return {"message": "仿真已暂停 ⏸️"}
            return {"message": "当前仿真未运行 ⚠️"}

        @component_router.api_route(
            path=GridAPI.FACTORY_RESUME.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.FACTORY_RESUME.method],  # 从GridAPI获取HTTP请求方法
            response_class=JSONResponse,
        )
        async def factory_resume():
            if self.core.resume():
                return {"message": "仿真已恢复 ▶️"}
            return {"message": "当前仿真未运行 ⚠️"}

        @component_router.api_route(
            path=GridAPI.FACTORY_RESET.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.FACTORY_RESET.method],  # 从GridAPI获取HTTP请求方法
            response_class=JSONResponse,
        )
        async def factory_reset():
            self.core.reset()
            return ({"message": "仿真环境已重置 🔄"})

        @component_router.api_route(
            path=GridAPI.MAP_RENDER.path,
            methods=[GridAPI.MAP_RENDER.method],
            response_class=JSONResponse,
        )
        async def map_render(request: Request):
            data = await request.json()
            factory_name = data.get("factory_name")
            if factory_name:
                print(factory_name)
                self.core.set_factory(factory_name)
            svg_pic = self.core.render_map()
            return {"message": "渲染成功 ✅", "svg_pic": svg_pic}

        @component_router.api_route(
            path=GridAPI.FACTORY_LIST.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.FACTORY_LIST.method],  # 从GridAPI获取HTTP请求方法
            response_class=JSONResponse,
        )
        async def get_factory_list():
            factory_list = self.core.get_factory_list()
            factory_dict_list = []
            for factory in factory_list:
                temp_dict = {"id": factory}
                factory_dict_list.append(temp_dict)
            return {"message": "获取工厂列表成功 ✅", "factory_list": factory_dict_list}

        @component_router.api_route(
            path=GridAPI.JOB_LIST.path,  # 从GridAPI获取接口路径
            methods=[GridAPI.JOB_LIST.method],  # 从GridAPI获取HTTP请求方法
            response_class=JSONResponse,
        )
        async def get_job_list():
            job_list = self.core.get_job_list()
            job_dict_list = []
            for factory in job_list:
                temp_dict = {"id": factory}
                job_dict_list.append(temp_dict)
            return {"message": "获取任务列表成功 ✅", "job_list": job_dict_list}
        # ========== 智能体组件相关代码 ==========
