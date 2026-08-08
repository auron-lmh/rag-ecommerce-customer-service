"""模块12 FastAPI 主应用 — 电商智能客服 RAG API

启动:
    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

端点:
    POST /api/auth/login     登录（JWT，模块13）
    POST /api/query          语义检索（需登录，按 access_level 过滤）
    POST /api/chat           智能对话（需登录）
    POST /api/chat/stream    流式对话（需登录）
    POST /api/upload         文件路径上传（管理员）
    POST /api/upload/file    文件流上传（管理员）
    DELETE /api/documents/{source_file}  删除文档（管理员）
    GET  /api/stats          Collection 统计（管理员）
    GET  /api/health         健康检查（公开）
    GET  /docs               Swagger UI
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import auth, chat, evaluate, query, stats, stream, upload
from src.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期 — 启动时执行轻量迁移

    模块13: 已有 Milvus collection 自动补 access_level 字段（INT8 + INVERTED 索引）。
    Milvus 不可达/无 collection 时静默跳过（连接被拒绝快速失败，不阻塞启动）。
    """
    try:
        from src.embedding.milvus_store import MilvusStore

        result = MilvusStore().ensure_access_level_field()
        logger.info("Milvus access_level 字段迁移: %s", result)
    except Exception as e:
        logger.warning("Milvus access_level 字段迁移跳过: %s", e)
    yield


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""

    app = FastAPI(
        title="电商智能客服 RAG API",
        description=(
            "基于 Milvus + DashScope 的电商知识库检索服务。\n\n"
            "核心能力:\n"
            "- Hybrid Search (BM25 + 稠密向量)\n"
            "- Qwen3-VL-Reranker 重排序\n"
            "- 多格式文档摄入 (PDF/Office/图片/网页/FAQ)\n"
            "- 模块13: JWT 鉴权 + 内容级权限隔离 (access_level)"
        ),
        version="0.4.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──
    # 模块13: 收紧到白名单（"*" + credentials 是无效组合，浏览器会拒收凭据）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 注册路由 ──
    app.include_router(auth.router)
    app.include_router(query.router)
    app.include_router(upload.router)
    app.include_router(stats.router)
    app.include_router(chat.router)
    app.include_router(stream.router)
    app.include_router(evaluate.router)

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
