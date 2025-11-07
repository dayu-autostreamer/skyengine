# backend/Dockerfile
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 基础构建依赖（如需编译 C++/扩展）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake g++ git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 可选：先拷贝依赖声明，提高缓存命中
# 如无 requirements.txt，可创建；或直接 pip install 主要依赖
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# 代码
COPY . /app

# 暴露后端端口（与 GUNICORN_PORT 一致）
EXPOSE 8000

# 缺省环境变量（可在 docker-compose 覆盖）
ENV SERVER_TYPE=grid \
    GUNICORN_PORT=8000

# 使用 Uvicorn 启动（main.py 内已经 uvicorn.run，可直接 python 运行）
CMD ["python", "backend/main.py"]