# 电商智能客服 RAG 系统 - Dockerfile
# 使用 pip + requirements.txt（避免 Poetry 依赖问题）
# 构建: docker build -t rag-api .
# 运行: docker run -p 8000:8000 rag-api

FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 使用国内 PyPI 镜像源 (阿里云，比清华更全)
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip config set global.trusted-host mirrors.aliyun.com

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ ./src/
COPY .env.example .env

# 创建数据和日志目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8000

# 启动命令
# --workers 1: 多 worker 会 fork 子进程，实测导致 DashScope embedding 跨进程不一致
# （fork worker 与单进程产出不同向量，检索全挂）。单 worker 保证确定性。
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
