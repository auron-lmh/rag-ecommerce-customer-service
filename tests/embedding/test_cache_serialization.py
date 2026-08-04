"""SearchResponse 缓存序列化 round-trip 测试（Redis JSON 序列化修复）"""

from src.embedding.models import SearchResponse, SearchResult
from src.embedding.retriever import _dict_to_search_response, _search_response_to_dict


def _resp() -> SearchResponse:
    return SearchResponse(
        query="怎么退货",
        results=[
            SearchResult(
                chunk_id="c1",
                text="文本1",
                score=0.9,
                source_file="a.md",
                metadata={"effective_to": "2026-08-01"},
            ),
            SearchResult(chunk_id="c2", text="文本2", score=0.5, source_file="b.md"),
        ],
        total_found=2,
        elapsed_ms=12.3,
        threshold=0.7,
    )


def test_roundtrip_preserves_fields():
    r = _resp()
    d = _search_response_to_dict(r)
    r2 = _dict_to_search_response(d)
    assert r2.query == r.query
    assert r2.total_found == r.total_found
    assert r2.elapsed_ms == r.elapsed_ms
    assert r2.threshold == r.threshold
    assert [x.chunk_id for x in r2.results] == ["c1", "c2"]
    assert r2.results[0].metadata["effective_to"] == "2026-08-01"
    assert r2.results[1].score == 0.5


def test_roundtrip_empty_results():
    r = SearchResponse(query="q", results=[], total_found=0, elapsed_ms=0, threshold=0)
    r2 = _dict_to_search_response(_search_response_to_dict(r))
    assert r2.results == []
    assert r2.total_found == 0


def test_dict_is_json_serializable():
    """序列化后的 dict 必须能被 json.dumps（Redis 缓存要求）"""
    import json

    d = _search_response_to_dict(_resp())
    json.dumps(d, ensure_ascii=False)  # 不抛异常即通过
