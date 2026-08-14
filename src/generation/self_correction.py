"""模块6 自纠正闭环 — 幻觉检测 → 缺失信息提取 → 改写重搜 → 重新生成

闭环流程:
  1. 检索 → 生成回答
  2. 幻觉检测
  3. 如果有幻觉 → 提取缺失信息 → 改写 query → 重新检索
  4. 合并文档 → 重新生成
  5. 重复直到无幻觉或达到最大轮数

使用统一 LLMClient 替代原始 requests 调用。
"""

import logging
from typing import Optional

from src.engineering.llm_client import get_llm_client

from .hallucination_detector import HallucinationDetector, get_detector
from .models import GenerationResult, HallucinationCheck

logger = logging.getLogger(__name__)

# 最大自纠正轮数
MAX_CORRECTION_ROUNDS = 2

# LLM 调用预算（防止延迟爆炸）
MAX_LLM_CALLS = 8

# 生成 System Prompt
GENERATION_PROMPT = """你是一个电商客服助手。请基于以下参考文档回答用户问题。

规则:
1. 只基于提供的文档内容回答，不要编造信息
2. 如果文档中没有相关信息，请明确说"根据已有信息无法确认"
3. 每个回答附引用来源，格式: [1][2]...
4. 回答要简洁、专业、有帮助

参考文档:
{context}

用户问题: {query}"""

# 缺失信息提取 Prompt
EXTRACT_MISSING_PROMPT = """根据幻觉检测结果，提取回答中缺失的关键信息。

用户问题: {query}
幻觉检测结果:
{hallucination_details}

请用一句话概括需要补充检索的信息（例如: "退货时限" "退款到账时间"）:"""


