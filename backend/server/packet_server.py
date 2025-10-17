import os

from fastapi import FastAPI, File, UploadFile, Body, Request
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse, FileResponse, StreamingResponse, Response
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware

import config
from backend.core.lib.network.api import NetworkAPIMethod, NetworkAPIPath

from sky_executor.packet_factory.packet_factory_core.packet_core import BackendCore

# service引入
from backend.service.packet import monitor_service, agent_service, file_service

from sky_logs.logger import BACKEND_LOGGER as LOGGER
from sky_logs.dc_helper import DiskCacheHelper


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

        self.routes = [
            # 工厂控制
            APIRoute(NetworkAPIPath.FACTORY_ALIVE,
                     handler.handle_factory_alive,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.FACTORY_ALIVE]),

            APIRoute(NetworkAPIPath.FACTORY_START,
                     handler.handle_factory_start,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.FACTORY_START]),

            APIRoute(NetworkAPIPath.FACTORY_PAUSE,
                     handler.handle_factory_pause,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.FACTORY_PAUSE]),

            APIRoute(NetworkAPIPath.FACTORY_RESET,
                     handler.handle_factory_reset,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.FACTORY_RESET]),

            APIRoute(NetworkAPIPath.FACTORY_SPEED,
                     handler.handle_factory_speed,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.FACTORY_SPEED]),

            # AGV 控制
            APIRoute(NetworkAPIPath.AGVS,
                     handler.handle_agvs,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.AGVS]),

            APIRoute(NetworkAPIPath.AGV_PAUSE,
                     handler.handle_agv_pause,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.AGV_PAUSE]),

            APIRoute(NetworkAPIPath.AGV_RESUME,
                     handler.handle_agv_resume,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.AGV_RESUME]),

            # 机器控制
            APIRoute(NetworkAPIPath.MACHINES,
                     handler.handle_machines,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.MACHINES]),

            APIRoute(NetworkAPIPath.MACHINE_PAUSE,
                     handler.handle_machine_pause,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.MACHINE_PAUSE]),

            APIRoute(NetworkAPIPath.MACHINE_RESUME,
                     handler.handle_machine_resume,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.MACHINE_RESUME]),

            # Job 控制
            APIRoute(NetworkAPIPath.JOB_TEMPLATES,
                     handler.handle_job_templates,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.JOB_TEMPLATES]),

            APIRoute(NetworkAPIPath.JOB_ADD,
                     handler.handle_job_add,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.JOB_ADD]),
        ]

        self.map_routes = [
            # 信息展示
            APIRoute(NetworkAPIPath.JOBS_PROGRESS,
                     handler.handle_jobs_progress,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.JOBS_PROGRESS]),

            # 上传配置
            APIRoute(NetworkAPIPath.YAML_UPLOAD,
                     handler.handle_yaml_upload,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.YAML_UPLOAD]),

            # 获取标准配置集合
            APIRoute(NetworkAPIPath.STANDARD_GET,
                     handler.handle_template_download,
                     response_class=FileResponse,
                     methods=[NetworkAPIMethod.STANDARD_GET]),

            # 下载日志
            APIRoute(NetworkAPIPath.LOG_DOWNLOAD,
                     handler.handle_log_download,
                     response_class=FileResponse,
                     methods=[NetworkAPIMethod.LOG_DOWNLOAD]),

            # 获取地图
            APIRoute(NetworkAPIPath.MAP_UPDATE,
                     handler.handle_map_display,
                     response_class=StreamingResponse,
                     methods=[NetworkAPIMethod.MAP_UPDATE]),

            # 启动地图
            APIRoute(NetworkAPIPath.MAP_RENDER,
                     handler.handle_map_render,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.MAP_RENDER]),

            # 获取工厂列表
            APIRoute(NetworkAPIPath.FACTORY_LIST,
                     handler.handle_file_list,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.FACTORY_LIST]),

            # 获取案例
            APIRoute(NetworkAPIPath.CASES_IMAGE,
                     handler.handle_cases_image,
                     response_class=StreamingResponse,
                     methods=[NetworkAPIMethod.CASES_IMAGE]),

            APIRoute(NetworkAPIPath.CASES_CONFIG,
                     handler.handle_cases_config,
                     response_class=FileResponse,
                     methods=[NetworkAPIMethod.CASES_CONFIG]),
        ]
        self.agent_routes = [
            APIRoute(NetworkAPIPath.AGENT_LIST,
                     handler.get_agent_list,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.AGENT_LIST]),
            APIRoute(NetworkAPIPath.SET_AGENT,
                     handler.set_agent,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.SET_AGENT]),
        ]
        self.monitor_routes = [
            APIRoute(NetworkAPIPath.AGV_MONITOR,
                     handler.get_agv_indicator,
                     response_class=StreamingResponse,
                     methods=[NetworkAPIMethod.AGV_MONITOR]),
            APIRoute(NetworkAPIPath.MACHINE_MONITOR,
                     handler.get_machine_indicator,
                     response_class=StreamingResponse,
                     methods=[NetworkAPIMethod.MACHINE_MONITOR]),
            APIRoute(NetworkAPIPath.JOB_MONITOR,
                     handler.get_job_indicator,
                     response_class=StreamingResponse,
                     methods=[NetworkAPIMethod.JOB_MONITOR]),
            APIRoute(NetworkAPIPath.SYSTEM_MONITOR,
                     handler.get_system_indicator,
                     response_class=StreamingResponse,
                     methods=[NetworkAPIMethod.SYSTEM_MONITOR]),
            APIRoute(NetworkAPIPath.TOTAL_MONITOR,
                     handler.get_total_indicator,
                     response_class=StreamingResponse,
                     methods=[NetworkAPIMethod.TOTAL_MONITOR]),
        ]
        self.routes.extend(self.map_routes)
        self.routes.extend(self.agent_routes)
        self.routes.extend(self.monitor_routes)

        self.app = FastAPI(routes=self.routes, log_level='trace', timeout=6000, lifespan=lifespan)

        self.app.add_middleware(
            CORSMiddleware, allow_origins=["*"], allow_credentials=True,
            allow_methods=["*"], allow_headers=["*"],
        )


