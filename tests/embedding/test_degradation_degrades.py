"""degradation 降级异常测试 — 检索抛异常时降级到兜底，不崩溃（P1 修复）"""

from src.embedding.degradation import DegradationStrategy
from src.embedding.models import SearchResponse


class _ThrowingRetriever:
    def search(self, *args, **kwargs):
        raise ConnectionError("Milvus 不可达")

    def search_dual_path(self, *args, **kwargs):
        raise ConnectionError("Milvus 不可达")

    @property
    def reranker(self):
        return None


def test_degrades_to_fallback_when_retrieval_raises(monkeypatch):
    """Level 1/2 检索抛异常 → 降级到兜底，不崩溃"""
    strat = DegradationStrategy(_ThrowingRetriever())
    monkeypatch.setattr(strat, "_web_search", lambda q: [])
    monkeypatch.setattr(strat, "_rewrite_query", lambda q, a: q)
    monkeypatch.setattr(
        strat,
        "_expand_and_search",
        lambda *a, **kw: SearchResponse(
            query="", results=[], total_found=0, elapsed_ms=0, threshold=0.7
        ),
    )

    result = strat.search_with_degradation("怎么退货")

    assert result.level == 5  # 最终降级到兜底
    assert result.response.total_found == 0
