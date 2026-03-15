"""
路由注册表：用于统一管理 FastAPI 路由
"""
from typing import Callable, Dict, List, Any
from fastapi import FastAPI
from fastapi.routing import APIRoute


class RouteRegistry:
    """全局路由注册表"""
    
    _routes: Dict[str, dict] = {}
    
    @classmethod
    def register_route(
        cls, 
        path: str, 
        method: str = "GET",
        response_class: Any = None,
        **kwargs
    ):
        """
        路由注册装饰器
        
        Args:
            path: 路由路径
            method: HTTP 方法 (GET, POST, PUT, DELETE 等)
            response_class: 响应类型 (JSONResponse, FileResponse, StreamingResponse 等)
            **kwargs: 其他 FastAPI 路由参数
        """
        def decorator(func: Callable):
            cls._routes[path] = {
                "path": path,
                "method": method,
                "func": func,
                "name": func.__name__,
                "response_class": response_class,
                "kwargs": kwargs
            }
            return func
        return decorator
    
    @classmethod
    def get_routes(cls) -> Dict[str, dict]:
        """获取所有注册的路由"""
        return cls._routes
    
    @classmethod
    def clear_routes(cls):
        """清空所有路由"""
        cls._routes = {}
    
    @classmethod
    def register_to_app(cls, app: FastAPI, prefix: str = ""):
        """
        将注册的路由添加到 FastAPI 应用
        
        Args:
            app: FastAPI 实例
            prefix: 路由前缀 (如 "/api")
        """
        for path, route_info in cls._routes.items():
            full_path = f"{prefix}{path}"
            
            # 创建 APIRoute
            route = APIRoute(
                path=full_path,
                endpoint=route_info["func"],
                methods=[route_info["method"]],
                response_class=route_info.get("response_class"),
                **route_info.get("kwargs", {})
            )
            
            app.router.routes.append(route)
            print(f"✅ 注册路由：{route_info['method']} {full_path}")