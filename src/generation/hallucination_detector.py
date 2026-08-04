"""模块6 幻觉检测器 — G-Eval 风格 LLM 自检

使用 LLM 检查生成的回答是否有事实依据。
使用统一 LLMClient 替代原始 requests 调用。
"""

import logging
from typing import Optional

from src.engineering.llm_client import get_llm_client

from .models import Claim, ClaimVerdict, HallucinationCheck

logger = logging.getLogger(__name__)

DETECTION_PROMPT = """请逐一检查以下回答中的每个事实断言，判断在参考文档中是否有依据。

参考文档:
{retrieved_docs}

待检查回答:
{answer}

请将回答拆分为事实断言列表，逐一标注:
- ✅ 有依据（标注来源片段）
- ⚠️ 部分有依据（指出缺失的部分）
- ❌ 无依据（幻觉）

输出JSON格式:
{{
    "claims": [
        {{"text": "...", "verdict": "supported", "evidence": "文档1第3段: ..."}},
        {{"text": "...", "verdict": "partially", "evidence": "...", "reason": "缺少..."}},
        {{"text": "...", "verdict": "hallucination", "reason": "参考文档中没有提到..."}}
    ],
    "overall_faithfulness": 0.85,
    "has_hallucination": true
}}"""


class HallucinationDetector:
    """幻觉检测器 — LLM 自检

    使用方式:
        detector = HallucinationDetector()
        check = detector.check(answer="退货流程是...", docs=["文档1...", "文档2..."])
        print(check.has_hallucination)
    """

    def __init__(
        self,
        model: Optional[str] = None,
    ):
        if model:
            from src.engineering.llm_client import LLMClient

            self._client = LLMClient(model=model)
        else:
            self._client = get_llm_client()

    def check(self, answer: str, docs: list[str]) -> HallucinationCheck:
        """检查回答是否有幻觉

        Args:
            answer: LLM 生成的回答
            docs: 参考文档列表

        Returns:
            HallucinationCheck
        """
        if not answer or not docs:
            return HallucinationCheck(
                claims=[],
                overall_faithfulness=0.0,
                has_hallucination=True,
            )

        try:
            return self._call_llm(answer, docs)
        except Exception as e:
            logger.error("幻觉检测失败，降级为简单检查: %s", e)
            return self._fallback_check(answer, docs)

    def _call_llm(self, answer: str, docs: list[str]) -> HallucinationCheck:
        """调用 LLM 进行幻觉检测（使用统一 LLMClient）"""
        docs_text = "\n\n".join(
            f"[文档{i+1}] {d[:1000]}" for i, d in enumerate(docs[:5])
        )

        data = self._client.chat_json(
            messages=[
                {
                    "role": "user",
                    "content": DETECTION_PROMPT.format(
                        retrieved_docs=docs_text,
                        answer=answer,
                    ),
                }
            ],
            temperature=0.1,
            max_tokens=2048,
            timeout=30,
        )
        return self._parse_result(data)

    @staticmethod
    def _normalize_verdict(verdict_str: str) -> str:
        """容错: emoji/中文别名 → 标准 verdict"""
        v = (verdict_str or "").strip().lower()
        mapping = {
            "✅": "supported",
            "有依据": "supported",
            "supported": "supported",
            "yes": "supported",
            "true": "supported",
            "⚠️": "partially",
            "部分有依据": "partially",
            "partially": "partially",
            "partial": "partially",
            "部分": "partially",
            "❌": "hallucination",
            "无依据": "hallucination",
            "hallucination": "hallucination",
            "no": "hallucination",
            "false": "hallucination",
        }
        return mapping.get(v, v)

    def _parse_result(self, data: dict) -> HallucinationCheck:
        """解析 LLM 返回的 JSON — 从 claims 聚合，不信任 LLM 自报标量

        修复 (P0): 之前直接取 LLM 自报 overall_faithfulness/has_hallucination，
        模型自偏或均值化会掩盖个别幻觉断言。改为从 claim 级聚合:
          faithfulness = (supported + 0.5*partial) / total
          has_hallucination = 存在幻觉断言 或 faithfulness < 0.6
        空 claims 视为检测失败，保守处理（不判干净）。
        """
        claims = []
        for c in data.get("claims", []):
            verdict_str = self._normalize_verdict(c.get("verdict", "hallucination"))
            try:
                verdict = ClaimVerdict(verdict_str)
            except ValueError:
                verdict = ClaimVerdict.HALLUCINATION

            claims.append(
                Claim(
                    text=c.get("text", ""),
                    verdict=verdict,
                    evidence=c.get("evidence", ""),
                    reason=c.get("reason", ""),
                )
            )

        supported = sum(1 for c in claims if c.verdict == ClaimVerdict.SUPPORTED)
        partial = sum(1 for c in claims if c.verdict == ClaimVerdict.PARTIALLY)
        hallucination = sum(
            1 for c in claims if c.verdict == ClaimVerdict.HALLUCINATION
        )

        total = len(claims)
        if total == 0:
            # 空 claims = 检测失败，保守处理（不判干净，走人工/重检）
            logger.warning("幻觉检测返回空 claims，按未通过处理")
            return HallucinationCheck(
                claims=[],
                overall_faithfulness=0.0,
                has_hallucination=True,
            )

        # 从 claims 聚合（部分有依据折半计入）
        faithfulness = round((supported + 0.5 * partial) / total, 4)
        has_hallucination = hallucination > 0 or faithfulness < 0.6

        return HallucinationCheck(
            claims=claims,
            overall_faithfulness=faithfulness,
            has_hallucination=has_hallucination,
            hallucination_count=hallucination,
            supported_count=supported,
            partial_count=partial,
        )

    def _fallback_check(self, answer: str, docs: list[str]) -> HallucinationCheck:
        """降级检查（LLM 不可用时）— 无法验证，标记不确定

        修复 (P1): 之前按关键词方向误判——正常有依据的回答被判幻觉触发重写，
        含"建议咨询"但编造的回答被判干净。改为:
          - 诚实拒答（明确说不知道）→ 不算幻觉
          - 无法验证 → 低忠实度 + 不触发重写（由上游质量评估决定转人工）
        """
        honest_phrases = ["无法确认", "不确定", "没有找到", "根据已有信息"]
        if any(phrase in answer for phrase in honest_phrases):
            return HallucinationCheck(
                claims=[],
                overall_faithfulness=0.9,
                has_hallucination=False,
            )
        # 无法验证：低忠实度 + 不判幻觉（避免无谓重写），由 evaluate_quality 决定
        return HallucinationCheck(
            claims=[],
            overall_faithfulness=0.5,
            has_hallucination=False,
        )


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_detector() -> HallucinationDetector:
    """获取 HallucinationDetector 单例"""
    return HallucinationDetector()
