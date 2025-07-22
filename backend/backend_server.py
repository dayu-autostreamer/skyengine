import os

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse, FileResponse

from fastapi.middleware.cors import CORSMiddleware

from core.lib.network import NetworkAPIMethod, NetworkAPIPath

from backend_core import BackendCore

# service引入
from service import file_service


class BackendServer:
    def __init__(self):
        self.server = BackendCore()

        # 初始化 FastAPI 实例
        handler = APIHandler()

        self.app = FastAPI(routes=[
            # 测试连通性
            APIRoute(NetworkAPIPath.TEST,
                     handler.just_test,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.TEST]),

            # 工厂控制
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
            APIRoute(NetworkAPIPath.JOBS,
                     handler.handle_jobs,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.JOBS]),

            APIRoute(NetworkAPIPath.JOB_ADD,
                     handler.handle_job_add,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.JOB_ADD]),

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
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.STANDARD_GET]),

            # 下载日志
            APIRoute(NetworkAPIPath.LOG_DOWNLOAD,
                     handler.handle_log_download,
                     response_class=JSONResponse,
                     methods=[NetworkAPIMethod.LOG_DOWNLOAD]),

        ], log_level='trace', timeout=6000)

        self.app.add_middleware(
            CORSMiddleware, allow_origins=["*"], allow_credentials=True,
            allow_methods=["*"], allow_headers=["*"],
        )


class APIHandler:
    async def just_test(self):
        return JSONResponse({"just_test": True})

    async def handle_factory_start(self):
        return JSONResponse({"action": "start"})

    async def handle_factory_pause(self):
        return JSONResponse({"action": "pause"})

    async def handle_factory_reset(self):
        return JSONResponse({"action": "reset"})

    async def handle_factory_speed(self, speedLevel: int):
        return JSONResponse({"speedLevel": speedLevel})

    async def handle_agvs(self):
        return JSONResponse({"agvs": [{"id": "1"}, {"id": "2"}]})

    async def handle_agv_pause(self, agvId):
        return JSONResponse({"agvId": agvId})

    async def handle_agv_resume(self, agvId):
        return JSONResponse({"agvId": agvId})

    async def handle_machines(self):
        return JSONResponse({"machines": [{"id": "1"}, {"id": "2"}]})

    async def handle_machine_pause(self, machineId):
        return JSONResponse({"machineId": machineId})

    async def handle_machine_resume(self, machineId):
        return JSONResponse({"machineId": machineId})

    async def handle_jobs(self):
        return JSONResponse({"jobs": [{"id": "1"}, {"id": "2"}]})

    async def handle_job_add(self, jobId):
        return JSONResponse({"jobId": jobId})

    async def handle_jobs_progress(self):
        return JSONResponse({
            "jobs": [
                {"id": "1", "status": "STARTED", "progress": 75},
                {"id": "2", "status": "FINISHED", "progress": 100},
            ]
        })

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

    async def handle_log_download(self, file):
        file_service.get_log()
        return JSONResponse({
            "success": True
        })
