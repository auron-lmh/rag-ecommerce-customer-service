"""模块12 统计路由 — GET /api/stats, GET /api/health, GET /api/cache/stats, GET /api/stats/daily"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.auth import CurrentUser
from src.api.deps import get_retriever, get_store, require_admin
from src.api.models import HealthResponse, StatsResponse
from src.config import settings
from src.embedding.milvus_store import MilvusStore
from src.embedding.retriever import Retriever
from src.engineering import get_cache, get_monitor

router = APIRouter(prefix="/api", tags=["监控"])


@router.get("/stats", response_model=StatsResponse)
async def stats(
    store: MilvusStore = Depends(get_store),
    admin: CurrentUser = Depends(require_admin),
) -> StatsResponse:
    """Milvus Collection 统计信息（仅管理员）"""
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
async def cache_stats(admin: CurrentUser = Depends(require_admin)) -> dict:
    """缓存统计信息（仅管理员）"""
    cache = get_cache()
    return cache.stats()


@router.delete("/cache")
async def clear_cache(admin: CurrentUser = Depends(require_admin)) -> dict:
    """清空所有缓存（仅管理员）"""
    cache = get_cache()
    cache.clear()
    return {"status": "ok", "message": "缓存已清空"}


@router.get("/stats/daily")
async def daily_stats(
    date: Optional[str] = Query(default=None, description="日期 YYYY-MM-DD"),
    admin: CurrentUser = Depends(require_admin),
) -> dict:
    """每日统计 — 查询量/成本/延迟/幻觉率/缓存命中率（仅管理员）"""
    monitor = get_monitor()
    return monitor.get_daily_stats(date)


@router.get("/stats/recent")
async def recent_queries(
    limit: int = Query(default=20, ge=1, le=100),
    admin: CurrentUser = Depends(require_admin),
) -> list[dict]:
    """最近查询记录（仅管理员）"""
    monitor = get_monitor()
    return monitor.get_recent_queries(limit)


@router.get("/stats/alerts")
async def alerts(
    date: Optional[str] = Query(default=None, description="日期 YYYY-MM-DD"),
    admin: CurrentUser = Depends(require_admin),
) -> list[dict]:
    """告警规则检查（仅管理员）"""
    monitor = get_monitor()
    return monitor.check_alerts(date)
