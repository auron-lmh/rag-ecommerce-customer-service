"""RRF 融合测试 — 按排名融合，不看分数尺度（P1 修复）"""

from src.embedding.models import SearchResponse, SearchResult
from src.embedding.retriever import Retriever


def _r(chunk_id, score):
    return SearchResult(chunk_id=chunk_id, text=chunk_id, score=score, source_file="s")


def test_rrf_ranks_by_rank_not_score():
    """RRF 按排名融合，而非分数尺度——dense 里 rank1 和 sparse 里 rank1 的文档应靠前"""
    retriever = Retriever.__new__(Retriever)  # 跳过 __init__（不连 Milvus）

    # dense: A rank1, B rank2；sparse: B rank1, A rank2 → A、B 都是 1/(60+1)+1/(60+2)
    dense = SearchResponse(
        query="q",
        results=[_r("A", 0.95), _r("B", 0.80)],
        total_found=2,
        elapsed_ms=1,
        threshold=0.7,
    )
    sparse = SearchResponse(
        query="q",
        results=[_r("B", 25.0), _r("A", 20.0)],  # BM25 分数尺度完全不同
        total_found=2,
        elapsed_ms=1,
        threshold=0,
    )

    fused = retriever._rrf_fusion(dense, sparse, "q")

    # A 和 B 的 RRF 分数相同（都在两路里 rank1/rank2），都应保留
    ids = [r.chunk_id for r in fused.results]
    assert set(ids) == {"A", "B"}


def test_rrf_prefers_doc_high_in_both():
    """两路都排名靠前的文档 > 只在单路排名靠前的文档"""
    retriever = Retriever.__new__(Retriever)

    dense = SearchResponse(
        query="q",
        results=[_r("A", 0.95), _r("C", 0.50)],
        total_found=2,
        elapsed_ms=1,
        threshold=0.7,
    )
    sparse = SearchResponse(
        query="q",
        results=[_r("A", 30.0), _r("B", 28.0)],
        total_found=2,
        elapsed_ms=1,
        threshold=0,
    )

    fused = retriever._rrf_fusion(dense, sparse, "q")

    # A 在两路都是 rank1，应排第一
    assert fused.results[0].chunk_id == "A"
