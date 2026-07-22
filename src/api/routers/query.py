"""模块12 查询路由 — POST /api/query"""

import logging

from fastapi import APIRouter, Depends

from src.api.deps import get_retriever
from src.api.models import QueryRequest, QueryResponse, SearchResultItem
from src.embedding.retriever import Retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["查询"])


@router.post("/query", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    retriever: Retriever = Depends(get_retriever),
) -> QueryResponse:
    """语义检索 — Hybrid Search + Reranker

    流程: query → Embedder → Milvus Hybrid Search → (可选) Reranker → 返回
    """
    response = retriever.search(
        query=req.query,
        top_k=req.top_k,
        use_hybrid=req.use_hybrid,
        use_rerank=req.use_reranker,
        filter_by_doc_type=req.filter_doc_type,
        filter_by_source=req.filter_source,
        threshold=req.threshold,
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
