"""模块13 降级检索权限透传 — 各级检索都必须携带 access_level"""

from src.embedding.degradation import DegradationStrategy
from src.embedding.models import SearchResponse, SearchResult


def _res(chunk_id: str = "c", score: float = 0.99) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        text=f"文本{chunk_id}",
        score=score,
        source_file=f"{chunk_id}.md",
    )


class _RecordingRetriever:
    """记录每次检索收到的 access_level"""

    def __init__(self):
        self.search_calls: list[tuple[str, str | None]] = []
        self.dual_calls: list[tuple[str, str, str | None]] = []
        self.reranker = None

    def search(self, query, top_k=5, use_rerank=True, **kwargs):
        self.search_calls.append((query, kwargs.get("access_level")))
        return SearchResponse(
            query=query,
            results=[_res()],
            total_found=1,
            elapsed_ms=1,
            threshold=0,
        )

    def search_dual_path(
        self, query, secondary_query, top_k=5, use_rerank=True, **kwargs
    ):
        self.dual_calls.append((query, secondary_query, kwargs.get("access_level")))
        return SearchResponse(
            query=query,
            results=[_res()],
            total_found=1,
            elapsed_ms=1,
            threshold=0,
        )


class TestDegradationThreadsAccessLevel:
    def test_level1_single_forwards(self):
        """简单查询 → Level 1 单路 search 带 access_level"""
        rec = _RecordingRetriever()
        strategy = DegradationStrategy(rec)
        strategy.search_with_degradation("怎么退货", access_level="member")
        assert rec.search_calls[0][1] == "member"

    def test_level1_dual_forwards(self):
        """提供改写问题 → Level 1 双路 search_dual_path 带 access_level"""
        rec = _RecordingRetriever()
        strategy = DegradationStrategy(rec)
        strategy.search_with_degradation(
            "退货要什么", secondary_query="退货需要哪些材料", access_level="vip"
        )
        assert rec.dual_calls[0][2] == "vip"

    def test_default_is_public(self):
        """漏传 access_level → 默认 public（fail-safe 最低权限）"""
        rec = _RecordingRetriever()
        strategy = DegradationStrategy(rec)
        strategy.search_with_degradation("怎么退货")
        assert rec.search_calls[0][1] == "public"


class _FakeExpander:
    def expand(self, query):
        return {"queries": ["子问题1", "子问题2"], "hyde_doc": "假设答案文档"}


class TestExpandAndSearchThreads:
    def test_subqueries_and_hyde_forwards(self, monkeypatch):
        """Level 0/3 查询扩展: 并行子查询 + HyDE 检索都带 access_level"""
        rec = _RecordingRetriever()
        strategy = DegradationStrategy(rec)
        monkeypatch.setattr(
            "src.embedding.query_expansion.get_query_expander", lambda: _FakeExpander()
        )

        strategy._expand_and_search("q", top_k=5, access_level="member")

        # 2 个子查询 + 1 个 HyDE = 3 次 search，全部带 member
        assert len(rec.search_calls) == 3
        assert all(lv == "member" for _, lv in rec.search_calls)
