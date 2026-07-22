"""模块12 依赖注入 — FastAPI Depends 工厂"""

from functools import lru_cache

from src.embedding.embedder import Embedder, get_embedder
from src.embedding.milvus_store import MilvusStore
from src.embedding.pipeline import IndexingPipeline
from src.embedding.retriever import Retriever


@lru_cache
def get_store() -> MilvusStore:
    """MilvusStore 单例"""
    return MilvusStore()


@lru_cache
def get_embedder_instance() -> Embedder:
    """Embedder 单例"""
    return get_embedder()


@lru_cache
def get_retriever() -> Retriever:
    """Retriever 单例（Embedder + MilvusStore + Reranker）"""
    return Retriever(
        embedder=get_embedder_instance(),
        store=get_store(),
    )


@lru_cache
def get_pipeline() -> IndexingPipeline:
    """IndexingPipeline 单例（Embedder + MilvusStore）"""
    return IndexingPipeline(
        embedder=get_embedder_instance(),
        store=get_store(),
    )
