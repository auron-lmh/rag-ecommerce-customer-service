"""模块6 幻觉检测器 — G-Eval 风格 LLM 自检

使用 LLM 检查生成的回答是否有事实依据。
"""

import json
import logging
from typing import Optional

import requests

from src.config import settings

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
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model or settings.default_model
        self._api_key = api_key or settings.deepseek_api_key
        self._base_url = base_url or settings.deepseek_base_url

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
        """调用 LLM 进行幻觉检测"""
        docs_text = "\n\n".join(
            f"[文档{i+1}] {d[:1000]}" for i, d in enumerate(docs[:5])
        )

        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": DETECTION_PROMPT.format(
                            retrieved_docs=docs_text,
                            answer=answer,
                        ),
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
            },
            timeout=30,
        )
        resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"].strip()
        # 提取 JSON（可能被 markdown 包裹）
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content)
        return self._parse_result(data)

    def _parse_result(self, data: dict) -> HallucinationCheck:
        """解析 LLM 返回的 JSON"""
        claims = []
        for c in data.get("claims", []):
            verdict_str = c.get("verdict", "hallucination")
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

        return HallucinationCheck(
            claims=claims,
            overall_faithfulness=float(data.get("overall_faithfulness", 0)),
            has_hallucination=bool(data.get("has_hallucination", hallucination > 0)),
            hallucination_count=hallucination,
            supported_count=supported,
            partial_count=partial,
        )

    def _fallback_check(self, answer: str, docs: list[str]) -> HallucinationCheck:
        """降级检查（LLM 不可用时）"""
        # 简单检查：回答是否包含"无法确认"等关键词
        fallback_phrases = ["无法确认", "不确定", "没有找到", "建议咨询"]
        has_fallback = any(phrase in answer for phrase in fallback_phrases)

        if has_fallback:
            return HallucinationCheck(
                claims=[],
                overall_faithfulness=0.5,
                has_hallucination=False,
            )

        return HallucinationCheck(
            claims=[],
            overall_faithfulness=0.3,
            has_hallucination=True,
        )


# ── 模块级单例 ──

_detector_instance: Optional[HallucinationDetector] = None


def get_detector() -> HallucinationDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = HallucinationDetector()
    return _detector_instance
