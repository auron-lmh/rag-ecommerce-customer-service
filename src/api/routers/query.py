"""模块12 查询路由 — POST /api/query"""

import logging

from fastapi import APIRouter, Depends

from src.api.auth import CurrentUser
from src.api.deps import get_current_user, get_retriever
from src.api.models import QueryRequest, QueryResponse, SearchResultItem
from src.embedding.retriever import Retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["查询"])


@router.post("/query", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    retriever: Retriever = Depends(get_retriever),
    current_user: CurrentUser = Depends(get_current_user),
) -> QueryResponse:
    """语义检索 — Hybrid Search + Reranker（需要登录，按用户 access_level 过滤知识范围）

    流程: query → Embedder → Milvus Hybrid Search → (可选) Reranker → 返回
    """
    # 修复: 检索（含 embedding）放线程池执行，避免在 async 事件循环里跑同步
    # dashscope 调用，规避 uvicorn 进程 embedding 不一致的异常连接路径
    import asyncio

    response = await asyncio.to_thread(
        retriever.search,
        query=req.query,
        top_k=req.top_k,
        use_hybrid=req.use_hybrid,
        use_rerank=req.use_reranker,
        filter_by_doc_type=req.filter_doc_type,
        filter_by_source=req.filter_source,
        threshold=req.threshold,
        # 模块33: 按当前用户等级过滤（access_level <= 用户等级才可见）
        access_level=current_user.access_level,
    )

    return QueryResponse(
        query=response.query,
        results=[
            SearchResultItem(
                chunk_id=r.chunk_id,
                text=r.text,
                score=r.score,
                doc_type=r.doc_type,
                source_file=r.source_file,
                heading_path=r.heading_path,
            )
            for r in response.results
        ],
        total_found=response.total_found,
        query_time_ms=response.elapsed_ms,
        threshold=response.threshold,
    )
