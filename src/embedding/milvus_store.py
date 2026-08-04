"""Milvus 向量存储 — 稠密 + 稀疏(BM25) Hybrid Search

Schema:
  - id: INT64 自增主键
  - text: VARCHAR(8000), 启用 jieba 分词 → BM25 稀疏向量
  - dense: FLOAT_VECTOR(2048), qwen3-vl-embedding
  - sparse: SPARSE_FLOAT_VECTOR, 由 BM25 Function 自动生成
  - doc_type / source_file / heading_path / chunk_metadata

索引:
  - dense: AUTOINDEX (IP 度量)
  - sparse: SPARSE_INVERTED_INDEX (BM25 度量)

参考: PythonProject1 RAG 项目的 milvus_db 模块
"""

import logging
import time
from typing import Optional

from pymilvus import (
    AnnSearchRequest,
    DataType,
    Function,
    FunctionType,
    MilvusClient,
    WeightedRanker,
)

from src.config import settings

from .models import EmbeddingResult, SearchResponse, SearchResult

logger = logging.getLogger(__name__)

COLLECTION_NAME = settings.milvus_collection
DIM = settings.milvus_dim
TEXT_FIELD = "text"
DENSE_FIELD = "dense"
SPARSE_FIELD = "sparse"
MAX_TEXT_LEN = 8000


