"""分块策略抽象基类"""

from abc import ABC, abstractmethod

from src.ingestion.models import DocType

from ..models import Chunk, ChunkResult, ChunkStrategy
from ..token_counter import count_chars, count_tokens


class BaseSplitter(ABC):
    """所有分块策略的基类

    子类只需实现 _split_impl()，其余（chunk_id生成、元数据填充、统计）由基类负责。
    """

    strategy: ChunkStrategy

    def __init__(
        self,
        target_size: int = 512,  # token
        min_size: int = 100,  # token
        max_size: int = 1024,  # token
        overlap: int = 50,  # token
    ):
        self.target_size = target_size
        self.min_size = min_size
        self.max_size = max_size
        self.overlap = overlap

    # ── 公共入口 ──

    def split(
        self, text: str, source_file: str = "", doc_type: DocType | None = None
    ) -> ChunkResult:
        """拆分文本 → ChunkResult（含完整元数据）"""
        raw_chunks = self._split_impl(text)

        # 组装Chunk对象
        chunks: list[Chunk] = []
        total = len(raw_chunks)

        for i, content in enumerate(raw_chunks):
            if not content.strip():
                continue

            char_count = count_chars(content)
            token_count = count_tokens(content)

            # 跳过过小的碎片（合并到前一个或丢弃）
            if token_count < self.min_size and i > 0 and total > 1:
                # 合并到前一个chunk（不独立成块）
                prev = chunks[-1]
                merged = prev.content + "\n\n" + content
                merged_tokens = count_tokens(merged)
                if merged_tokens <= self.max_size:
                    prev.content = merged
                    prev.char_count = count_chars(merged)
                    prev.token_count = merged_tokens
                    prev.total_chunks = len(chunks)
                    continue

            # 重叠内容（从前一个chunk尾部取）
            overlap_content = ""
            overlap_with_prev = False
            if i > 0 and self.overlap > 0 and chunks:
                prev_content = chunks[-1].content
                if len(prev_content) > self.overlap * 2:
                    overlap_content = prev_content[-int(self.overlap * 2) :]
                    overlap_with_prev = True

            chunks.append(
                Chunk(
                    chunk_id=_make_chunk_id(source_file, i),
                    content=content,
                    char_count=char_count,
                    token_count=token_count,
                    chunk_index=i,
                    total_chunks=total,
                    source_file=source_file,
                    doc_type=doc_type,
                    strategy=self.strategy,
                    overlap_with_prev=overlap_with_prev,
                    overlap_content=overlap_content,
                    heading_path=self._extract_headings(content),
                    section_title=self._extract_section_title(content),
                )
            )

        # 更新 total_chunks
        for c in chunks:
            c.total_chunks = len(chunks)

        return ChunkResult(
            source_file=source_file,
            doc_type=doc_type or DocType.PLAIN_TEXT,
            strategy=self.strategy,
            chunks=chunks,
            total_chars=sum(c.char_count for c in chunks),
            total_tokens=sum(c.token_count for c in chunks),
        )

    # ── 子类实现 ──

    @abstractmethod
    def _split_impl(self, text: str) -> list[str]:
        """实际切分逻辑 → 返回原始文本块列表"""
        ...

    # ── 标题提取（子类可覆盖）──

    def _extract_headings(self, text: str) -> list[str]:
        """从文本中提取标题路径"""
        import re

        headings = re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)
        return headings

    def _extract_section_title(self, text: str) -> str | None:
        """提取最近的标题"""
        import re

        match = re.search(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)
        return match.group(1) if match else None


def _make_chunk_id(source_file: str, index: int) -> str:
    import hashlib

    raw = f"{source_file}#chunk{index}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]
