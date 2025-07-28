import os

from fastapi import FastAPI, File, UploadFile, Form, Body, Request
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse, FileResponse, StreamingResponse

from fastapi.middleware.cors import CORSMiddleware

from core.lib.network import NetworkAPIMethod, NetworkAPIPath

from backend_core import BackendCore

# service引入
from service import file_service


class BackendServer:
    def __init__(self):
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

        ], log_level='trace', timeout=6000)

        self.app.add_middleware(
            CORSMiddleware, allow_origins=["*"], allow_credentials=True,
            allow_methods=["*"], allow_headers=["*"],
        )


class APIHandler:
    def __init__(self):
        self.server = BackendCore()

    async def just_test(self):
        return JSONResponse({"just_test": True})

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

    async def handle_jobs(self):
        job_list = self.server.get_jobs()
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
        file_type=body.get("file_type")
        print(file_type)
        log_path = ""
        file_name = ""
        if file_type == "backend":
            pass
        elif file_type == "system":
            pass

        return FileResponse(
            path=log_path,
            filename="factory_log_output.log",
            media_type="text/plain"
        )

    async def handle_map_display(self):
        # 返回图片
        image_bytes = self.server.get_map_current()
        return StreamingResponse(image_bytes, media_type="image/png")

    async def handle_map_render(self):
        self.server.render_map()
        return JSONResponse({
            "success": True
        })
