"""复杂查询主动分解 + 并行检索测试"""

from src.embedding.degradation import DegradationStrategy, _is_complex_query
from src.embedding.models import SearchResponse, SearchResult


def _res(chunk_id: str, score: float = 0.9) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        text=f"文本{chunk_id}",
        score=score,
        source_file=f"{chunk_id}.md",
    )


class TestIsComplexQuery:
    def test_strong_compare_marker(self):
        assert _is_complex_query("A和B有什么区别") is True

    def test_two_weak_markers(self):
        assert _is_complex_query("同时查A和B的性能") is True

    def test_single_weak_marker_not_complex(self):
        """单次弱标记（和运费）→ 不误判为复杂"""
        assert _is_complex_query("退货和运费怎么算") is False

    def test_plain_query_not_complex(self):
        assert _is_complex_query("怎么退货") is False

    def test_empty_query(self):
        assert _is_complex_query("") is False
        assert _is_complex_query(None) is False


class _FakeRetriever:
    def __init__(self):
        self.search_calls = 0
        self.reranker = None

    def search(self, query, top_k=5, use_rerank=True, **kwargs):
        self.search_calls += 1
        return SearchResponse(
            query=query,
            results=[_res("a")],
            total_found=1,
            elapsed_ms=1,
            threshold=0,
        )

    def search_dual_path(
        self, query, secondary_query, top_k=5, use_rerank=True, **kwargs
    ):
        self.search_calls += 1
        return SearchResponse(
            query=query,
            results=[_res("a")],
            total_found=1,
            elapsed_ms=1,
            threshold=0,
        )


class TestProactiveDecomposition:
    def test_complex_query_uses_decomposition(self, monkeypatch):
        """复杂查询 → 主动分解，不走常规单路检索"""
        r = _FakeRetriever()
        s = DegradationStrategy(r)
        monkeypatch.setattr(
            s,
            "_expand_and_search",
            lambda q, k, access_level="public": SearchResponse(
                query=q,
                results=[_res("a", 0.9)],
                total_found=1,
                elapsed_ms=1,
                threshold=0,
            ),
        )
        res = s.search_with_degradation("A和B有什么区别", use_rerank=False)
        assert res.method == "decomposed"
        assert res.level == 1
        assert r.search_calls == 0  # 未走常规单路

    def test_complex_but_insufficient_falls_to_dual_path(self, monkeypatch):
        """分解结果不足 → 降级走双路召回（不影响降级链路）"""
        r = _FakeRetriever()
        s = DegradationStrategy(r)
        monkeypatch.setattr(
            s,
            "_expand_and_search",
            lambda q, k, access_level="public": SearchResponse(
                query=q,
                results=[_res("a", 0.3)],
                total_found=1,
                elapsed_ms=1,
                threshold=0,
            ),
        )
        res = s.search_with_degradation("A和B有什么区别", use_rerank=False)
        assert r.search_calls >= 1  # 走了 Level 1 常规检索

    def test_plain_query_skips_decomposition(self):
        """普通查询 → 不触发分解"""
        r = _FakeRetriever()
        s = DegradationStrategy(r)
        s._expand_and_search = lambda q, k: (_ for _ in ()).throw(
            AssertionError("普通查询不应调用分解")
        )
        res = s.search_with_degradation("怎么退货", use_rerank=False)
        assert r.search_calls >= 1
