"""模块2 策略路由器 — 按 DocType 自动选择最优分块策略

映射规则:
  FAQ_JSON    → FAQSplitter      (Q&A对保整)
  PDF/WORD    → MarkdownSplitter  (标题层级切分)
  PPT/WEB     → SemanticSplitter  (句子边界切分)
  EXCEL/IMAGE → RecursiveSplitter (无明确结构，通用切分)
  PLAIN_TEXT  → RecursiveSplitter
"""

from src.ingestion.models import DocType

from .models import ChunkResult
from .strategies import (
    FAQSplitter,
    MarkdownSplitter,
    RecursiveSplitter,
    SemanticSplitter,
)


def chunk_document(
    text: str,
    source_file: str = "",
    doc_type: DocType | None = None,
    target_size: int = 512,
    min_size: int | None = None,
    max_size: int = 1024,
) -> ChunkResult:
    """统一入口 — 根据文档类型自动选择分块策略

    Args:
        text: Markdown/纯文本内容
        source_file: 来源文件路径
        doc_type: 文档类型（自动选择策略）
        target_size: 目标 chunk 大小 (token)
        min_size: 最小 chunk 大小 (默认 target_size / 5)
        max_size: 最大 chunk 大小 (token)

    Returns:
        ChunkResult（含chunks + 统计信息）
    """
    if min_size is None:
        min_size = max(target_size // 5, 50)

    splitter = _select_splitter(doc_type, target_size, min_size, max_size)

    if isinstance(splitter, FAQSplitter):
        return _wrap_splitter(
            splitter, text, source_file, doc_type, strategy_name="faq"
        )
    elif isinstance(splitter, MarkdownSplitter):
        return _wrap_splitter(
            splitter, text, source_file, doc_type, strategy_name="markdown"
        )
    elif isinstance(splitter, SemanticSplitter):
        return _wrap_splitter(
            splitter, text, source_file, doc_type, strategy_name="semantic"
        )
    else:
        return _wrap_splitter(
            splitter, text, source_file, doc_type, strategy_name="recursive"
        )


def _select_splitter(
    doc_type: DocType | None,
    target_size: int = 512,
    min_size: int = 100,
    max_size: int = 1024,
):
    """根据文档类型选择切分器"""
    mapping = {
        DocType.FAQ_JSON: FAQSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        ),
        DocType.PDF: MarkdownSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        ),
        DocType.WORD: MarkdownSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        ),
        DocType.PPT: SemanticSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        ),
        DocType.EXCEL: RecursiveSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        ),
        DocType.IMAGE: RecursiveSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        ),
        DocType.WEB: SemanticSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        ),
        DocType.PLAIN_TEXT: RecursiveSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        ),
    }
    return mapping.get(
        doc_type,
        RecursiveSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        ),
    )


def _wrap_splitter(
    splitter,
    text: str,
    source_file: str,
    doc_type: DocType | None,
    strategy_name: str,
) -> ChunkResult:
    """包装非BaseSplitter的策略 → 统一ChunkResult输出"""
    from .models import Chunk, ChunkStrategy
    from .token_counter import count_chars, count_tokens

    strategy_map = {
        "faq": ChunkStrategy.FAQ,
        "markdown": ChunkStrategy.MARKDOWN,
        "semantic": ChunkStrategy.SEMANTIC,
        "recursive": ChunkStrategy.RECURSIVE,
    }
    strategy = strategy_map.get(strategy_name, ChunkStrategy.RECURSIVE)

    raw_chunks = splitter.split(text)
    chunks: list[Chunk] = []

    for i, content in enumerate(raw_chunks):
        if not content.strip():
            continue

        chunks.append(
            Chunk(
                chunk_id=_make_chunk_id(source_file, i),
                content=content,
                char_count=count_chars(content),
                token_count=count_tokens(content),
                chunk_index=i,
                source_file=source_file,
                doc_type=doc_type,
                strategy=strategy,
                heading_path=_extract_headings(content),
                section_title=_extract_section_title(content),
            )
        )

    for c in chunks:
        c.total_chunks = len(chunks)

    return ChunkResult(
        source_file=source_file,
        doc_type=doc_type or DocType.PLAIN_TEXT,
        strategy=strategy,
        chunks=chunks,
        total_chars=sum(c.char_count for c in chunks),
        total_tokens=sum(c.token_count for c in chunks),
    )


def _make_chunk_id(source_file: str, index: int) -> str:
    import hashlib

    raw = f"{source_file}#chunk{index}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _extract_headings(text: str) -> list[str]:
    import re

    return re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)


def _extract_section_title(text: str) -> str | None:
    import re

    match = re.search(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)
    return match.group(1) if match else None
