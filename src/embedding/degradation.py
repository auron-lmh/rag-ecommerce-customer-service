"""模块5 多级降级策略 — 检索质量不足时的逐级降级

三级降级:
  Level 1: 原始 query → Hybrid Search → 检查最高相似度 > threshold
  Level 2: 相似度不足 → LLM 改写 query → 重新检索
  Level 3: 仍不足 → 联网搜索兜底（Tavily/Bing）
  兜底: 诚实回复 "根据已有信息无法确认"

使用:
    strategy = DegradationStrategy(retriever)
    result = strategy.search_with_degradation("怎么退货？")
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

from src.config import settings
from src.engineering.llm_client import get_llm_client

from .models import SearchResponse, SearchResult

logger = logging.getLogger(__name__)

# 降级参数
SIMILARITY_THRESHOLD = 0.7  # Level 1 最低相似度阈值
IMPROVEMENT_THRESHOLD = 0.05  # Level 2 改善幅度阈值
MAX_REWRITE_ATTEMPTS = 2  # 最大改写尝试次数

# 复杂查询判定（主动拆分子问题并行检索）
_STRONG_COMPLEX_MARKERS = [
    "对比",
    "比较",
    "哪个好",
    "哪个更好",
    "有什么区别",
    "分别",
    "以及",
]
_WEAK_COMPLEX_MARKERS = ["和", "与", "同时"]


def _is_complex_query(query: str) -> bool:
    """判断是否为复杂/复合查询（需要拆分子问题并行检索）

    强标记（对比/区别/分别/以及）命中即复杂；
    弱标记（和/与/同时）需 ≥2 个，避免"和运费"类误判。
    例: "A和B的性能参数对比" → 复杂；"怎么退货" → 不复杂。
    """
    if not query:
        return False
    strong = sum(1 for m in _STRONG_COMPLEX_MARKERS if m in query)
    weak = sum(1 for m in _WEAK_COMPLEX_MARKERS if m in query)
    return strong >= 1 or weak >= 2


@dataclass
class DegradationResult:
    """降级检索结果"""

    response: SearchResponse
    level: int  # 最终使用的降级级别 (1/2/3/4)
    method: str  # hybrid / rewritten / web_search / fallback
    original_query: str = ""
    rewritten_query: str = ""
    web_results: list[dict] = field(default_factory=list)
    degradation_reason: str = ""


class DegradationStrategy:
    """多级降级策略

    使用方式:
        strategy = DegradationStrategy(retriever)
        result = strategy.search_with_degradation("怎么退货？")
        print(result.level)  # 1=直接命中, 2=改写后命中, 3=联网搜索, 4=兜底
    """

    def __init__(self, retriever):
        self.retriever = retriever

    def search_with_degradation(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = SIMILARITY_THRESHOLD,
        use_rerank: bool = True,
        secondary_query: str | None = None,
        access_level: str = "public",
    ) -> DegradationResult:
        """带降级的检索（Level 1 支持双路召回）

        Args:
            query: 用户查询（原始问题，保真兜底）
            top_k: 返回结果数
            threshold: 最低相似度阈值
            use_rerank: 是否启用 Reranker
            secondary_query: 改写后问题（提供时 Level 1 走双路召回，
                             原始+改写并行合并去重；不提供则退化为单路）
            access_level: 模块33 内容权限等级，透传给各级检索（Level 0-3）

        Returns:
            DegradationResult
        """
        # ── Level 0: 复杂查询主动拆分子问题并行检索（面试加分项）──
        # 例: "A和B的性能参数对比" → 拆成 ["A性能", "A参数", "B性能", ...] 并行检索 → 合并
        # 行业实践（Question Decomposition for RAG）: 单查询对复合问题会"夹在概念之间"，
        # 拆分子查询并行检索 + 汇总，MRR@10 +36.7%。
        if _is_complex_query(query):
            decomposed = self._expand_and_search(
                query, top_k, access_level=access_level
            )
            if decomposed.results and self._is_sufficient(decomposed, threshold):
                if use_rerank and self.retriever.reranker:
                    try:
                        decomposed = self.retriever.reranker.rerank_search_response(
                            query=query,
                            search_response=decomposed,
                            top_n=top_k,
                        )
                    except Exception as e:
                        logger.warning("复杂查询精排失败，用合并结果: %s", e)
                logger.info(
                    "复杂查询主动分解命中: %s → %d 条",
                    query[:40],
                    len(decomposed.results),
                )
                return DegradationResult(
                    response=decomposed,
                    level=1,
                    method="decomposed",
                    original_query=query,
                )
            logger.info("复杂查询分解结果不足，继续双路召回")

        # ── Level 1: 双路召回（原始 + 改写并行合并去重）──
        if secondary_query and secondary_query != query:
            response = self.retriever.search_dual_path(
                query=query,
                secondary_query=secondary_query,
                top_k=top_k,
                use_rerank=use_rerank,
                access_level=access_level,
            )
        else:
            response = self.retriever.search(
                query=query,
                top_k=top_k,
                use_rerank=use_rerank,
                access_level=access_level,
            )

        if self._is_sufficient(response, threshold):
            logger.info(
                "Level 1 命中: query=%s, max_score=%.4f",
                query,
                response.results[0].score,
            )
            return DegradationResult(
                response=response,
                level=1,
                method="hybrid",
                original_query=query,
            )

        # ── Level 2: LLM 改写 query ──
        best_response = response
        best_score = self._max_score(response)
        best_query = query

        for attempt in range(MAX_REWRITE_ATTEMPTS):
            rewritten = self._rewrite_query(query, attempt)
            logger.info(
                "Level 2 改写 (attempt %d): %s → %s", attempt + 1, query, rewritten
            )

            new_response = self.retriever.search(
                query=rewritten,
                top_k=top_k,
                use_rerank=use_rerank,
                access_level=access_level,
            )
            new_score = self._max_score(new_response)

            # 检查是否有改善
            if new_score > best_score + IMPROVEMENT_THRESHOLD:
                best_response = new_response
                best_score = new_score
                best_query = rewritten

                if self._is_sufficient(new_response, threshold):
                    logger.info(
                        "Level 2 命中: rewritten=%s, max_score=%.4f",
                        rewritten,
                        new_score,
                    )
                    return DegradationResult(
                        response=new_response,
                        level=2,
                        method="rewritten",
                        original_query=query,
                        rewritten_query=rewritten,
                    )

        # ── Level 3: 查询扩展 (Multi-Query + HyDE) ──
        logger.info("Level 3 尝试查询扩展: %s", query[:50])
        expanded_response = self._expand_and_search(
            query, top_k, access_level=access_level
        )
        expanded_score = self._max_score(expanded_response)
        if expanded_score > best_score + IMPROVEMENT_THRESHOLD:
            best_response = expanded_response
            best_score = expanded_score
            logger.info("Level 3 命中: 查询扩展, max_score=%.4f", expanded_score)
            if self._is_sufficient(expanded_response, threshold):
                return DegradationResult(
                    response=expanded_response,
                    level=3,
                    method="expanded",
                    original_query=query,
                    rewritten_query=query,
                )

        # ── Level 4: 联网搜索 ──
        web_results = self._web_search(query)
        if web_results:
            logger.info("Level 4 命中: web_search, %d results", len(web_results))
            # 将联网搜索结果转换为 SearchResult
            web_search_results = [
                SearchResult(
                    chunk_id=f"web_{i}",
                    text=r.get("snippet", ""),
                    score=0.5,  # 联网结果给固定分数
                    doc_type="web",
                    source_file=r.get("url", ""),
                    heading_path=[r.get("title", "")],
                )
                for i, r in enumerate(web_results[:top_k])
            ]
            web_response = SearchResponse(
                query=query,
                results=web_search_results,
                total_found=len(web_search_results),
                elapsed_ms=best_response.elapsed_ms,
                threshold=threshold,
            )
            return DegradationResult(
                response=web_response,
                level=4,
                method="web_search",
                original_query=query,
                rewritten_query=best_query,
                web_results=web_results,
            )

        # ── Level 5: 兜底 ──
        logger.info("Level 5 兜底: query=%s", query)
        fallback_response = SearchResponse(
            query=query,
            results=[],
            total_found=0,
            elapsed_ms=best_response.elapsed_ms,
            threshold=threshold,
        )
        return DegradationResult(
            response=fallback_response,
            level=5,
            method="fallback",
            original_query=query,
            rewritten_query=best_query,
            degradation_reason="三级降级均未找到足够相关的结果",
        )

    def _is_sufficient(self, response: SearchResponse, threshold: float) -> bool:
        """检查检索结果是否足够好"""
        if not response.results:
            return False
        return response.results[0].score >= threshold

    def _max_score(self, response: SearchResponse) -> float:
        """获取最高分数"""
        if not response.results:
            return 0.0
        return max(r.score for r in response.results)

    def _rewrite_query(self, query: str, attempt: int) -> str:
        """LLM 改写查询"""
        try:
            # 不同尝试使用不同的改写策略
            if attempt == 0:
                prompt = f"将以下电商客服问题改写为更适合向量检索的简洁查询，去掉语气词，保留核心关键词：\n\n{query}"
            else:
                prompt = f"将以下电商客服问题换一种表达方式，补充隐含的电商上下文：\n\n{query}"

            client = get_llm_client()
            rewritten = client.chat_with_fallback(
                messages=[{"role": "user", "content": prompt}],
                fallback_value=query,
                temperature=0.3,
                max_tokens=100,
                timeout=10,
            )
            # 限制长度
            if len(rewritten) > 100:
                rewritten = rewritten[:100]
            return rewritten
        except Exception as e:
            logger.warning("查询改写失败: %s", e)
            return query

    def _expand_and_search(
        self, query: str, top_k: int, access_level: str = "public"
    ) -> SearchResponse:
        """查询扩展 + 并行检索 + 合并结果

        使用 Multi-Query 扩展，对每个子查询**并发**检索（ThreadPool，网络I/O 并行），
        合并去重后返回最佳结果。子问题上限由 QueryExpander 控制（3~5 个）。

        Args:
            access_level: 模块33 内容权限等级，透传给子查询 + HyDE 检索
        """
        import time as _time

        _t0 = _time.time()
        from .query_expansion import get_query_expander

        expander = get_query_expander()
        expansion = expander.expand(query)

        queries = expansion["queries"]
        hyde_doc = expansion.get("hyde_doc", "")

        logger.info("查询扩展: %s → %d 个子查询（并行）", query[:50], len(queries))

        # 并行检索所有子查询（线程池，网络I/O 并发 → 响应更快）
        all_results = []
        with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as pool:
            futures = [
                pool.submit(
                    self.retriever.search,
                    query=q,
                    top_k=top_k,
                    use_rerank=False,  # 子查询不重排序，最后统一排序
                    access_level=access_level,
                )
                for q in queries
            ]
            for future in futures:
                try:
                    all_results.extend(future.result().results)
                except Exception as e:
                    logger.warning("扩展查询检索失败: %s", e)

        # HyDE 文档检索
        if hyde_doc:
            try:
                hyde_response = self.retriever.search(
                    query=hyde_doc,
                    top_k=top_k,
                    use_rerank=False,
                    access_level=access_level,
                )
                all_results.extend(hyde_response.results)
            except Exception as e:
                logger.warning("HyDE 检索失败: %s", e)

        # 去重（按 chunk_id）
        seen = set()
        unique_results = []
        for r in all_results:
            if r.chunk_id not in seen:
                seen.add(r.chunk_id)
                unique_results.append(r)

        # 按分数排序
        unique_results.sort(key=lambda r: r.score, reverse=True)

        # 取 top_k
        final_results = unique_results[:top_k]

        # 修复(审查): elapsed_ms 用真实计时——SearchResult.metadata 来自 Milvus chunk_metadata
        # 不含 elapsed_ms，之前的 sum() 恒为 0，导致 search_time_ms 上报为 0。
        total_ms = int((_time.time() - _t0) * 1000)

        return SearchResponse(
            query=query,
            results=final_results,
            total_found=len(final_results),
            elapsed_ms=total_ms,
            threshold=0.0,
        )

    def _web_search(self, query: str) -> list[dict]:
        """联网搜索兜底

        优先使用智谱联网搜索，其次使用 Tavily Search API。
        """
        # 检查是否启用联网搜索
        if not getattr(settings, "web_search_enabled", True):
            return []

        # 优先尝试智谱联网搜索
        if settings.zhipu_api_key and getattr(
            settings, "zhipu_web_search_enabled", True
        ):
            results = self._zhipu_web_search(query)
            if results:
                return results

        # 备选：Tavily Search API
        tavily_key = getattr(settings, "tavily_api_key", "")
        if tavily_key:
            return self._tavily_web_search(query, tavily_key)

        logger.debug("未配置联网搜索 API Key（智谱/Tavily），跳过联网搜索")
        return []

    def _zhipu_web_search(self, query: str) -> list[dict]:
        """智谱联网搜索

        使用智谱 GLM-4-Flash + 联网搜索插件（统一使用 httpx 替代 requests）
        """
        import httpx

        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    f"{settings.zhipu_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.zhipu_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "glm-4-flash",
                        "messages": [{"role": "user", "content": query}],
                        "tools": [
                            {
                                "type": "web_search",
                                "web_search": {
                                    "enable": True,
                                    "search_query": query,
                                },
                            }
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            # 提取搜索结果
            results = []
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                # 检查是否有工具调用结果
                tool_calls = message.get("tool_calls", [])
                for tc in tool_calls:
                    if tc.get("type") == "web_search":
                        search_results = tc.get("web_search", {}).get("results", [])
                        for r in search_results:
                            results.append(
                                {
                                    "title": r.get("title", ""),
                                    "url": r.get("url", ""),
                                    "snippet": r.get("content", "")[:500],
                                }
                            )

                # 如果没有工具调用结果，直接返回LLM的回答
                if not results:
                    content = message.get("content", "")
                    if content:
                        results.append(
                            {
                                "title": "智谱联网搜索结果",
                                "url": "",
                                "snippet": content[:500],
                            }
                        )

            logger.info("智谱联网搜索: %s, 返回 %d 条结果", query[:50], len(results))
            return results

        except Exception as e:
            logger.warning("智谱联网搜索失败: %s", e)
            return []

    def _tavily_web_search(self, query: str, api_key: str) -> list[dict]:
        """Tavily Search API（统一使用 httpx 替代 requests）"""
        import httpx

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": 5,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            results = data.get("results", [])
            logger.info("Tavily 联网搜索: %s, 返回 %d 条结果", query[:50], len(results))
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:500],
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("Tavily 联网搜索失败: %s", e)
            return []


# ── 模块级单例 ──

import threading

_strategy_instance: Optional[DegradationStrategy] = None
_lock = threading.Lock()


def get_degradation_strategy(retriever=None) -> DegradationStrategy:
    """获取降级策略单例"""
    global _strategy_instance
    if _strategy_instance is None:
        with _lock:
            if _strategy_instance is None:
                if retriever is None:
                    from .retriever import get_retriever

                    retriever = get_retriever()
                _strategy_instance = DegradationStrategy(retriever)
    return _strategy_instance
