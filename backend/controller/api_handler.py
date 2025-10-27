'''
@Project ：SkyEngine 
@File    ：api_handler.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/10/21 12:18 
'''

import os
import asyncio
from enum import Enum
from fastapi.routing import APIRouter
from starlette.responses import JSONResponse, StreamingResponse
from sky_logs.logger import BACKEND_LOGGER as LOGGER

from fastapi import Request

import config
from backend.core.lib.network.api import GridAPI

manage_router = APIRouter(tags=["Manage"])
monitor_router = APIRouter(tags=["Monitor"])
agent_router = APIRouter(tags=["Agent"])
component_router = APIRouter(tags=["Component"])
config_router = APIRouter(tags=["Config"])
normal_router = APIRouter(tags=["Normal"])


class SupportFactory(Enum):
    PACKET = "PACKET"
    GRID = "GRID"


class APIHandler:
    # ================== 新增的安全切换函数 ==================
    async def switch_core(self, factory_type: str):
        """
        安全切换 APIHandler 管理的核心模块
        """
        async with self.core_lock:
            if self.is_switching:
                LOGGER.warning("[Core] 已有切换正在进行中，跳过重复请求 ⚠️")
                return False

            self.is_switching = True
            LOGGER.info(f"[Core] 开始切换核心至 {factory_type} ...")

            # 关闭旧 core
            if self.core is not None:
                try:
                    if hasattr(self.core, "shutdown"):
                        await self.core.shutdown()
                    elif hasattr(self.core, "close"):
                        self.core.close()
                    LOGGER.info("[Core] 旧核心已安全关闭 ✅")
                except Exception as e:
                    LOGGER.error(f"[Core] 关闭旧核心时发生错误: {e}")

            # 加载新 core
            try:
                if factory_type == SupportFactory.PACKET.value:
                    from sky_executor.packet_factory.packet_factory_core.packet_core import BackendCore
                    self.core = BackendCore()
                elif factory_type == SupportFactory.GRID.value:
                    from sky_executor.grid_factory.core.core import Core
                    self.core = Core()
                else:
                    LOGGER.error(f"[Core] 未知的工厂类型: {factory_type}")
                    self.is_switching = False
                    return False

                self.core_type = factory_type
                LOGGER.info(f"[Core] 已成功切换至 {factory_type} ✅")

            except Exception as e:
                LOGGER.error(f"[Core] 切换失败: {e}")
                self.core = None
                self.core_type = None
                self.is_switching = False
                return False

            self.is_switching = False
            return True

    def __init__(self, ):
        self.core = None
        self.core_lock = asyncio.Lock()
        self.core_type = None
        self.is_switching = False

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



api_handler = APIHandler()

class ManageHandler:
    def __init__(self, ):
        # ========== 切换Core的路由 ==========
        @normal_router.api_route(
            path=GridAPI.MANAGE_FACTORY.path,
            methods=[GridAPI.MANAGE_FACTORY.method],
            response_class=JSONResponse,
        )
        async def update_handler(request: Request):
            data = await request.json()
            factory_type = data.get("factory_type")

            if not factory_type:
                return {"message": "缺少 factory_type 参数 ⚠️"}

            ok = await api_handler.switch_core(factory_type)
            if ok:
                return {"message": f"环境切换成功 ✅ 当前工厂：{factory_type}"}
            return {"message": "环境切换失败 ❌"}

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
            img_dir = config.BACKEND_ENV_DIR + "/environment_preview"
            img_name = f"{factory_id}"
            img_path = os.path.join(img_dir, img_name)

            if not os.path.exists(img_path):
                return {"error": "Image not found"}

            # 打开文件，返回 StreamingResponse
            def iterfile():
                with open(img_path, mode="rb") as f:
                    yield from f

            return StreamingResponse(iterfile(), media_type="image/png")
