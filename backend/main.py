import uvicorn

from backend_server import BackendServer
from core.lib.common import Context

app = BackendServer().app

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=Context.get_parameter('GUNICORN_PORT', '8000', direct=False), log_config=None)
