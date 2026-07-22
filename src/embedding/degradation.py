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
from dataclasses import dataclass, field
from typing import Optional

import requests

from src.config import settings

from .models import SearchResponse, SearchResult

logger = logging.getLogger(__name__)

# 降级参数
SIMILARITY_THRESHOLD = 0.7  # Level 1 最低相似度阈值
IMPROVEMENT_THRESHOLD = 0.05  # Level 2 改善幅度阈值
MAX_REWRITE_ATTEMPTS = 2  # 最大改写尝试次数


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
    ) -> DegradationResult:
        """带降级的检索

        Args:
            query: 用户查询
            top_k: 返回结果数
            threshold: 最低相似度阈值
            use_rerank: 是否启用 Reranker

        Returns:
            DegradationResult
        """
        # ── Level 1: 原始 query 检索 ──
        response = self.retriever.search(
            query=query,
            top_k=top_k,
            use_rerank=use_rerank,
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

        # ── Level 3: 联网搜索 ──
        web_results = self._web_search(query)
        if web_results:
            logger.info("Level 3 命中: web_search, %d results", len(web_results))
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
                level=3,
                method="web_search",
                original_query=query,
                rewritten_query=best_query,
                web_results=web_results,
            )

        # ── Level 4: 兜底 ──
        logger.info("Level 4 兜底: query=%s", query)
        fallback_response = SearchResponse(
            query=query,
            results=[],
            total_found=0,
            elapsed_ms=best_response.elapsed_ms,
            threshold=threshold,
        )
        return DegradationResult(
            response=fallback_response,
            level=4,
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
            from src.config import settings

            # 不同尝试使用不同的改写策略
            if attempt == 0:
                prompt = f"将以下电商客服问题改写为更适合向量检索的简洁查询，去掉语气词，保留核心关键词：\n\n{query}"
            else:
                prompt = f"将以下电商客服问题换一种表达方式，补充隐含的电商上下文：\n\n{query}"

            resp = requests.post(
                f"{settings.deepseek_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.default_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 100,
                },
                timeout=10,
            )
            resp.raise_for_status()
            rewritten = resp.json()["choices"][0]["message"]["content"].strip()
            # 限制长度
            if len(rewritten) > 100:
                rewritten = rewritten[:100]
            return rewritten
        except Exception as e:
            logger.warning("查询改写失败: %s", e)
            return query

    def _web_search(self, query: str) -> list[dict]:
        """联网搜索兜底

        使用 Tavily Search API（如果配置了），否则返回空列表。
        """
        tavily_key = getattr(settings, "tavily_api_key", "")
        if not tavily_key:
            logger.debug("未配置 Tavily API Key，跳过联网搜索")
            return []

        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("联网搜索失败: %s", e)
            return []


# ── 模块级单例 ──

_strategy_instance: Optional[DegradationStrategy] = None


def get_degradation_strategy(retriever=None) -> DegradationStrategy:
    """获取降级策略单例"""
    global _strategy_instance
    if _strategy_instance is None:
        if retriever is None:
            from .retriever import get_retriever

            retriever = get_retriever()
        _strategy_instance = DegradationStrategy(retriever)
    return _strategy_instance
