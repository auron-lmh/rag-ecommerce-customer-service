"""模块6 自纠正闭环 — 幻觉检测 → 缺失信息提取 → 改写重搜 → 重新生成

闭环流程:
  1. 检索 → 生成回答
  2. 幻觉检测
  3. 如果有幻觉 → 提取缺失信息 → 改写 query → 重新检索
  4. 合并文档 → 重新生成
  5. 重复直到无幻觉或达到最大轮数
"""

import logging
from typing import Optional

import requests

from src.config import settings
from src.embedding.models import SearchResponse

from .hallucination_detector import HallucinationDetector, get_detector
from .models import GenerationResult, HallucinationCheck

logger = logging.getLogger(__name__)

# 最大自纠正轮数
MAX_CORRECTION_ROUNDS = 2

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
    ) -> GenerationResult:
        """带自纠正的生成

        Args:
            query: 用户查询
            top_k: 检索结果数
            use_rerank: 是否启用 Reranker
            max_rounds: 最大纠正轮数
            faithfulness_threshold: 忠实度阈值

        Returns:
            GenerationResult
        """
        # ── 步骤1: 初始检索 ──
        search_response = self.retriever.search(
            query=query,
            top_k=top_k,
            use_rerank=use_rerank,
        )
        docs = [r.text for r in search_response.results]
        sources = [r.source_file for r in search_response.results]

        # ── 步骤2: 生成回答 ──
        answer = self._generate(query, docs)

        # ── 步骤3: 幻觉检测 ──
        check = self.detector.check(answer, docs)

        if (
            not check.has_hallucination
            or check.overall_faithfulness >= faithfulness_threshold
        ):
            return GenerationResult(
                answer=answer,
                sources=sources,
                faithfulness=check.overall_faithfulness,
                hallucination_check=check,
                correction_rounds=0,
                was_corrected=False,
            )

        # ── 步骤4: 自纠正循环 ──
        for round_num in range(1, max_rounds + 1):
            logger.info(
                "自纠正轮次 %d/%d: faithfulness=%.2f",
                round_num,
                max_rounds,
                check.overall_faithfulness,
            )

            # 提取缺失信息
            missing_info = self._extract_missing_info(query, check)

            # 改写 query 重新检索
            refined_query = f"{query} {missing_info}"
            new_response = self.retriever.search(
                query=refined_query,
                top_k=top_k,
                use_rerank=use_rerank,
            )

            # 合并文档（去重）
            new_docs = [r.text for r in new_response.results]
            merged_docs = self._merge_docs(docs, new_docs)
            new_sources = list(
                set(sources + [r.source_file for r in new_response.results])
            )

            # 重新生成
            answer = self._generate(query, merged_docs)

            # 重新检测
            check = self.detector.check(answer, merged_docs)
            docs = merged_docs
            sources = new_sources

            if (
                not check.has_hallucination
                or check.overall_faithfulness >= faithfulness_threshold
            ):
                return GenerationResult(
                    answer=answer,
                    sources=sources,
                    faithfulness=check.overall_faithfulness,
                    hallucination_check=check,
                    correction_rounds=round_num,
                    was_corrected=True,
                )

        # ── 步骤5: 兜底处理 ──
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
        """调用 LLM 生成回答（带缓存）"""
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

        try:
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
                    "max_tokens": 1024,
                },
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"].strip()

            # 存入缓存
            try:
                cache.set_llm_response(prompt, result, ttl=3600)
            except Exception:
                pass

            return result
        except Exception as e:
            logger.error("生成失败: %s", e)
            return "抱歉，生成回答时出现错误，请稍后重试。"

    def _extract_missing_info(self, query: str, check: HallucinationCheck) -> str:
        """从幻觉检测结果中提取缺失信息"""
        hallucination_details = "\n".join(
            f"- {c.text}: {c.reason}"
            for c in check.claims
            if c.verdict.value == "hallucination"
        )

        try:
            resp = requests.post(
                f"{settings.deepseek_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.default_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": EXTRACT_MISSING_PROMPT.format(
                                query=query,
                                hallucination_details=hallucination_details,
                            ),
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 100,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning("缺失信息提取失败: %s", e)
            return ""

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

_corrector_instance: Optional[SelfCorrector] = None


def get_corrector(retriever=None) -> SelfCorrector:
    global _corrector_instance
    if _corrector_instance is None:
        if retriever is None:
            from src.embedding.retriever import get_retriever

            retriever = get_retriever()
        _corrector_instance = SelfCorrector(retriever)
    return _corrector_instance
