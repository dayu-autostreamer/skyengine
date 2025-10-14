import os
import uvicorn

from backend.core.lib.common import Context


def load_server():
    """
    根据环境变量 SERVER_TYPE 选择不同的 server 实例。
    默认使用 BackendServer。
    """
    server_type = os.environ.get("SERVER_TYPE", "packet").lower()

    if server_type == "packet":
        # 不同 server 类
        from backend.server.packet_server import BackendServer as PacketServer
        return PacketServer()
    elif server_type == "grid":
        from backend.server.grid_server import BackendServer as GridServer
        return GridServer()
    else:
        raise ValueError(f"Unsupported SERVER_TYPE: {server_type}")


if __name__ == '__main__':
    # 获取 server 实例
    server_instance = load_server()
    app = server_instance.app

    # 端口优先读取环境变量，fallback 使用 Context 配置或默认 8000
    port = int(os.environ.get('GUNICORN_PORT', Context.get_parameter('GUNICORN_PORT', '8000', direct=False)))

    # uvicorn 启动
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=port,
        log_config=None,
        reload=os.environ.get("DEV_MODE", "0") == "1"  # DEV_MODE=1 时启用热重载
    )
