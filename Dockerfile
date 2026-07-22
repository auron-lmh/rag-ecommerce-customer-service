# 电商智能客服 RAG 系统 - Dockerfile
# 构建: docker build -t rag-api .
# 运行: docker run -p 8000:8000 rag-api

FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Poetry
RUN pip install poetry

# 复制依赖文件
COPY pyproject.toml poetry.lock ./

# 安装依赖（不创建虚拟环境，直接安装到系统）
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction

# 复制应用代码
COPY src/ ./src/
COPY .env.example .env

# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