class APIHandler:
    def __init__(self):
        self.server = BackendCore()

    async def handle_factory_alive(self):
        is_alive = self.server.is_factory_alive()
        return JSONResponse({"is_alive": is_alive})

    async def handle_factory_start(self):
        self.server.factory_start()
        return JSONResponse({"action": "start"})

    async def handle_factory_pause(self):
        self.server.factory_pause()
        return JSONResponse({"action": "pause"})

    async def handle_factory_reset(self):
        self.server.factory_reset()
        return JSONResponse({"action": "reset"})

    async def handle_factory_speed(self, data=Body(...)):
        speedLevel = data["speedLevel"]
        self.server.change_factory_speed(speedLevel)
        return JSONResponse({'state': 'success', 'msg': f'change factory speed={speedLevel} success'})

    async def handle_agvs(self):
        agv_list = self.server.get_agvs()
        return JSONResponse({"agvs": agv_list})

    async def handle_agv_pause(self, agvId):
        self.server.pause_agv(int(agvId))
        return JSONResponse({'state': 'success', 'msg': f'pause agv id={agvId} success'})

    async def handle_agv_resume(self, agvId):
        self.server.resume_agv(int(agvId))
        return JSONResponse({'state': 'success', 'msg': f'resume agv id={agvId} success'})

    async def handle_machines(self):
        machine_list = self.server.get_machines()
        return JSONResponse({"machines": machine_list})

    async def handle_machine_pause(self, machineId):
        self.server.pause_machine(int(machineId))
        return JSONResponse({"machineId": machineId})

    async def handle_machine_resume(self, machineId):
        self.server.resume_machine(int(machineId))
        return JSONResponse({"machineId": machineId})

    async def handle_job_templates(self):
        job_list = self.server.get_job_templates()
        return JSONResponse({"jobs": job_list})

    async def handle_job_add(self, jobId):
        self.server.add_job(int(jobId))
        return JSONResponse({"jobId": jobId})

    async def handle_jobs_progress(self):
        job_progress_list = self.server.get_jobs_progress()
        return JSONResponse({"jobs": job_progress_list})

    async def handle_yaml_upload(self, config_name: str, file: UploadFile = File(...)):
        file_service.save_file(config_name, file)
        return JSONResponse({
            "success": True
        })

    async def handle_template_download(self):
        # 生成 zip 压缩包
        zip_path = os.path.join(file_service.get_config_dir(), "template_config_set.zip")
        # 返回压缩包
        return FileResponse(
            path=zip_path,
            filename="template_config_set.zip",
            media_type="application/zip"
        )

    async def handle_log_download(self, request: Request):
        body = await request.json()
        file_type = body.get("file_type")
        log_path = ""
        file_name = ""
        if file_type == "backend":
            log_path = file_service.get_log(config.BACKEND_LOG_DIR)
            file_name = log_path.split("\\")[-1]
        elif file_type == "system":
            log_path = file_service.get_log(config.SYSTEM_LOG_DIR)
            file_name = log_path.split("\\")[-1]
        return FileResponse(
            path=log_path,
            filename=file_name,
            media_type="text/plain"
        )

    async def handle_map_display(self):
        image_bytes = self.server.get_map_current()
        if image_bytes == b'':
            LOGGER.warning("No Image Available.")
        return StreamingResponse(image_bytes, media_type="image/png")

    async def handle_map_render(self, request: Request):
        body = await request.json()
        self.server.render_map(body.get("target_factory"))
        return JSONResponse({
            "success": True
        })

    async def handle_file_list(self):
        # 返回图片
        config_list = file_service.get_config_list()
        factory_list = []
        for config_name in config_list:
            data = {
                'id': config_name
            }
            factory_list.append(data)
        return JSONResponse({
            "factory_list": factory_list,
            "success": True
        })

    async def handle_cases_image(self, map: str):
        # 获取案例图片
        if map == "map1":
            image_path = os.path.join(file_service.get_config_dir(), 'map1.png')
        elif map == "map2":
            image_path = os.path.join(file_service.get_config_dir(), 'map2.png')
        else:
            return Response(content="Image file not found.", media_type="text/plain", status_code=404)

        # 以二进制模式打开图片文件
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()

        return Response(content=image_bytes, media_type="image/png")

    async def handle_cases_config(self, type: str):
        # 获取案例配置
        if type == "custom_config_1":
            file_name = "pipeline_config_set.zip"
        elif type == "custom_config_2":
            file_name = "template_config_set.zip"
        else:
            return Response(content="Config file not found.", media_type="text/plain", status_code=404)

        # 生成 zip 压缩包
        zip_path = os.path.join(file_service.get_config_dir(), file_name)
        # 返回压缩包
        return FileResponse(
            path=zip_path,
            filename=file_name,
            media_type="application/zip"
        )

    async def handle_map_render(self, request: Request):
        body = await request.json()
        self.server.render_map(body.get("target_factory"))
        return JSONResponse({
            "success": True
        })

    async def set_agent(self, request: Request):
        body = await request.json()
        self.server.set_agent(body.get('Agent'))
        return JSONResponse({
            "success": True
        })

    async def get_agent_list(self):
        agent_list = agent_service.get_agent_list()
        return JSONResponse({
            "success": True,
            "agent_list": agent_list,
        })

    # todo
    async def get_agv_indicator(self):
        """
        Monitor类的函数,只会获取回调获得的指标.SSE 推流接口
        """
        return StreamingResponse(monitor_service.get_agv_indicator(), media_type="text/event-stream")

    async def get_machine_indicator(self):
        return StreamingResponse(monitor_service.get_machine_indicator(), media_type="text/event-stream")

    async def get_job_indicator(self):
        return StreamingResponse(monitor_service.get_job_indicator(), media_type="text/event-stream")

    async def get_system_indicator(self):
        return StreamingResponse(monitor_service.get_system_indicator(), media_type="text/event-stream")

    async def get_total_indicator(self):
        return StreamingResponse(monitor_service.event_generator(), media_type="text/event-stream")
