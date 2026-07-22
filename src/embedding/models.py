"""模块3 数据模型 — 向量化与存储阶段的数据结构"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EmbeddingResult:
    """单条 embedding 结果

    Attributes:
        chunk_id: 对应 Chunk.chunk_id
        vector: 2048-dim float32 向量 (qwen3-vl-embedding)
        text: 原始文本（存 Milvus 用于调试/全文回退）
        metadata: 透传的元数据（doc_type, source_file, heading_path 等）
    """

    chunk_id: str
    vector: list[float]
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class BatchEmbeddingResult:
    """批量 embedding 结果汇总"""

    embeddings: list[EmbeddingResult]
    total: int
    dimension: int
    model_name: str
    elapsed_seconds: float
    errors: list[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """单条检索结果"""

    chunk_id: str
    text: str
    score: float  # 余弦相似度或 L2 距离
    doc_type: str = ""
    source_file: str = ""
    page_number: int = 0  # 页码（0表示未知）
    heading_path: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResponse:
    """一次检索的完整响应"""

    query: str
    results: list[SearchResult]
    total_found: int
    elapsed_ms: float
    threshold: float = 0.0  # 最低相似度阈值
