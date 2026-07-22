"""模块2 数据模型 — 分块阶段的数据结构"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.ingestion.models import DocType


class ChunkStrategy(str, Enum):
    """分块策略标识"""

    MARKDOWN = "markdown"  # 按Markdown标题层级切分
    FAQ = "faq"  # Q&A对保整、不拆散
    RECURSIVE = "recursive"  # 递归字符切分（通用降级策略）
    SEMANTIC = "semantic"  # 句子边界切分（保留语义完整）


@dataclass
class Chunk:
    """一个分块 — 最小检索单元

    Attributes:
        chunk_id: 全局唯一标识
        content: 分块文本内容
        char_count: 字符数
        token_count: 估算token数
        chunk_index: 在源文档中的序号 (0-based)
        total_chunks: 源文档总分块数
        source_file: 来源文件路径
        doc_type: 文档类型
        page_number: 页码（PDF文档，从1开始）
        heading_path: 标题路径 ["父标题", "子标题"]
        section_title: 最近标题
        strategy: 使用的分块策略
        overlap_with_prev: 是否与前一个chunk有重叠内容
        overlap_content: 重叠的文本内容
    """

    chunk_id: str
    content: str
    char_count: int
    token_count: int

    chunk_index: int = 0
    total_chunks: int = 1

    source_file: str = ""
    doc_type: DocType | None = None
    page_number: int = 0  # 页码（0表示未知）

    heading_path: list[str] = field(default_factory=list)
    section_title: Optional[str] = None

    strategy: ChunkStrategy = ChunkStrategy.RECURSIVE

    overlap_with_prev: bool = False
    overlap_content: str = ""

    metadata: dict = field(default_factory=dict)


@dataclass
class ChunkResult:
    """一批文档的分块结果汇总"""

    source_file: str
    doc_type: DocType
    strategy: ChunkStrategy
    chunks: list[Chunk]
    total_chars: int
    total_tokens: int

    @property
    def avg_chunk_size(self) -> float:
        if not self.chunks:
            return 0.0
        return self.total_chars / len(self.chunks)

    @property
    def size_stddev(self) -> float:
        """chunk size标准差 — 越小越均匀"""
        if len(self.chunks) < 2:
            return 0.0
        mean = self.avg_chunk_size
        variance = sum((c.char_count - mean) ** 2 for c in self.chunks) / len(
            self.chunks
        )
        return variance**0.5
