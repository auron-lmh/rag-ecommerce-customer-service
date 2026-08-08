"""模块33 自纠正权限透传 — 初始检索 + 纠正循环重新检索都必须带 access_level

★ workflow 空 docs 兜底会触发 generate_with_correction 内部再检索，
   这一环漏传 = 受限用户"检索空→自行重搜"时无过滤漏检索（头号隐性泄漏路径）。
"""

from types import SimpleNamespace

from src.embedding.models import SearchResponse, SearchResult
from src.generation.self_correction import SelfCorrector


def _res():
    return SearchResult(chunk_id="c", text="文本", score=0.9, source_file="s.md")


class _RecordingRetriever:
    def __init__(self):
        self.search_calls: list[tuple[str, str | None]] = []

    def search(self, query, top_k=5, use_rerank=True, **kwargs):
        self.search_calls.append((query, kwargs.get("access_level")))
        return SearchResponse(
            query=query,
            results=[_res()],
            total_found=1,
            elapsed_ms=1,
            threshold=0,
        )


class _AlwaysPassDetector:
    """幻觉检测永远通过 → 不进入纠正循环"""

    def check(self, answer, docs):
        return SimpleNamespace(has_hallucination=False, overall_faithfulness=1.0)


class _FirstFailDetector:
    """第一次检测失败 → 触发纠正循环 → 第二次通过"""

    def __init__(self):
        self.n = 0

    def check(self, answer, docs):
        self.n += 1
        if self.n == 1:
            return SimpleNamespace(has_hallucination=True, overall_faithfulness=0.3)
        return SimpleNamespace(has_hallucination=False, overall_faithfulness=0.95)


class TestSelfCorrectionThreads:
    def test_initial_search_forwards(self, monkeypatch):
        """generate_with_correction 初始检索带 access_level"""
        rec = _RecordingRetriever()
        cor = SelfCorrector(rec, detector=_AlwaysPassDetector())
        monkeypatch.setattr(cor, "_generate", lambda query, docs: "答案")

        cor.generate_with_correction("怎么退货", access_level="member")

        assert rec.search_calls[0][1] == "member"

    def test_correction_loop_search_forwards(self, monkeypatch):
        """纠正循环重新检索带 access_level（最易漏传的一环）"""
        rec = _RecordingRetriever()
        cor = SelfCorrector(rec, detector=_FirstFailDetector())
        monkeypatch.setattr(cor, "_generate", lambda query, docs: "答案")
        monkeypatch.setattr(
            cor, "_extract_missing_info", lambda query, check: "缺货信息"
        )

        cor.generate_with_docs(
            "q", docs=["初始文档"], sources=["s"], access_level="vip"
        )

        # 纠正轮触发一次重新检索，必须带 vip
        assert any(lv == "vip" for _, lv in rec.search_calls)

    def test_default_is_public(self, monkeypatch):
        """漏传 → 默认 public"""
        rec = _RecordingRetriever()
        cor = SelfCorrector(rec, detector=_AlwaysPassDetector())
        monkeypatch.setattr(cor, "_generate", lambda query, docs: "答案")

        cor.generate_with_correction("q")

        assert rec.search_calls[0][1] == "public"
