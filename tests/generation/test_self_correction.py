"""self_correction 纠正循环退出条件回归测试

P0 回归：退出条件 `or` → `and`。
修复前：`has_hallucination=True` 但 `overall_faithfulness >= threshold` 时，
        `or` 短路直接返回，检测到的幻觉被放行（含高敏退款/价格/政策）。
修复后：只有「无幻觉 且 忠实度达标」才跳过纠正，含幻觉必须纠正。
"""

from types import SimpleNamespace

from src.embedding.models import SearchResponse, SearchResult
from src.generation.self_correction import SelfCorrector


def _res():
    return SearchResult(chunk_id="c", text="文本", score=0.9, source_file="s.md")


class _RecordingRetriever:
    def __init__(self):
        self.search_calls = 0

    def search(self, query, top_k=5, use_rerank=True, **kwargs):
        self.search_calls += 1
        return SearchResponse(
            query=query,
            results=[_res()],
            total_found=1,
            elapsed_ms=1,
            threshold=0,
        )


class _HighFaithfulnessWithHallucinationDetector:
    """第一次检测：整体忠实度高(0.9≥0.8)但存在幻觉 claim → 必须触发纠正"""

    def __init__(self):
        self.n = 0

    def check(self, answer, docs):
        self.n += 1
        if self.n == 1:
            return SimpleNamespace(has_hallucination=True, overall_faithfulness=0.9)
        return SimpleNamespace(has_hallucination=False, overall_faithfulness=0.95)


class TestCorrectionExitCondition:
    def test_hallucination_with_high_faithfulness_still_corrects(self, monkeypatch):
        """P0 回归：整体忠实度高但含幻觉 claim 时，不得跳过纠正"""
        rec = _RecordingRetriever()
        detector = _HighFaithfulnessWithHallucinationDetector()
        cor = SelfCorrector(rec, detector=detector)
        monkeypatch.setattr(cor, "_generate", lambda query, docs: "答案")
        monkeypatch.setattr(cor, "_extract_missing_info", lambda query, check: "补充")

        result = cor.generate_with_docs(
            "q", docs=["初始文档"], sources=["s"], access_level="public"
        )

        # 修复前：or 短路 → was_corrected=False、correction_rounds=0、不重新检索
        # 修复后：进入纠正循环 → 重新检索 + 重新检测
        assert result.was_corrected is True
        assert result.correction_rounds == 1
        assert rec.search_calls == 1  # 纠正循环触发了一次重新检索

    def test_no_hallucination_high_faithfulness_skips_correction(self, monkeypatch):
        """对照组：无幻觉且忠实度达标 → 正常跳过纠正"""
        rec = _RecordingRetriever()
        cor = SelfCorrector(
            rec,
            detector=SimpleNamespace(
                check=lambda a, d: SimpleNamespace(
                    has_hallucination=False, overall_faithfulness=0.95
                )
            ),
        )
        monkeypatch.setattr(cor, "_generate", lambda query, docs: "答案")

        result = cor.generate_with_docs(
            "q", docs=["初始文档"], sources=["s"], access_level="public"
        )

        assert result.was_corrected is False
        assert result.correction_rounds == 0
        assert rec.search_calls == 0  # 未进入纠正循环
