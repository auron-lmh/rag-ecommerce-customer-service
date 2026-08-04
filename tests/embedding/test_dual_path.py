"""双路召回 + 合并去重测试"""

from src.embedding.degradation import DegradationStrategy
from src.embedding.models import SearchResponse, SearchResult
from src.embedding.retriever import _merge_results


def _res(chunk_id: str, score: float) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        text=f"文本{chunk_id}",
        score=score,
        source_file=f"{chunk_id}.md",
    )


class TestMergeResults:
    def test_dedupe_keep_highest(self):
        """同一 chunk 两路都命中 → 保留最高分"""
        a = [_res("a", 0.9), _res("b", 0.7)]
        b = [_res("a", 0.8), _res("c", 0.95)]
        merged = _merge_results(a, b)
        assert [r.chunk_id for r in merged] == ["c", "a", "b"]
        # a 保留两路中最高分 0.9
        assert merged[1].score == 0.9

    def test_union_all_unique(self):
        """两路无重复 → 全部保留"""
        a = [_res("a", 0.5)]
        b = [_res("b", 0.6)]
        assert len(_merge_results(a, b)) == 2

    def test_sorted_desc(self):
        """合并结果按分数降序"""
        out = _merge_results([_res("x", 0.3)], [_res("y", 0.6), _res("z", 0.5)])
        scores = [r.score for r in out]
        assert scores == sorted(scores, reverse=True)

    def test_empty_inputs(self):
        assert _merge_results([], []) == []
        assert [r.chunk_id for r in _merge_results([_res("a", 0.9)], [])] == ["a"]


class _FakeRetriever:
    """模拟检索器，统计双路/单路调用"""

    def __init__(self):
        self.dual_calls = 0
        self.single_calls = 0

    def search(self, query, top_k=5, use_rerank=True, **kwargs):
        self.single_calls += 1
        return SearchResponse(
            query=query,
            results=[_res("a", 0.9)],
            total_found=1,
            elapsed_ms=1,
            threshold=0,
        )

    def search_dual_path(
        self, query, secondary_query, top_k=5, use_rerank=True, **kwargs
    ):
        self.dual_calls += 1
        return SearchResponse(
            query=query,
            results=[_res("a", 0.9)],
            total_found=1,
            elapsed_ms=1,
            threshold=0,
        )


class TestDualPathDispatch:
    def test_with_secondary_uses_dual_path(self):
        """提供改写问题 → Level 1 走双路召回"""
        r = _FakeRetriever()
        res = DegradationStrategy(r).search_with_degradation(
            "原始问题", secondary_query="改写问题"
        )
        assert r.dual_calls == 1
        assert r.single_calls == 0
        assert res.level == 1  # 高分命中 Level 1

    def test_without_secondary_uses_single(self):
        """不提供改写问题 → 退化为单路"""
        r = _FakeRetriever()
        DegradationStrategy(r).search_with_degradation("原始问题")
        assert r.single_calls == 1
        assert r.dual_calls == 0

    def test_identical_secondary_falls_back_to_single(self):
        """改写与原始相同 → 避免重复检索，走单路"""
        r = _FakeRetriever()
        DegradationStrategy(r).search_with_degradation(
            "相同问题", secondary_query="相同问题"
        )
        assert r.single_calls == 1
        assert r.dual_calls == 0
