"""milvus_store 存储层权限过滤兜底测试 — 漏传 filter 时默认 public（P1 修复）"""

from src.embedding.milvus_store import MILVUS_ACCESS_FIELD, MilvusStore


class _CapturingClient:
    def __init__(self):
        self.last_filter = None

    def search(self, **kwargs):
        self.last_filter = kwargs.get("filter")
        return [[]]


def test_dense_search_defaults_to_public_filter(monkeypatch):
    store = MilvusStore()
    monkeypatch.setattr(store, "_ensure_ready", lambda: None)
    fake = _CapturingClient()
    store._client = fake

    store.dense_search(query_vector=[0.0] * 2048)

    assert fake.last_filter == f"{MILVUS_ACCESS_FIELD} <= 0"


def test_dense_search_preserves_explicit_filter(monkeypatch):
    store = MilvusStore()
    monkeypatch.setattr(store, "_ensure_ready", lambda: None)
    fake = _CapturingClient()
    store._client = fake

    store.dense_search(
        query_vector=[0.0] * 2048, filter_expr=f"{MILVUS_ACCESS_FIELD} <= 2"
    )

    assert fake.last_filter == f"{MILVUS_ACCESS_FIELD} <= 2"
