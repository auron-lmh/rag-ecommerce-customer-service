"""模块13 检索权限透传 — filter_expr 构造 / 缓存 key 隔离 / 双路&批量透传

伪 store 捕获每次检索收到的 filter_expr 与调用次数，
验证权限过滤在向量检索阶段生效、缓存 key 含 access_level。
"""

import numpy as np

from src.access import build_access_filter_expr
from src.embedding.models import SearchResponse
from src.embedding.retriever import Retriever
from src.engineering.cache import CacheManager, MemoryCache


class _FakeEmbedder:
    def embed_query(self, query):
        return np.zeros(8, dtype=np.float32)

    def embed_queries(self, queries):
        return [np.zeros(8, dtype=np.float32) for _ in queries]


class _FakeStore:
    """记录每次检索的 filter_expr 和调用次数"""

    def __init__(self):
        self.filters: list[str | None] = []
        self.calls = 0

    def _resp(self, query):
        return SearchResponse(
            query=query,
            results=[],
            total_found=0,
            elapsed_ms=1,
            threshold=0,
        )

    def hybrid_search(
        self,
        query_vector,
        query_text,
        top_k,
        filter_expr=None,
        threshold=None,
        sparse_weight=0.3,
        dense_weight=0.7,
        **kwargs,
    ):
        self.calls += 1
        self.filters.append(filter_expr)
        return self._resp(query_text)

    def dense_search(
        self,
        query_vector,
        top_k,
        filter_expr=None,
        threshold=None,
        **kwargs,
    ):
        self.calls += 1
        self.filters.append(filter_expr)
        return self._resp("")


def _make_retriever(store=None):
    return Retriever(embedder=_FakeEmbedder(), store=store or _FakeStore())


class TestFilterExpr:
    def test_member_gets_access_filter(self):
        store = _FakeStore()
        r = _make_retriever(store)
        r.search("怎么退货", use_rerank=False, access_level="member")
        assert store.filters[-1] == "access_level <= 1"

    def test_vip_gets_wider_filter(self):
        store = _FakeStore()
        r = _make_retriever(store)
        r.search("怎么退货", use_rerank=False, access_level="vip")
        assert store.filters[-1] == "access_level <= 2"

    def test_combined_with_doc_type(self):
        store = _FakeStore()
        r = _make_retriever(store)
        r.search(
            "退货政策",
            use_rerank=False,
            filter_by_doc_type="pdf",
            access_level="member",
        )
        assert store.filters[-1] == 'doc_type == "pdf" && access_level <= 1'

    def test_invalid_level_failsafe_to_public(self):
        store = _FakeStore()
        r = _make_retriever(store)
        r.search("x", use_rerank=False, access_level="superadmin")
        # fail-safe: 非法等级 → 最严 public(0)，不泄漏
        assert store.filters[-1] == "access_level <= 0"


class TestCacheKeyIsolation:
    def test_same_query_different_level_does_not_share_cache(self, monkeypatch):
        """核心泄漏防护: 同 query 不同权限 → 缓存 key 不同 → 各自独立检索"""
        store = _FakeStore()
        r = _make_retriever(store)
        cache = CacheManager(backend=MemoryCache())
        monkeypatch.setattr("src.embedding.retriever._get_cache", lambda: cache)

        r.search("退货政策", use_rerank=False, access_level="vip")  # vip 检索写入缓存
        assert store.calls == 1

        r.search(
            "退货政策", use_rerank=False, access_level="member"
        )  # member 不得命中 vip 缓存
        assert store.calls == 2  # 重新走 Milvus，带 member 过滤

        r.search(
            "退货政策", use_rerank=False, access_level="member"
        )  # member 再查 → 命中自己缓存
        assert store.calls == 2  # 未再触发 Milvus


class TestDualPathAndBatch:
    def test_dual_path_forwards_access_level(self):
        store = _FakeStore()
        r = _make_retriever(store)
        r.search_dual_path("退货要什么", "退货需要哪些材料", access_level="member")
        # 双路内部两次 search 都带 member 过滤
        assert all(f == "access_level <= 1" for f in store.filters[-2:])

    def test_batch_forwards_access_level(self):
        store = _FakeStore()
        r = _make_retriever(store)
        r.search_batch(["q1", "q2"], access_level="vip")
        assert all(f == "access_level <= 2" for f in store.filters[-2:])


def test_build_access_filter_expr_consistency():
    assert build_access_filter_expr("member") == "access_level <= 1"