class MilvusStore:
    """Milvus 向量存储 — 支持 Hybrid Search (dense + sparse)

    使用:
        store = MilvusStore()
        store.create_collection(drop_if_exists=False)
        store.insert(embeddings)
        results = store.hybrid_search(query_vector, query_text, top_k=5)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or settings.milvus_host
        self.port = port or settings.milvus_port
        self.user = user or settings.milvus_user
        self.password = password or settings.milvus_password
        self._uri = f"http://{self.host}:{self.port}"
        self._client: Optional[MilvusClient] = None  # 实例级单例

    @property
    def client(self) -> MilvusClient:
        """获取 MilvusClient 单例（实例级复用，避免每次请求新建连接）"""
        if self._client is None:
            self._client = MilvusClient(
                uri=self._uri, user=self.user, password=self.password, timeout=10
            )
        return self._client

    # ── 健康检查 ──

    def health_check(self) -> bool:
        try:
            self.client.list_collections()
            return True
        except Exception as e:
            logger.warning("Milvus 不可达: %s", e)
            return False

    # ── Collection 生命周期 ──

    def create_collection(self, drop_if_exists: bool = False) -> None:
        """创建带 BM25 + 稠密双索引的 collection"""
        if self.client.has_collection(COLLECTION_NAME):
            if drop_if_exists:
                self.client.drop_collection(COLLECTION_NAME)
                logger.info("已删除旧 collection: %s", COLLECTION_NAME)
            else:
                logger.info("Collection 已存在: %s", COLLECTION_NAME)
                return

        # ── Schema ──
        schema = self.client.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field(
            field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True
        )
        schema.add_field(
            field_name=TEXT_FIELD,
            datatype=DataType.VARCHAR,
            max_length=MAX_TEXT_LEN,
            enable_analyzer=True,
            analyzer_params={"tokenizer": "jieba", "filter": ["cnalphanumonly"]},
        )
        schema.add_field(
            field_name=DENSE_FIELD, datatype=DataType.FLOAT_VECTOR, dim=DIM
        )
        schema.add_field(field_name=SPARSE_FIELD, datatype=DataType.SPARSE_FLOAT_VECTOR)
        schema.add_field(
            field_name="doc_type", datatype=DataType.VARCHAR, max_length=32
        )
        schema.add_field(
            field_name="source_file", datatype=DataType.VARCHAR, max_length=512
        )
        schema.add_field(field_name="heading_path", datatype=DataType.JSON)
        schema.add_field(field_name="chunk_metadata", datatype=DataType.JSON)

        # ── BM25 Function: text → sparse ──
        bm25_fn = Function(
            name="text_bm25",
            input_field_names=[TEXT_FIELD],
            output_field_names=[SPARSE_FIELD],
            function_type=FunctionType.BM25,
        )
        schema.add_function(bm25_fn)

        # ── 索引 ──
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name=SPARSE_FIELD,
            index_name="idx_sparse",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
                "bm25_k1": 1.2,
                "bm25_b": 0.75,
            },
        )
        index_params.add_index(
            field_name=DENSE_FIELD,
            index_name="idx_dense",
            index_type="AUTOINDEX",
            metric_type="IP",
        )

        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            schema=schema,
            index_params=index_params,
        )
        self.client.load_collection(COLLECTION_NAME)
        logger.info("Collection 已创建: %s (BM25+IP, %d-dim)", COLLECTION_NAME, DIM)

    def collection_exists(self) -> bool:
        try:
            return self.client.has_collection(COLLECTION_NAME)
        except Exception:
            return False

    # ── 自检 ──

    def _ensure_ready(self):
        """每次操作前检查: Milvus可达 + collection存在 + 已加载

        优化: 使用 get_load_state 检查，避免每次都调用 load_collection
        """
        if not self.health_check():
            raise ConnectionError(f"Milvus 不可达 ({self._uri})，请检查虚拟机是否运行")
        if not self.collection_exists():
            raise RuntimeError(
                f"Collection '{COLLECTION_NAME}' 不存在，请先调用 create_collection() 或重启应用"
            )
        # 检查加载状态，避免每次都调用 load_collection（重操作）
        try:
            state = self.client.get_load_state(COLLECTION_NAME)
            if state.get("state") != "loaded":
                self.client.load_collection(COLLECTION_NAME)
        except Exception:
            # get_load_state 可能不可用，降级为直接加载
            self.client.load_collection(COLLECTION_NAME)

    # ── 写入 ──

    def insert(self, embeddings: list[EmbeddingResult], batch_size: int = 500) -> int:
        if not embeddings:
            return 0
        self._ensure_ready()
        total = len(embeddings)
        inserted = 0
        logger.info("写入 Milvus: %d 条", total)

        for i in range(0, total, batch_size):
            batch = embeddings[i : i + batch_size]
            entities = [
                {
                    TEXT_FIELD: e.text[:MAX_TEXT_LEN],
                    DENSE_FIELD: e.vector,
                    "doc_type": e.metadata.get("doc_type", ""),
                    "source_file": e.metadata.get("source_file", ""),
                    "heading_path": e.metadata.get("heading_path", []),
                    "chunk_metadata": e.metadata,
                }
                for e in batch
            ]
            try:
                self.client.insert(collection_name=COLLECTION_NAME, data=entities)
                inserted += len(batch)
            except Exception as e:
                logger.error("批次 %d 写入失败: %s", i // batch_size + 1, e)
                raise

        self.client.flush(COLLECTION_NAME)
        logger.info("写入完成: %d/%d 条, 已 flush", inserted, total)
        return inserted

    # ── 检索 ──

    def dense_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_expr: Optional[str] = None,
        threshold: float = 0.0,
    ) -> SearchResponse:
        """纯稠密检索"""
        t0 = time.time()
        self._ensure_ready()

        raw = self.client.search(
            collection_name=COLLECTION_NAME,
            data=[query_vector],
            anns_field=DENSE_FIELD,
            search_params={"metric_type": "IP", "params": {"nprobe": 16}},
            limit=top_k,
            filter=filter_expr,
            output_fields=[TEXT_FIELD, "doc_type", "source_file", "heading_path"],
        )
        return self._build_response("", raw, threshold, time.time() - t0)

    def hybrid_search(
        self,
        query_vector: list[float],
        query_text: str,
        top_k: int = 5,
        sparse_weight: float = 0.3,  # BM25 关键词权重 (辅助)
        dense_weight: float = 0.7,  # 语义向量权重 (主力)
        filter_expr: Optional[str] = None,
        threshold: float = 0.0,
    ) -> SearchResponse:
        """Hybrid Search: BM25 稀疏 + 稠密向量 + WeightedRanker 融合"""
        t0 = time.time()
        self._ensure_ready()

        dense_req = AnnSearchRequest(
            [query_vector],
            DENSE_FIELD,
            {"metric_type": "IP", "params": {"nprobe": 16}},
            limit=top_k,
        )
        sparse_req = AnnSearchRequest(
            [query_text],
            SPARSE_FIELD,
            {"metric_type": "BM25", "params": {"drop_ratio_search": 0.2}},
            limit=top_k,
        )
        ranker = WeightedRanker(sparse_weight, dense_weight)

        raw = self.client.hybrid_search(
            collection_name=COLLECTION_NAME,
            reqs=[sparse_req, dense_req],
            ranker=ranker,
            limit=top_k,
            filter=filter_expr,
            output_fields=[TEXT_FIELD, "doc_type", "source_file", "heading_path"],
        )
        return self._build_response(query_text, raw, threshold, time.time() - t0)

    def _build_response(
        self, query: str, raw_results: list, threshold: float, elapsed: float
    ) -> SearchResponse:
        results: list[SearchResult] = []
        if raw_results and raw_results[0]:
            for hit in raw_results[0]:
                score = hit.get("distance", 0.0)
                if score < threshold:
                    continue
                entity = hit.get("entity", {})
                chunk_metadata = entity.get("chunk_metadata", {}) or {}
                results.append(
                    SearchResult(
                        chunk_id=str(hit.get("id", "")),
                        text=entity.get(TEXT_FIELD, ""),
                        score=round(score, 4),
                        doc_type=entity.get("doc_type", ""),
                        source_file=entity.get("source_file", ""),
                        page_number=chunk_metadata.get("page_number", 0),
                        heading_path=list(entity.get("heading_path", []) or []),
                        metadata=chunk_metadata,  # 改进4: 带时效/版本元数据，供检索层过滤
                    )
                )
        return SearchResponse(
            query=query,
            results=results,
            total_found=len(results),
            elapsed_ms=round(elapsed * 1000, 1),
            threshold=threshold,
        )

    # ── 统计 ──

    def stats(self) -> dict:
        try:
            if not self.client.has_collection(COLLECTION_NAME):
                return {"exists": False, "total_vectors": 0}
            stat = self.client.get_collection_stats(COLLECTION_NAME)
            return {
                "exists": True,
                "collection_name": COLLECTION_NAME,
                "total_vectors": stat.get("row_count", 0),
            }
        except Exception as e:
            logger.warning("统计获取失败: %s", e)
            return {"exists": False, "total_vectors": 0, "error": str(e)}

    def delete_by_source(self, source_file: str) -> int:
        try:
            results = self.client.query(
                collection_name=COLLECTION_NAME,
                filter=f'source_file == "{source_file}"',
                output_fields=["id"],
                limit=10000,
            )
            ids = [r["id"] for r in results]
            if ids:
                self.client.delete(
                    collection_name=COLLECTION_NAME,
                    filter=f'source_file == "{source_file}"',
                )
                logger.info("已删除 %d 条: %s", len(ids), source_file)
            return len(ids)
        except Exception as e:
            logger.error("删除失败: %s", e)
            return 0
