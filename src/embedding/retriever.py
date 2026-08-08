"""模块3 检索接口 — Hybrid Search (稠密 + BM25 稀疏) + Reranker 重排序

使用:
    retriever = Retriever()
    results = retriever.search("怎么退货?")                    # hybrid + rerank
    results = retriever.search("退款", use_rerank=False)       # 纯 hybrid
    results = retriever.search("退款", use_hybrid=False)       # 纯稠密
"""

import logging
from typing import Optional

from src.access import build_access_filter_expr
from src.config import settings

from .embedder import Embedder, get_embedder
from .milvus_store import MilvusStore
from .models import SearchResponse, SearchResult

logger = logging.getLogger(__name__)


def _get_cache():
    """延迟导入缓存模块"""
    from src.engineering import get_cache

    return get_cache()


def _search_response_to_dict(response: SearchResponse) -> dict:
    """SearchResponse → dict（Redis 缓存需 JSON 序列化）

    修复: SearchResponse 是 dataclass 不可 json.dumps，生产 Redis 缓存会失败。
    """
    return {
        "query": response.query,
        "results": [
            {
                "chunk_id": r.chunk_id,
                "text": r.text,
                "score": r.score,
                "doc_type": r.doc_type,
                "source_file": r.source_file,
                "page_number": r.page_number,
                "heading_path": r.heading_path,
                "metadata": r.metadata,
            }
            for r in response.results
        ],
        "total_found": response.total_found,
        "elapsed_ms": response.elapsed_ms,
        "threshold": response.threshold,
    }


def _dict_to_search_response(data: dict) -> SearchResponse:
    """dict → SearchResponse（缓存反序列化）"""
    return SearchResponse(
        query=data.get("query", ""),
        results=[SearchResult(**r) for r in data.get("results", [])],
        total_found=data.get("total_found", 0),
        elapsed_ms=data.get("elapsed_ms", 0),
        threshold=data.get("threshold", 0),
    )


def _merge_results(results_a: list, results_b: list) -> list:
    """双路召回合并去重 — 按 chunk_id 保留最高分，按分数降序

    作用: 原始问题（保真度）+ 改写后问题（专业术语）两路召回合并，
    同一文档只保留相似度最高的一条，避免重复/低质量文档淹没高质量结果。
    """
    best: dict[str, SearchResult] = {}
    for r in results_a + results_b:
        if r.chunk_id not in best or r.score > best[r.chunk_id].score:
            best[r.chunk_id] = r
    return sorted(best.values(), key=lambda r: r.score, reverse=True)


