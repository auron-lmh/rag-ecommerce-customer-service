"""模块3 检索接口 — Hybrid Search (稠密 + BM25 稀疏) + Reranker 重排序

使用:
    retriever = Retriever()
    results = retriever.search("怎么退货?")                    # hybrid + rerank
    results = retriever.search("退款", use_rerank=False)       # 纯 hybrid
    results = retriever.search("退款", use_hybrid=False)       # 纯稠密
"""

import logging
from typing import Optional

from src.config import settings

from .embedder import Embedder, get_embedder
from .milvus_store import MilvusStore
from .models import SearchResponse

logger = logging.getLogger(__name__)


class Retriever:
    """Hybrid 检索器 — Embedder + MilvusStore + Reranker

    默认流程:
      1. Embedder 将 query → 稠密向量
      2. Milvus Hybrid Search (BM25 + Dense + WeightedRanker)
      3. (可选) Reranker 重排序
    """

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        store: Optional[MilvusStore] = None,
    ):
        self.embedder = embedder or get_embedder()
        self.store = store or MilvusStore()
        self._reranker = None  # 懒加载

    @property
    def reranker(self):
        if self._reranker is None and settings.reranker_enabled:
            from src.retrieval.reranker import get_reranker

            self._reranker = get_reranker()
        return self._reranker

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_hybrid: bool = True,
        use_rerank: Optional[bool] = None,
        filter_by_doc_type: Optional[str] = None,
        filter_by_source: Optional[str] = None,
        threshold: Optional[float] = None,
        sparse_weight: float = 0.5,
        dense_weight: float = 0.5,
    ) -> SearchResponse:
        """检索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数
            use_hybrid: 是否用 Hybrid Search (BM25+稠密), False=纯稠密
            use_rerank: 是否启用重排序 (默认跟随 settings.reranker_enabled)
            filter_by_doc_type: 按文档类型过滤
            filter_by_source: 按来源文件过滤
            threshold: 最低相似度阈值
            sparse_weight: BM25 权重 (默认 0.5)
            dense_weight: 稠密向量权重 (默认 0.5)
        """
        if threshold is None:
            threshold = settings.retrieval_similarity_threshold
        if use_rerank is None:
            use_rerank = settings.reranker_enabled

        # ── 构建过滤表达式 ──
        filter_parts = []
        if filter_by_doc_type:
            filter_parts.append(f'doc_type == "{filter_by_doc_type}"')
        if filter_by_source:
            filter_parts.append(f'source_file == "{filter_by_source}"')
        filter_expr = " && ".join(filter_parts) if filter_parts else None

        # ── 向量化 ──
        query_vector = self.embedder.embed_query(query)

        # ── 检索 (Hybrid 召回阶段需要更多候选供 Reranker 筛选) ──
        recall_k = max(top_k, settings.retrieval_dense_top_k) if use_rerank else top_k

        if use_hybrid:
            response = self.store.hybrid_search(
                query_vector=query_vector.tolist(),
                query_text=query,
                top_k=recall_k,
                filter_expr=filter_expr,
                threshold=threshold,
                sparse_weight=sparse_weight,
                dense_weight=dense_weight,
            )
        else:
            response = self.store.dense_search(
                query_vector=query_vector.tolist(),
                top_k=recall_k,
                filter_expr=filter_expr,
                threshold=threshold,
            )

        response.query = query

        # ── 重排序 ──
        if use_rerank and self.reranker and response.results:
            try:
                response = self.reranker.rerank_search_response(
                    query=query,
                    search_response=response,
                    top_n=top_k,
                )
                logger.debug("重排序完成: %d → %d", recall_k, response.total_found)
            except Exception as e:
                logger.warning("重排序失败，降级使用原始结果: %s", e)
                # 截断回 top_k
                response = SearchResponse(
                    query=query,
                    results=response.results[:top_k],
                    total_found=min(response.total_found, top_k),
                    elapsed_ms=response.elapsed_ms,
                    threshold=response.threshold,
                )

        return response

    def search_batch(
        self,
        queries: list[str],
        top_k: int = 5,
        use_hybrid: bool = True,
        use_rerank: Optional[bool] = None,
        threshold: Optional[float] = None,
    ) -> list[SearchResponse]:
        """批量检索"""
        if threshold is None:
            threshold = settings.retrieval_similarity_threshold
        if use_rerank is None:
            use_rerank = settings.reranker_enabled

        query_vectors = self.embedder.embed_queries(queries)
        responses = []
        for i, q in enumerate(queries):
            if use_hybrid:
                r = self.store.hybrid_search(
                    query_vector=query_vectors[i].tolist(),
                    query_text=q,
                    top_k=top_k,
                    threshold=threshold,
                )
            else:
                r = self.store.dense_search(
                    query_vector=query_vectors[i].tolist(),
                    top_k=top_k,
                    threshold=threshold,
                )
            r.query = q

            # 重排序
            if use_rerank and self.reranker and r.results:
                try:
                    r = self.reranker.rerank_search_response(q, r, top_n=top_k)
                except Exception as e:
                    logger.warning("批量重排序失败 [%d]: %s", i, e)

            responses.append(r)
        return responses

    def health_check(self) -> dict:
        result = {
            "embedder": "ok",
            "milvus": "not_ok",
            "reranker": "not_configured",
            "search_test": "skipped",
        }
        milvus_ok = self.store.health_check()
        result["milvus"] = "ok" if milvus_ok else "not_ok"

        if self.reranker:
            result["reranker"] = "configured"

        if milvus_ok:
            stats = self.store.stats()
            result["collection"] = stats
            if stats.get("total_vectors", 0) > 0:
                try:
                    test_vec = self.embedder.embed_query("健康检查")
                    r = self.store.hybrid_search(
                        query_vector=test_vec.tolist(),
                        query_text="健康检查",
                        top_k=1,
                    )
                    result["search_test"] = "ok" if r.total_found > 0 else "no_results"
                except Exception as e:
                    result["search_test"] = f"failed: {e}"
        return result
