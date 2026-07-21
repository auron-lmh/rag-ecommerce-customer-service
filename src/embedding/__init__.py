"""模块3: 向量化 + 向量存储 + 检索

Qwen3-VL-Embedding (DashScope API) → Milvus 存储 → Hybrid 语义检索 + Reranker

使用:
    from src.embedding import Retriever, IndexingPipeline

    # 检索
    retriever = Retriever()
    results = retriever.search("如何退货?")

    # 入库
    pipeline = IndexingPipeline()
    report = pipeline.run_from_text(markdown_text, "policy.pdf", DocType.PDF)
"""

from .embedder import Embedder, get_embedder
from .milvus_store import MilvusStore
from .models import EmbeddingResult, SearchResponse, SearchResult
from .pipeline import IndexingPipeline
from .retriever import Retriever
