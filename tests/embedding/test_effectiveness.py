"""政策时效过滤测试 — 过期/未生效文档剔除（改进4）"""

from src.embedding.models import SearchResult
from src.embedding.retriever import _filter_by_effectiveness


def _result(
    chunk_id: str, effective_from: str = "", effective_to: str = ""
) -> SearchResult:
    meta = {}
    if effective_from:
        meta["effective_from"] = effective_from
    if effective_to:
        meta["effective_to"] = effective_to
    return SearchResult(chunk_id=chunk_id, text="t", score=0.9, metadata=meta)


class TestEffectivenessFilter:
    def test_no_effectiveness_kept(self):
        """未设时效窗口 → 全部保留（默认永不过期）"""
        results = [_result("a"), _result("b")]
        out = _filter_by_effectiveness(results, today="2026-07-01")
        assert [r.chunk_id for r in out] == ["a", "b"]

    def test_expired_removed(self):
        """已过期（effective_to < today）→ 剔除"""
        results = [_result("a"), _result("b", effective_to="2026-06-01")]
        out = _filter_by_effectiveness(results, today="2026-07-01")
        assert [r.chunk_id for r in out] == ["a"]

    def test_not_yet_effective_removed(self):
        """未生效（effective_from > today）→ 剔除"""
        results = [_result("a", effective_from="2026-08-01"), _result("b")]
        out = _filter_by_effectiveness(results, today="2026-07-01")
        assert [r.chunk_id for r in out] == ["b"]

    def test_active_window_kept(self):
        """生效窗口内 → 保留"""
        results = [_result("a", effective_from="2026-06-01", effective_to="2026-08-01")]
        out = _filter_by_effectiveness(results, today="2026-07-01")
        assert [r.chunk_id for r in out] == ["a"]

    def test_boundary_equal_kept(self):
        """生效/过期边界当天 → 视为有效（>= / <=）"""
        results = [_result("a", effective_to="2026-07-01")]
        out = _filter_by_effectiveness(results, today="2026-07-01")
        assert [r.chunk_id for r in out] == ["a"]

    def test_empty_input(self):
        assert _filter_by_effectiveness([], today="2026-07-01") == []

    def test_default_today(self):
        """不传 today 时用系统日期，不应抛异常"""
        results = [_result("a"), _result("b", effective_to="2000-01-01")]
        out = _filter_by_effectiveness(results)
        assert [r.chunk_id for r in out] == ["a"]
