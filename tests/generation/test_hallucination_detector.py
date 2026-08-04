"""幻觉检测器测试 — claims 聚合（不信任 LLM 自报标量）"""

from src.generation.hallucination_detector import HallucinationDetector
from src.generation.models import ClaimVerdict


def _detect(data: dict):
    return HallucinationDetector()._parse_result(data)


class TestClaimsAggregation:
    def test_all_supported_high_faithfulness(self):
        r = _detect(
            {
                "claims": [
                    {"text": "a", "verdict": "supported"},
                    {"text": "b", "verdict": "supported"},
                ]
            }
        )
        assert r.has_hallucination is False
        assert r.overall_faithfulness == 1.0

    def test_one_hallucination_flags_even_if_llm_says_clean(self):
        """修复P0: LLM 自报 has_hallucination=false，但 claims 里有幻觉 → 判有幻觉"""
        r = _detect(
            {
                "claims": [
                    {"text": "a", "verdict": "supported"},
                    {"text": "b", "verdict": "hallucination"},
                ],
                "has_hallucination": False,
                "overall_faithfulness": 0.9,
            }
        )
        assert r.has_hallucination is True
        assert r.overall_faithfulness == 0.5

    def test_empty_claims_conservative(self):
        """修复P1: 空 claims = 检测失败 → 保守判有幻觉"""
        r = _detect(
            {"claims": [], "has_hallucination": False, "overall_faithfulness": 0.95}
        )
        assert r.has_hallucination is True
        assert r.overall_faithfulness == 0.0

    def test_partial_claims_half_credit(self):
        r = _detect(
            {
                "claims": [
                    {"text": "a", "verdict": "supported"},
                    {"text": "b", "verdict": "partially"},
                    {"text": "c", "verdict": "hallucination"},
                ]
            }
        )
        assert r.overall_faithfulness == round((1 + 0.5) / 3, 4)
        assert r.has_hallucination is True


class TestVerdictNormalization:
    def test_emoji_alias(self):
        r = _detect({"claims": [{"text": "a", "verdict": "✅"}]})
        assert r.claims[0].verdict == ClaimVerdict.SUPPORTED

    def test_chinese_alias(self):
        r = _detect({"claims": [{"text": "a", "verdict": "无依据"}]})
        assert r.claims[0].verdict == ClaimVerdict.HALLUCINATION

    def test_unknown_verdict_falls_to_hallucination(self):
        r = _detect({"claims": [{"text": "a", "verdict": "weird_label"}]})
        assert r.claims[0].verdict == ClaimVerdict.HALLUCINATION


class TestFallbackCheck:
    def test_honest_uncertainty_clean(self):
        r = HallucinationDetector()._fallback_check(
            "根据已有信息无法确认，建议咨询人工客服。", ["doc"]
        )
        assert r.has_hallucination is False
        assert r.overall_faithfulness == 0.9

    def test_unverifiable_low_faithfulness(self):
        """修复P1: 无法验证 → 低忠实度 + 不触发重写（不判幻觉）"""
        r = HallucinationDetector()._fallback_check(
            "您的退款将在1-3个工作日内到账。", ["doc"]
        )
        assert r.has_hallucination is False
        assert r.overall_faithfulness == 0.5