class SelfCorrector:
    """自纠正闭环

    使用方式:
        corrector = SelfCorrector(retriever)
        result = corrector.generate_with_correction("怎么退货？")
        print(result.answer)
        print(result.was_corrected)
        print(result.correction_rounds)
    """

    def __init__(
        self,
        retriever,
        detector: Optional[HallucinationDetector] = None,
    ):
        self.retriever = retriever
        self.detector = detector or get_detector()

    def generate_with_correction(
        self,
        query: str,
        top_k: int = 5,
        use_rerank: bool = True,
        max_rounds: int = MAX_CORRECTION_ROUNDS,
        faithfulness_threshold: float = 0.8,
        access_level: str = "public",
    ) -> GenerationResult:
        """带自纠正的生成（包含初始检索，适合独立调用）

        Args:
            query: 用户查询
            top_k: 检索结果数
            use_rerank: 是否启用 Reranker
            max_rounds: 最大纠正轮数
            faithfulness_threshold: 忠实度阈值
            access_level: 模块33 内容权限等级，透传给初始检索 + 纠正循环重新检索

        Returns:
            GenerationResult
        """
        # ── 步骤1: 初始检索 ──
        search_response = self.retriever.search(
            query=query,
            top_k=top_k,
            use_rerank=use_rerank,
            access_level=access_level,
        )
        docs = [r.text for r in search_response.results]
        sources = [r.source_file for r in search_response.results]

        # ── 步骤2-5: 复用 generate_with_docs ──
        return self.generate_with_docs(
            query=query,
            docs=docs,
            sources=sources,
            top_k=top_k,
            use_rerank=use_rerank,
            max_rounds=max_rounds,
            faithfulness_threshold=faithfulness_threshold,
            access_level=access_level,
        )

    def generate_with_docs(
        self,
        query: str,
        docs: list[str],
        sources: list[str],
        top_k: int = 5,
        use_rerank: bool = True,
        max_rounds: int = MAX_CORRECTION_ROUNDS,
        faithfulness_threshold: float = 0.8,
        access_level: str = "public",
    ) -> GenerationResult:
        """基于已有文档生成回答（供 LangGraph workflow 调用，跳过初始检索）

        Args:
            query: 用户查询
            docs: 已检索的文档文本列表（来自 retriever_node）
            sources: 文档来源文件名列表
            top_k: 检索结果数（纠正循环中重新检索时使用）
            use_rerank: 是否启用 Reranker
            max_rounds: 最大纠正轮数
            faithfulness_threshold: 忠实度阈值
            access_level: 模块33 内容权限等级，透传给纠正循环重新检索
                          ★workflow 空 docs 兜底会触发这里再检索，漏传=受限用户无过滤重搜

        Returns:
            GenerationResult
        """
        # LLM 调用计数器（防止延迟爆炸）
        llm_call_count = 0

        # ── 步骤1: 基于已有文档生成回答 ──
        answer = self._generate(query, docs)
        llm_call_count += 1

        # ── 步骤2: 幻觉检测 ──
        check = self.detector.check(answer, docs)
        llm_call_count += 1

        if (
            not check.has_hallucination
            and check.overall_faithfulness >= faithfulness_threshold
        ):
            return GenerationResult(
                answer=answer,
                sources=sources,
                faithfulness=check.overall_faithfulness,
                hallucination_check=check,
                correction_rounds=0,
                was_corrected=False,
            )

        # ── 步骤3: 自纠正循环（带 LLM 调用预算） ──
        for round_num in range(1, max_rounds + 1):
            # 检查 LLM 调用预算
            if llm_call_count >= MAX_LLM_CALLS:
                logger.warning(
                    "LLM 调用已达预算上限 (%d/%d)，停止纠正",
                    llm_call_count,
                    MAX_LLM_CALLS,
                )
                break

            logger.info(
                "自纠正轮次 %d/%d: faithfulness=%.2f, LLM调用=%d/%d",
                round_num,
                max_rounds,
                check.overall_faithfulness,
                llm_call_count,
                MAX_LLM_CALLS,
            )

            # 提取缺失信息
            missing_info = self._extract_missing_info(query, check)
            llm_call_count += 1

            # 改写 query 重新检索
            refined_query = f"{query} {missing_info}"
            new_response = self.retriever.search(
                query=refined_query,
                top_k=top_k,
                use_rerank=use_rerank,
                access_level=access_level,
            )

            # 合并文档（去重）
            new_docs_list = [r.text for r in new_response.results]
            merged_docs = self._merge_docs(docs, new_docs_list)
            new_sources = list(
                set(sources + [r.source_file for r in new_response.results])
            )

            # 重新生成
            answer = self._generate(query, merged_docs)
            llm_call_count += 1

            # 重新检测
            check = self.detector.check(answer, merged_docs)
            llm_call_count += 1
            docs = merged_docs
            sources = new_sources

            if (
                not check.has_hallucination
                and check.overall_faithfulness >= faithfulness_threshold
            ):
                return GenerationResult(
                    answer=answer,
                    sources=sources,
                    faithfulness=check.overall_faithfulness,
                    hallucination_check=check,
                    correction_rounds=round_num,
                    was_corrected=True,
                )

        # ── 步骤4: 兜底处理 ──
        logger.warning("自纠正 %d 轮后仍有幻觉，降级为部分回答", max_rounds)
        fallback_answer = self._build_fallback_answer(query, answer, check)

        return GenerationResult(
            answer=fallback_answer,
            sources=sources,
            faithfulness=check.overall_faithfulness,
            hallucination_check=check,
            correction_rounds=max_rounds,
            was_corrected=True,
            final_level=4,
        )

    def _generate(self, query: str, docs: list[str]) -> str:
        """调用 LLM 生成回答（带缓存，使用统一 LLMClient）"""
        context = "\n\n".join(f"[文档{i+1}] {d[:800]}" for i, d in enumerate(docs[:5]))
        prompt = GENERATION_PROMPT.format(context=context, query=query)

        # 检查 LLM 缓存
        try:
            from src.engineering import get_cache

            cache = get_cache()
            cached = cache.get_llm_response(prompt)
            if cached:
                logger.debug("LLM 缓存命中: %s", query[:50])
                return cached
        except Exception:
            pass

        client = get_llm_client()
        fallback_msg = "抱歉，生成回答时出现错误，请稍后重试。"
        result = client.chat_with_fallback(
            messages=[{"role": "user", "content": prompt}],
            fallback_value=fallback_msg,
            temperature=0.3,
            max_tokens=1024,
            timeout=30,
        )

        # 存入缓存（修复: 不缓存降级错误文案，避免后续同 query 一直返回错误）
        if result and result != fallback_msg:
            try:
                cache.set_llm_response(prompt, result, ttl=3600)
            except Exception:
                pass

        return result

    def _extract_missing_info(self, query: str, check: HallucinationCheck) -> str:
        """从幻觉检测结果中提取缺失信息（使用统一 LLMClient）"""
        hallucination_details = "\n".join(
            f"- {c.text}: {c.reason}"
            for c in check.claims
            if c.verdict.value == "hallucination"
        )

        client = get_llm_client()
        return client.chat_with_fallback(
            messages=[
                {
                    "role": "user",
                    "content": EXTRACT_MISSING_PROMPT.format(
                        query=query,
                        hallucination_details=hallucination_details,
                    ),
                }
            ],
            fallback_value="",
            temperature=0.1,
            max_tokens=100,
            timeout=15,
        )

    def _merge_docs(self, existing: list[str], new: list[str]) -> list[str]:
        """合并文档列表（简单去重）"""
        seen = set()
        merged = []
        for doc in existing + new:
            # 用前100字符作为去重 key
            key = doc[:100]
            if key not in seen:
                seen.add(key)
                merged.append(doc)
        return merged

    def _build_fallback_answer(
        self, query: str, answer: str, check: HallucinationCheck
    ) -> str:
        """构建兜底回答 — 保留有依据的部分，标注不确定的部分"""
        supported_parts = []
        uncertain_parts = []

        for claim in check.claims:
            if claim.verdict.value == "supported":
                supported_parts.append(claim.text)
            elif claim.verdict.value == "hallucination":
                uncertain_parts.append(claim.text)

        result = ""
        if supported_parts:
            result += "根据已有信息:\n" + "\n".join(f"- {p}" for p in supported_parts)

        if uncertain_parts:
            result += "\n\n关于以下问题，根据已有信息我无法确认，建议您咨询人工客服获取准确信息:\n"
            result += "\n".join(f"- {p}" for p in uncertain_parts)

        return (
            result
            if result
            else "抱歉，根据已有信息无法回答该问题，建议您咨询人工客服。"
        )


# ── 模块级单例 ──

import threading

_corrector_instance: Optional[SelfCorrector] = None
_lock = threading.Lock()


def get_corrector(retriever=None) -> SelfCorrector:
    global _corrector_instance
    if _corrector_instance is None:
        with _lock:
            if _corrector_instance is None:
                if retriever is None:
                    from src.embedding.retriever import get_retriever

                    retriever = get_retriever()
                _corrector_instance = SelfCorrector(retriever)
    return _corrector_instance
