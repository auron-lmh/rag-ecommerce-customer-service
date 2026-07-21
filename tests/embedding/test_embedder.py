"""模块3测试 — Embedder / 数据模型 / Pipeline

注意: Embedder 单元测试需要 BAILIAN_API_KEY (DashScope API)。
    标记为 @pytest.mark.slow 的测试需要网络 + API Key。
    标记为 @pytest.mark.integration 的测试需要 Milvus + API Key。
"""

import numpy as np
import pytest

from src.embedding.embedder import Embedder, get_embedder
from src.embedding.milvus_store import MilvusStore
from src.embedding.models import (
    BatchEmbeddingResult,
    EmbeddingResult,
    SearchResponse,
    SearchResult,
)
from src.embedding.pipeline import IndexingPipeline
from src.embedding.retriever import Retriever

# ═══════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════


class TestEmbeddingResult:
    def test_create(self):
        r = EmbeddingResult(
            chunk_id="abc123",
            vector=[0.1, 0.2, 0.3],
            text="测试文本",
            metadata={"doc_type": "pdf"},
        )
        assert r.chunk_id == "abc123"
        assert len(r.vector) == 3
        assert r.metadata["doc_type"] == "pdf"

    def test_batch_result_summary(self):
        r = BatchEmbeddingResult(
            embeddings=[],
            total=100,
            dimension=1024,
            model_name="bge-m3",
            elapsed_seconds=5.2,
            errors=["batch[10:20]: timeout"],
        )
        assert r.total == 100
        assert r.dimension == 1024
        assert len(r.errors) == 1


class TestSearchResult:
    def test_create(self):
        r = SearchResult(
            chunk_id="c1",
            text="退货政策内容",
            score=0.95,
            doc_type="pdf",
            source_file="policy.pdf",
            heading_path=["售后服务", "退货说明"],
        )
        assert r.score == 0.95
        assert len(r.heading_path) == 2

    def test_search_response(self):
        r = SearchResponse(
            query="怎么退货",
            results=[
                SearchResult(chunk_id="c1", text="...", score=0.92),
                SearchResult(chunk_id="c2", text="...", score=0.85),
            ],
            total_found=2,
            elapsed_ms=12.5,
            threshold=0.7,
        )
        assert r.total_found == 2
        assert r.results[0].score == 0.92


# ═══════════════════════════════════════
# Embedder 单元测试 (需要模型下载, 标记为 slow)
# ═══════════════════════════════════════


@pytest.mark.slow
class TestEmbedder:
    def test_singleton(self):
        e1 = get_embedder()
        e2 = get_embedder()
        assert e1 is e2  # 同一个实例

    def test_dimension(self):
        e = get_embedder()
        dim = e.dimension
        from src.config import settings

        assert dim == settings.embedding_dim

    def test_embed_single_query(self):
        e = get_embedder()
        from src.config import settings

        vec = e.embed_query("测试查询文本")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (settings.embedding_dim,)
        # L2归一化 → 范数 ≈ 1.0
        assert abs(np.linalg.norm(vec) - 1.0) < 0.01

    def test_embed_multiple_queries(self):
        e = get_embedder()
        from src.config import settings

        queries = ["第一个查询", "第二个查询", "第三个查询"]
        vecs = e.embed_queries(queries)
        assert vecs.shape == (3, settings.embedding_dim)

    def test_embed_chunks_batch(self):
        e = get_embedder()
        from src.config import settings

        texts = [f"测试文本 {i}" for i in range(10)]
        ids = [f"chunk_{i}" for i in range(10)]
        result = e.embed_chunks(texts, ids, show_progress=False)
        assert result.total == 10
        assert result.dimension == settings.embedding_dim
        assert len(result.embeddings) == 10
        assert result.errors == []

    def test_embed_empty(self):
        e = get_embedder()
        result = e.embed_chunks([], [], show_progress=False)
        assert result.total == 0
        assert len(result.embeddings) == 0

    def test_embed_large_batch(self):
        """测试超过 batch_size 的批量处理 (API batch_size=20)"""
        e = get_embedder()
        n = 70  # > batch_size(20)
        texts = [f"测试文本 {i}" for i in range(n)]
        ids = [f"chunk_{i}" for i in range(n)]
        result = e.embed_chunks(texts, ids, show_progress=False)
        assert result.total == n
        assert len(result.embeddings) == n


# ═══════════════════════════════════════
# MilvusStore 离线测试 (不需要真实连接)
# ═══════════════════════════════════════


class TestMilvusStoreOffline:
    def test_create_instance(self):
        store = MilvusStore(host="localhost", port=19530)
        assert store.host == "localhost"
        assert store.port == 19530


# ═══════════════════════════════════════
# Pipeline / Retriever 实例化测试
# ═══════════════════════════════════════


class TestPipelineInstantiation:
    def test_create_pipeline(self):
        pipeline = IndexingPipeline()
        assert pipeline.embedder is not None
        assert pipeline.store is not None

    def test_create_retriever(self):
        retriever = Retriever()
        assert retriever.embedder is not None
        assert retriever.store is not None


# ═══════════════════════════════════════
# 集成测试标记 (需要 Milvus + 模型)
# ═══════════════════════════════════════


@pytest.mark.integration
class TestMilvusIntegration:
    """这些测试需要 Milvus 运行 + BGE-M3 模型已下载"""

    def test_milvus_health_check(self):
        store = MilvusStore()
        ok = store.health_check()
        assert ok, "Milvus 连接失败，请确认虚拟机 Milvus 正在运行"

    def test_create_collection_and_insert(self):
        store = MilvusStore()
        store.create_collection(drop_if_exists=True)

        # 生成测试向量
        embedder = get_embedder()
        texts = ["测试文本1", "测试文本2", "测试文本3"]
        ids = ["test_1", "test_2", "test_3"]
        batch = embedder.embed_chunks(texts, ids, show_progress=False)

        n = store.insert(batch.embeddings)
        assert n == 3

        stats = store.stats()
        assert stats["total_vectors"] >= 3

    def test_search(self):
        embedder = get_embedder()
        store = MilvusStore()

        query_vec = embedder.embed_query("测试")
        response = store.hybrid_search(query_vec.tolist(), "测试", top_k=2)
        assert response.total_found >= 1
        assert response.results[0].score > 0.0

    def test_end_to_end_pipeline(self):
        from src.ingestion.models import DocType

        pipeline = IndexingPipeline()
        text = "# 售后服务政策\n\n## 退货说明\n\n用户可在签收后7天内申请退货。\n\n## 退款流程\n\n退款在1-3个工作日内到账。"
        report = pipeline.run_from_text(
            text, "test_policy.pdf", DocType.PDF, recreate_collection=True
        )
        assert report["status"] in ("ok", "partial")
        assert report["total_chunks"] > 0

    def test_retriever(self):
        retriever = Retriever()
        # qwen3-vl-embedding 2048-dim + IP 度量
        response = retriever.search("退货", top_k=3, threshold=0.3)
        assert response.total_found >= 1
        assert response.results[0].score > 0.0
