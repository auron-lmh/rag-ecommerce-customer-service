"""Qwen3-VL-Reranker 重排序模块 — DashScope TextReRank API

特性:
  - 支持文本查询 + 文本文档重排序
  - 支持图片查询 (以图搜文)
  - 指数退避重试 (429)
  - 最大文档数: 文本 100 / 图片 40

API: dashscope.TextReRank.call() (非 OpenAI 兼容协议)
文档: https://help.aliyun.com/zh/model-studio/text-rerank-api
"""

import logging
import time
from http import HTTPStatus
from typing import Optional, Union

import dashscope

from src.config import settings

from ..embedding.models import SearchResponse, SearchResult

logger = logging.getLogger(__name__)

# 重试参数
MAX_429_RETRIES = 5
BASE_BACKOFF = 2.0


class Reranker:
    """Qwen3-VL-Reranker 封装 (DashScope API)

    使用方式:
        reranker = Reranker()
        reranked = reranker.rerank(query="怎么退货?", documents=["doc1...", "doc2..."])
        # 或从 SearchResponse 直接重排
        reranked = reranker.rerank_search_response(query, search_response, top_n=5)
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model_name = model_name or settings.reranker_model
        self._api_key = api_key or settings.bailian_api_key

    # ── 文本查询重排序 ──

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int = 5,
        return_documents: bool = True,
        instruct: Optional[str] = None,
    ) -> list[dict]:
        """对文档列表进行重排序

        Args:
            query: 查询文本
            documents: 候选文档文本列表 (最多 100 条)
            top_n: 返回前 N 条
            return_documents: 是否返回文档原文
            instruct: 排序指令 (英文), 如 "Given a query, retrieve relevant passages"

        Returns:
            [{"index": 0, "document": {"text": "..."}, "relevance_score": 0.93}, ...]
            按 relevance_score 降序排列
        """
        if not documents:
            return []
        if len(documents) > 100:
            logger.warning("文档数 %d 超过上限 100, 截断处理", len(documents))
            documents = documents[:100]

        docs_payload = [{"text": d} for d in documents]

        for attempt in range(MAX_429_RETRIES + 1):
            try:
                response = dashscope.TextReRank.call(
                    model=self.model_name,
                    query={"text": query},
                    documents=docs_payload,
                    top_n=min(top_n, len(documents)),
                    return_documents=return_documents,
                    api_key=self._api_key,
                    **(instruct and {"instruct": instruct} or {}),
                )
            except Exception as e:
                logger.error("Reranker API 异常 (attempt %d): %s", attempt + 1, e)
                if attempt < MAX_429_RETRIES:
                    time.sleep(BASE_BACKOFF**attempt)
                    continue
                raise

            status = getattr(response, "status_code", None)

            if status == HTTPStatus.OK:
                results = response.output.get("results", [])
                # 按 relevance_score 降序排列 (API 已排序，但确保一下)
                results.sort(key=lambda r: r.get("relevance_score", 0), reverse=True)
                return results

            if status == 429:
                retry_after = None
                try:
                    headers = getattr(response, "headers", {}) or {}
                    ra = headers.get("Retry-After") or headers.get("retry-after")
                    if ra:
                        retry_after = float(ra)
                except Exception:
                    pass
                wait = retry_after or (BASE_BACKOFF**attempt)
                logger.warning(
                    "Reranker 429 (attempt %d/%d), 等待 %.1fs",
                    attempt + 1,
                    MAX_429_RETRIES,
                    wait,
                )
                if attempt < MAX_429_RETRIES:
                    time.sleep(wait)
                continue

            code = getattr(response, "code", "")
            msg = getattr(response, "message", "")
            raise RuntimeError(
                f"Reranker API 错误: status={status}, code={code}, message={msg}"
            )

        raise RuntimeError("Reranker API 调用失败: 重试耗尽")

    # ── 图片查询重排序 ──

    def rerank_by_image(
        self,
        image_url: str,
        documents: list[str],
        top_n: int = 5,
        return_documents: bool = True,
    ) -> list[dict]:
        """以图搜文 — 图片查询 + 文本候选文档

        Args:
            image_url: 图片 URL (需 DashScope 可访问) 或 base64 data URI
            documents: 候选文本列表 (最多 40 条)
            top_n: 返回前 N 条
        """
        if not documents:
            return []
        if len(documents) > 40:
            logger.warning("图片查询文档数 %d 超过上限 40, 截断处理", len(documents))
            documents = documents[:40]

        docs_payload = [{"text": d} for d in documents]

        for attempt in range(MAX_429_RETRIES + 1):
            try:
                response = dashscope.TextReRank.call(
                    model=self.model_name,
                    query={"image": image_url},
                    documents=docs_payload,
                    top_n=min(top_n, len(documents)),
                    return_documents=return_documents,
                    api_key=self._api_key,
                )
            except Exception as e:
                logger.error("Reranker API 异常 (attempt %d): %s", attempt + 1, e)
                if attempt < MAX_429_RETRIES:
                    time.sleep(BASE_BACKOFF**attempt)
                    continue
                raise

            status = getattr(response, "status_code", None)
            if status == HTTPStatus.OK:
                results = response.output.get("results", [])
                results.sort(key=lambda r: r.get("relevance_score", 0), reverse=True)
                return results

            if status == 429:
                retry_after = None
                try:
                    headers = getattr(response, "headers", {}) or {}
                    ra = headers.get("Retry-After") or headers.get("retry-after")
                    if ra:
                        retry_after = float(ra)
                except Exception:
                    pass
                wait = retry_after or (BASE_BACKOFF**attempt)
                logger.warning(
                    "Reranker 429 (attempt %d/%d), 等待 %.1fs",
                    attempt + 1,
                    MAX_429_RETRIES,
                    wait,
                )
                if attempt < MAX_429_RETRIES:
                    time.sleep(wait)
                continue

            code = getattr(response, "code", "")
            msg = getattr(response, "message", "")
            raise RuntimeError(
                f"Reranker API 错误: status={status}, code={code}, message={msg}"
            )

        raise RuntimeError("Reranker API 调用失败: 重试耗尽")

    # ── 集成 SearchResponse ──

    def rerank_search_response(
        self,
        query: str,
        search_response: SearchResponse,
        top_n: Optional[int] = None,
    ) -> SearchResponse:
        """对 SearchResponse 进行重排序，生成新的 SearchResponse

        保留原始 score，新增 rerank_score。
        """
        if top_n is None:
            top_n = settings.reranker_top_n

        if not search_response.results:
            return search_response

        # 提取文本列表
        texts = [r.text for r in search_response.results]
        indices = list(range(len(texts)))

        try:
            ranked = self.rerank(query=query, documents=texts, top_n=top_n)
        except Exception as e:
            logger.error("重排序失败，返回原始结果: %s", e)
            return search_response

        # 重建结果列表
        reranked_results: list[SearchResult] = []
        for item in ranked:
            orig_idx = item["index"]
            if orig_idx < len(search_response.results):
                orig = search_response.results[orig_idx]
                reranked_results.append(
                    SearchResult(
                        chunk_id=orig.chunk_id,
                        text=orig.text,
                        score=orig.score,  # 保留原始检索分数
                        doc_type=orig.doc_type,
                        source_file=orig.source_file,
                        heading_path=orig.heading_path,
                        metadata={
                            **orig.metadata,
                            "rerank_score": item.get("relevance_score", 0),
                            "original_rank": orig_idx,
                        },
                    )
                )

        return SearchResponse(
            query=query,
            results=reranked_results,
            total_found=len(reranked_results),
            elapsed_ms=search_response.elapsed_ms,
            threshold=search_response.threshold,
        )


# ═══════════════════════════════════════
# 模块级单例
# ═══════════════════════════════════════

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_reranker() -> Reranker:
    return Reranker()
