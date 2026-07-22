"""模块12 FastAPI 主应用 — 电商智能客服 RAG API

启动:
    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

端点:
    POST /api/query          语义检索
    POST /api/upload         文件路径上传
    POST /api/upload/file    文件流上传
    DELETE /api/documents/{source_file}  删除文档
    GET  /api/stats          Collection 统计
    GET  /api/health         健康检查
    GET  /docs               Swagger UI
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import chat, query, stats, stream, upload
from src.config import settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""

    app = FastAPI(
        title="电商智能客服 RAG API",
        description=(
            "基于 Milvus + DashScope 的电商知识库检索服务。\n\n"
            "核心能力:\n"
            "- Hybrid Search (BM25 + 稠密向量)\n"
            "- Qwen3-VL-Reranker 重排序\n"
            "- 多格式文档摄入 (PDF/Office/图片/网页/FAQ)"
        ),
        version="0.4.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 注册路由 ──
    app.include_router(query.router)
    app.include_router(upload.router)
    app.include_router(stats.router)
    app.include_router(chat.router)
    app.include_router(stream.router)

    # ── 根路由 ──

    @app.get("/")
    async def root():
        return {
            "service": "电商智能客服 RAG",
            "version": "0.4.0",
            "docs": "/docs",
        }

    return app


app = create_app()
