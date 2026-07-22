"""模块12 统计路由 — GET /api/stats, GET /api/health, GET /api/cache/stats"""

from fastapi import APIRouter, Depends

from src.api.deps import get_retriever, get_store
from src.api.models import HealthResponse, StatsResponse
from src.config import settings
from src.embedding.milvus_store import MilvusStore
from src.embedding.retriever import Retriever
from src.engineering import get_cache

router = APIRouter(prefix="/api", tags=["监控"])


@router.get("/stats", response_model=StatsResponse)
async def stats(
    store: MilvusStore = Depends(get_store),
) -> StatsResponse:
    """Milvus Collection 统计信息"""
    info = store.stats()
    return StatsResponse(
        exists=info.get("exists", False),
        collection_name=info.get("collection_name", settings.milvus_collection),
        total_vectors=info.get("total_vectors", 0),
        dimension=settings.milvus_dim,
        model_name=settings.embedding_model,
    )


@router.get("/health", response_model=HealthResponse)
async def health(
    retriever: Retriever = Depends(get_retriever),
) -> HealthResponse:
    """服务健康检查 — 测试 Embedder / Milvus / Reranker 连通性"""
    result = retriever.health_check()

    overall = "ok"
    if result.get("milvus") != "ok":
        overall = "unhealthy"
    elif result.get("search_test", "").startswith("failed"):
        overall = "degraded"

    return HealthResponse(
        status=overall,
        milvus=result.get("milvus", "unknown"),
        embedder=result.get("embedder", "unknown"),
        reranker=result.get("reranker", "unknown"),
        collection=result.get("collection", {}),
    )


@router.get("/cache/stats")
async def cache_stats() -> dict:
    """缓存统计信息"""
    cache = get_cache()
    return cache.stats()


@router.delete("/cache")
async def clear_cache() -> dict:
    """清空所有缓存"""
    cache = get_cache()
    cache.clear()
    return {"status": "ok", "message": "缓存已清空"}
