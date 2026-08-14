"""父文档检索补全测试 — 召回子块后补全相邻块上下文（Parent Document Retriever 简化版）"""

from src.embedding.models import SearchResult
from src.embedding.retriever import Retriever


class _StoreWithChunks:
    def __init__(self, chunks):
        self._chunks = chunks

    def query_chunks_by_source(self, source_file):
        return self._chunks


def _r(chunk_id, text, chunk_index):
    return SearchResult(
        chunk_id=chunk_id,
        text=text,
        score=0.9,
        source_file="test.txt",
        metadata={"chunk_index": chunk_index},
    )


def test_expand_parent_context_adds_neighbors():
    chunks = [
        {"chunk_id": "0", "text": "块0", "chunk_index": 0},
        {"chunk_id": "1", "text": "块1", "chunk_index": 1},
        {"chunk_id": "2", "text": "块2", "chunk_index": 2},
    ]
    retriever = Retriever.__new__(Retriever)
    retriever.store = _StoreWithChunks(chunks)

    docs = [_r("1", "块1", 1)]
    expanded = retriever.expand_parent_context(docs, window=1)

    # 块1 前后相邻块（块0、块2）应补进 text
    assert "块0" in expanded[0].text
    assert "块2" in expanded[0].text
    assert "块1" in expanded[0].text


def test_expand_parent_window_zero_is_noop():
    retriever = Retriever.__new__(Retriever)
    retriever.store = _StoreWithChunks([])

    docs = [_r("1", "块1", 1)]
    expanded = retriever.expand_parent_context(docs, window=0)

    # window=0 不补全，原样返回
    assert expanded[0].text == "块1"