def _filter_by_effectiveness(results: list, today: str | None = None) -> list:
    """过滤已过期/未生效的文档（政策时效元数据，改进4）

    chunk metadata 中的 effective_from / effective_to（ISO 日期字符串）
    决定文档生效窗口:
      - effective_from 存在且 > today → 尚未生效，过滤
      - effective_to   存在且 < today → 已过期，过滤
      - 未设置（默认）                → 永不过期，保留

    背景: 电商政策频繁变（大促/618/双11），历史政策必须被过滤，
    否则用户问"最新优惠"会返回已结束活动。
    （注: 检索缓存 TTL 内可能出现 ≤1h 时效滞后；生产可改为 Milvus 标量字段过滤）
    """
    if not results:
        return results
    if today is None:
        from datetime import date

        today = date.today().isoformat()

    valid = []
    for r in results:
        meta = r.metadata or {}
        eff_from = meta.get("effective_from") or ""
        eff_to = meta.get("effective_to") or ""
        if eff_from and eff_from > today:
            continue  # 尚未生效
        if eff_to and eff_to < today:
            continue  # 已过期
        valid.append(r)
    return valid


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
        sparse_weight: float = 0.3,  # BM25 关键词权重 (辅助)
        dense_weight: float = 0.7,  # 语义向量权重 (主力)
        access_level: str = "public",  # 模块13 内容权限: 用户等级, fail-safe 最低权限
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
            sparse_weight: BM25 关键词权重 (默认 0.3)
            dense_weight: 稠密向量权重 (默认 0.7)
            access_level: 内容权限等级 public/member/vip。漏传默认 public(最低)=只返回公开内容,
                         永不泄漏。★必须拼进缓存 key,否则高权限用户缓存被低权限用户命中=直接泄漏。
        """
        if threshold is None:
            threshold = settings.retrieval_similarity_threshold
        if use_rerank is None:
            use_rerank = settings.reranker_enabled

        # ── 查询缓存 ──
        cache = _get_cache()
        # 关键修复: 缓存 Key 包含所有查询参数（含过滤条件），避免返回错误缓存
        # 模块13: 必须含 access_level —— 不同权限用户命中彼此缓存 = 越权泄漏
        cache_key = (
            f"{query}:{top_k}:{use_hybrid}:{use_rerank}:{filter_by_doc_type}:"
            f"{filter_by_source}:{threshold}:{access_level}"
        )
        cached = cache.get_query_result(cache_key)
        if cached:
            logger.debug("缓存命中: %s", query[:50])
            return _dict_to_search_response(cached)

        # ── 构建过滤表达式 ──
        filter_parts = []
        if filter_by_doc_type:
            # 修复: 转义双引号，防止 Milvus 表达式注入
            safe_doc_type = filter_by_doc_type.replace('"', '\\"')
            filter_parts.append(f'doc_type == "{safe_doc_type}"')
        if filter_by_source:
            safe_source = filter_by_source.replace('"', '\\"')
            filter_parts.append(f'source_file == "{safe_source}"')
        # 模块13 内容权限: 用户等级 >= 文档等级才可见（access_level <= {rank}）。
        # 在向量检索阶段过滤，越权内容根本进不了召回集。
        filter_parts.append(build_access_filter_expr(access_level))
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

        # 改进4: 政策时效过滤——剔除已过期/未生效文档（在重排序前，让 rerank 只处理有效文档）
        filtered_results = _filter_by_effectiveness(response.results)
        if len(filtered_results) != len(response.results):
            logger.debug(
                "时效过滤: %d → %d 条", len(response.results), len(filtered_results)
            )
            response.results = filtered_results
            response.total_found = len(filtered_results)

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

        # ── 缓存结果（存 dict，Redis 可 JSON 序列化）──
        cache.set_query_result(cache_key, _search_response_to_dict(response), ttl=3600)

        return response

    def search_dual_path(
        self,
        query: str,
        secondary_query: str,
        top_k: int = 5,
        use_rerank: bool = True,
        threshold: Optional[float] = None,
        filter_by_doc_type: Optional[str] = None,
        filter_by_source: Optional[str] = None,
        access_level: str = "public",
    ) -> SearchResponse:
        """双路召回 + 合并去重（两步检索）

        原始问题（保真度）+ 改写后问题（专业术语）分别召回，合并去重后精排。
        行业实践（两步检索）: 召回率提升约 30%，且改写偏离时原始问题兜底，
        消除"改写错就全错"风险。

        Args:
            query: 原始问题（保真兜底）
            secondary_query: 改写后问题（专业术语/指代消解）
            top_k: 最终返回数
            use_rerank: 是否 Reranker 精排
            threshold: 最低相似度阈值
            filter_by_doc_type: 按文档类型过滤
            filter_by_source: 按来源文件过滤
            access_level: 模块13 内容权限等级，透传给两路内部检索

        Returns:
            SearchResponse（合并去重后的结果）
        """
        if not secondary_query or secondary_query == query:
            return self.search(
                query=query,
                top_k=top_k,
                use_rerank=use_rerank,
                threshold=threshold,
                filter_by_doc_type=filter_by_doc_type,
                filter_by_source=filter_by_source,
                access_level=access_level,
            )

        # 召回阶段取更多候选（供合并 + 精排筛选）
        recall_k = max(top_k, settings.retrieval_dense_top_k) if use_rerank else top_k

        r1 = self.search(
            query,
            top_k=recall_k,
            use_rerank=False,
            threshold=threshold,
            filter_by_doc_type=filter_by_doc_type,
            filter_by_source=filter_by_source,
            access_level=access_level,
        )
        r2 = self.search(
            secondary_query,
            top_k=recall_k,
            use_rerank=False,
            threshold=threshold,
            filter_by_doc_type=filter_by_doc_type,
            filter_by_source=filter_by_source,
            access_level=access_level,
        )

        merged = _merge_results(r1.results, r2.results)
        response = SearchResponse(
            query=query,
            results=merged,
            total_found=len(merged),
            elapsed_ms=round(r1.elapsed_ms + r2.elapsed_ms, 1),
            threshold=r1.threshold,
        )

        # 精排（跨编码器对合并结果重排，优于单路）
        if use_rerank and self.reranker and response.results:
            try:
                response = self.reranker.rerank_search_response(
                    query=query,
                    search_response=response,
                    top_n=top_k,
                )
            except Exception as e:
                logger.warning("双路召回精排失败，降级用合并结果: %s", e)
                response.results = response.results[:top_k]
                response.total_found = len(response.results)
        else:
            response.results = response.results[:top_k]
            response.total_found = len(response.results)

        return response

    def search_batch(
        self,
        queries: list[str],
        top_k: int = 5,
        use_hybrid: bool = True,
        use_rerank: Optional[bool] = None,
        threshold: Optional[float] = None,
        access_level: str = "public",
    ) -> list[SearchResponse]:
        """批量检索"""
        if threshold is None:
            threshold = settings.retrieval_similarity_threshold
        if use_rerank is None:
            use_rerank = settings.reranker_enabled

        # 模块13: 批量检索同样必须带权限过滤，否则评估/批量场景无差别召回越权内容
        filter_expr = build_access_filter_expr(access_level)

        query_vectors = self.embedder.embed_queries(queries)
        responses = []
        for i, q in enumerate(queries):
            if use_hybrid:
                r = self.store.hybrid_search(
                    query_vector=query_vectors[i].tolist(),
                    query_text=q,
                    top_k=top_k,
                    threshold=threshold,
                    filter_expr=filter_expr,
                )
            else:
                r = self.store.dense_search(
                    query_vector=query_vectors[i].tolist(),
                    top_k=top_k,
                    threshold=threshold,
                    filter_expr=filter_expr,
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


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_retriever() -> Retriever:
    """获取 Retriever 单例"""
    return Retriever()
