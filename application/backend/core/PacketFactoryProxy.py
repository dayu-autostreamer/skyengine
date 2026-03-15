import os
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, Body, Request
from starlette.responses import JSONResponse, FileResponse, StreamingResponse

from application.backend.core.BaseFactoryProxy import BaseFactoryProxy
from application.backend.core.RouteRegistry import RouteRegistry
# 导入后端服务
from application.backend.packet_factory.backend_server import APIHandler
from application.backend.packet_factory.backend_core import BackendCore
from application.backend.packet_factory.service import file_service


class PacketFactoryProxy(BaseFactoryProxy):
    """
    PacketFactory 代理，整合 BaseFactoryProxy 生命周期 + BackendCore 业务逻辑
    """
    
    def __init__(self):
        super().__init__()
        # 持有 APIHandler 实例（包含所有路由处理函数）
        self._api_handler: Optional[APIHandler] = None
        # 持有 BackendCore 实例
        self._backend_core: Optional[BackendCore] = None
        # 标记路由是否已注册
        self._routes_registered: bool = False
    
    def _ensure_backend(self):
        """确保 BackendCore 已初始化"""
        if self._backend_core is None:
            self._backend_core = BackendCore()
            self._api_handler = APIHandler()
    
    def _register_backend_routes(self):
        """注册后端路由到注册表"""
        if self._routes_registered or self._api_handler is None:
            return
        
        handler = self._api_handler
        
        # ========== 工厂控制路由 ==========
        @RouteRegistry.register_route("/factory/alive", method="GET")
        async def api_factory_alive():
            is_alive = self._backend_core.is_factory_alive()
            return JSONResponse({"is_alive": is_alive})
        
        @RouteRegistry.register_route("/factory/start", method="POST")
        async def api_factory_start():
            self._backend_core.factory_start()
            return JSONResponse({"action": "start"})
        
        @RouteRegistry.register_route("/factory/pause", method="POST")
        async def api_factory_pause():
            self._backend_core.factory_pause()
            return JSONResponse({"action": "pause"})
        
        @RouteRegistry.register_route("/factory/reset", method="POST")
        async def api_factory_reset():
            self._backend_core.factory_reset()
            return JSONResponse({"action": "reset"})
        
        @RouteRegistry.register_route("/factory/speed", method="POST")
        async def api_factory_speed(data: dict):
            speedLevel = data.get("speedLevel", 3)
            self._backend_core.change_factory_speed(speedLevel)
            return JSONResponse({
                'state': 'success', 
                'msg': f'change factory speed={speedLevel} success'
            })
        
        # ========== AGV 控制路由 ==========
        @RouteRegistry.register_route("/agvs", method="GET")
        async def api_agvs():
            agv_list = self._backend_core.get_agvs()
            return JSONResponse({"agvs": agv_list})
        
        @RouteRegistry.register_route("/agv/pause/{agvId}", method="POST")
        async def api_agv_pause(agvId: int):
            self._backend_core.pause_agv(int(agvId))
            return JSONResponse({
                'state': 'success', 
                'msg': f'pause agv id={agvId} success'
            })
        
        @RouteRegistry.register_route("/agv/resume/{agvId}", method="POST")
        async def api_agv_resume(agvId: int):
            self._backend_core.resume_agv(int(agvId))
            return JSONResponse({
                'state': 'success', 
                'msg': f'resume agv id={agvId} success'
            })
        
        # ========== 机器控制路由 ==========
        @RouteRegistry.register_route("/machines", method="GET")
        async def api_machines():
            machine_list = self._backend_core.get_machines()
            return JSONResponse({"machines": machine_list})
        
        @RouteRegistry.register_route("/machine/pause/{machineId}", method="POST")
        async def api_machine_pause(machineId: int):
            self._backend_core.pause_machine(int(machineId))
            return JSONResponse({"machineId": machineId})
        
        @RouteRegistry.register_route("/machine/resume/{machineId}", method="POST")
        async def api_machine_resume(machineId: int):
            self._backend_core.resume_machine(int(machineId))
            return JSONResponse({"machineId": machineId})
        
        # ========== Job 控制路由 ==========
        @RouteRegistry.register_route("/jobs", method="GET")
        async def api_jobs():
            job_list = self._backend_core.get_job_templates()
            return JSONResponse({"jobs": job_list})
        
        @RouteRegistry.register_route("/job/add/{jobId}", method="POST")
        async def api_job_add(jobId: int):
            self._backend_core.add_job(int(jobId))
            return JSONResponse({"jobId": jobId})
        
        @RouteRegistry.register_route("/jobs/progress", method="GET")
        async def api_jobs_progress():
            job_progress_list = self._backend_core.get_jobs_progress()
            return JSONResponse({"jobs": job_progress_list})

        @RouteRegistry.register_route("/{config_name}/yaml/upload", method="POST")
        async def api_yaml_upload(config_name: str, file: UploadFile = File(...)):
            content = await file.read()
            file_service.save_file(config_name, file)
            return JSONResponse({"state": "success", "msg": f"Config {config_name} uploaded successfully"})
        
        # ========== 配置上传路由 ==========
        @RouteRegistry.register_route("/standard/get", method="GET")
        async def api_standard_get():
            zip_path = os.path.join(file_service.get_config_set_dir(), "template_config_set.zip")
            return FileResponse(
                path=zip_path,
                filename="template_config_set.zip",
                media_type="application/zip"
            )
        
        # ========== 日志下载路由 ==========
        @RouteRegistry.register_route("/log/download", method="POST")
        async def api_log_download(request:Request):
            body = await request.json()
            file_type = body.get("file_type")
            log_path = ""
            file_name = ""
            if file_type == "backend":
                log_path = file_service.get_log(file_service.get_backend_log_dir())
                print(log_path)
                file_name = log_path.split("\\")[-1]
            elif file_type == "system":
                log_path = file_service.get_log(file_service.get_system_log_dir())
                file_name = log_path.split("\\")[-1]
            return FileResponse(
                path=log_path, 
                filename=file_name, 
                media_type="text/plain"
            )
        
        # ========== 地图路由 ==========
        @RouteRegistry.register_route("/map/update", method="GET")
        async def api_map_update():
            image_bytes = self._backend_core.get_map_current()
            if image_bytes == b'':
                from executor.packet_factory.logger.logger import BACKEND_LOGGER as LOGGER
                LOGGER.warning("No Image Available.")
            return StreamingResponse(image_bytes, media_type="image/png")
        
        @RouteRegistry.register_route("/map/render", method="POST")
        async def api_map_render(request: Request):
            body = await request.json()
            print(body)
            self._backend_core.render_map(body.get("target_factory"))
            return JSONResponse({"success": True})
        
        @RouteRegistry.register_route("/factory/list", method="GET")
        async def api_factory_list():
            config_list = file_service.get_config_list()
            factory_list = [{"id": config_name} for config_name in config_list]
            return JSONResponse({"factory_list": factory_list, "success": True})
        
        self._routes_registered = True
        print(f"✅ PacketFactoryProxy 路由已注册，共 {len(RouteRegistry.get_routes())} 条")
    
    # ========== BaseFactoryProxy 接口实现 ==========
    
    async def initialize(self):
        """初始化工厂"""
        self._ensure_backend()
        self._register_backend_routes()

    async def cleanup(self):
        """清理工厂"""
        # todo: 停止后端核心线程池等资源
        pass
    
    async def start(self):
        """启动工厂"""
        self._ensure_backend()
        self._backend_core.factory_start()
        await super().start()
    
    async def pause(self):
        """暂停工厂"""
        self._ensure_backend()
        self._backend_core.factory_pause()
        await super().pause()
    
    async def reset(self):
        """重置工厂"""
        self._ensure_backend()
        self._backend_core.factory_reset()
        await super().reset()
    
    def is_running(self) -> bool:
        """检查是否运行中"""
        self._ensure_backend()
        return self._backend_core.is_factory_alive()
    
    # ========== 代理方法（供 server.py 直接调用） ==========
    
    def get_agvs(self) -> List[dict]:
        self._ensure_backend()
        return self._backend_core.get_agvs()
    
    def get_machines(self) -> List[dict]:
        self._ensure_backend()
        return self._backend_core.get_machines()
    
    def get_job_templates(self) -> List[dict]:
        self._ensure_backend()
        return self._backend_core.get_job_templates()
    
    def add_job(self, job_id: int):
        self._ensure_backend()
        self._backend_core.add_job(job_id)
    
    def get_jobs_progress(self) -> List[dict]:
        self._ensure_backend()
        return self._backend_core.get_jobs_progress()
    
    def change_factory_speed(self, speed_level: int):
        self._ensure_backend()
        self._backend_core.change_factory_speed(speed_level)
    
    def get_map_current(self) -> bytes:
        self._ensure_backend()
        return self._backend_core.get_map_current()
    
    def render_map(self, target_factory: str):
        self._ensure_backend()
        self._backend_core.render_map(target_factory)
    
    def is_factory_alive(self) -> bool:
        self._ensure_backend()
        return self._backend_core.is_factory_alive()