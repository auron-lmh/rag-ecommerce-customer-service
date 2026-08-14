"""模块2 策略路由器 — 按 DocType + 内容形态自动选择最优分块策略

映射规则:
  FAQ_JSON    → FAQSplitter      (Q&A对保整)
  PDF/WORD    → MarkdownSplitter  (标题层级切分)
  PPT/WEB     → SemanticSplitter  (句子边界切分)
  EXCEL/IMAGE → RecursiveSplitter (无明确结构，通用切分)
  PLAIN_TEXT  → RecursiveSplitter

★ 内容优先 (改进A): 任何类型文本若检测为 QA 问答形式
  （如 PDF 解析出的 FAQ、带问答案例的手册），优先走 FAQSplitter，
  保证 Q&A 对不拆散——即使 doc_type 是 PDF/WORD。
★ base64 图片剥离 (改进C): 入库 chunk 内容剔除 data URI 内嵌图片，
  避免污染向量化 / token 统计 / LLM 上下文（原始 Markdown 保留给 UI 预览）。
"""

import re

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
    overlap: int = 80,
) -> ChunkResult:
    """统一入口 — 根据文档类型自动选择分块策略

    Args:
        text: Markdown/纯文本内容
        source_file: 来源文件路径
        doc_type: 文档类型（自动选择策略）
        target_size: 目标 chunk 大小 (token)
        min_size: 最小 chunk 大小 (默认 target_size / 5)
        max_size: 最大 chunk 大小 (token)
        overlap: 相邻 chunk 重叠字符数（默认 80，约 target_size=512 token 的 10%）。
                 重叠保留边界上下文，避免检索时语义被 chunk 边界切断。

    Returns:
        ChunkResult（含chunks + 统计信息）
    """
    if min_size is None:
        min_size = max(target_size // 5, 50)

    splitter = _select_splitter(text, doc_type, target_size, min_size, max_size)

    if isinstance(splitter, FAQSplitter):
        return _wrap_splitter(
            splitter, text, source_file, doc_type, strategy_name="faq", overlap=overlap
        )
    elif isinstance(splitter, MarkdownSplitter):
        return _wrap_splitter(
            splitter,
            text,
            source_file,
            doc_type,
            strategy_name="markdown",
            overlap=overlap,
        )
    elif isinstance(splitter, SemanticSplitter):
        return _wrap_splitter(
            splitter,
            text,
            source_file,
            doc_type,
            strategy_name="semantic",
            overlap=overlap,
        )
    else:
        return _wrap_splitter(
            splitter,
            text,
            source_file,
            doc_type,
            strategy_name="recursive",
            overlap=overlap,
        )


# ═══════════════════════════════════════
# 内容形态检测（改进A + 改进C）
# ═══════════════════════════════════════

# QA 形式检测模式（用于内容优先路由到 FAQSplitter）
_QA_DETECT_PATTERNS = [
    r"^#{2,6}\s*Q\d*[：:.]\s*\S",  # ## Q1: xxx / ### Q: xxx
    r"^Q\d+[、.．\s：:]\s*\S",  # Q1：xxx / Q1. xxx / Q1、xxx
    r"^问[：:]\s*\S",  # 问：xxx
    r"^\*\*Q\d*[：:.]",  # **Q1:** xxx
]


def _looks_like_faq(text: str | None) -> bool:
    """检测文本是否为 FAQ 问答形式（至少出现 2 个 QA 标记）

    用于: PDF/WORD 等解析出 Q&A 内容时，自动切换 FAQ 保整策略。
    要求 ≥2 个标记，避免把普通正文误判为问答。
    """
    if not text:
        return False
    count = 0
    for pattern in _QA_DETECT_PATTERNS:
        count += len(re.findall(pattern, text, re.MULTILINE))
        if count >= 2:
            return True
    return False


def _has_markdown_headings(text: str | None) -> bool:
    """检测文本是否含 Markdown 标题结构（如 .md 文档）

    改进: .md 文件此前走 PLAIN_TEXT→RecursiveSplitter，忽略标题结构。
    含标题（#/##/###...）的文档按标题层级切分，保留语义边界，检索更准。
    """
    if not text:
        return False
    return bool(re.search(r"^#{1,6}\s+\S", text, re.MULTILINE))


# base64 内嵌图片: ![alt](data:image/jpeg;base64,XXXX)
_INLINE_IMG_RE = re.compile(r"!\[[^\]]*\]\(data:image/[^;)]+;base64,[A-Za-z0-9+/=]+\)")


def _strip_inline_images(text: str) -> str:
    """移除 chunk 内容中的 base64 内嵌图片（保留 [图片] 占位）

    背景: 视觉大模型解析 PDF 时把图片以 data URI 内嵌进 Markdown，
    这些 base64 串会: ① 污染向量化 ② 扭曲 token 统计 ③ 混入 LLM 上下文。
    原始 Markdown 仍保留 base64 供 UI 预览，此函数仅作用于入库的 chunk 内容。
    """
    if not text:
        return text
    return _INLINE_IMG_RE.sub("![图片]", text)


def _select_splitter(
    text: str | None = None,
    doc_type: DocType | None = None,
    target_size: int = 512,
    min_size: int = 100,
    max_size: int = 1024,
):
    """根据内容形态 + 文档类型选择切分器

    ★ 内容优先: 文本若为 QA 问答形式（如 PDF 解析出的 FAQ），
      优先走 FAQSplitter 保证 Q&A 对不拆散（即使 doc_type 是 PDF/WORD）。
    """
    if _looks_like_faq(text):
        return FAQSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        )

    # 改进: .md 等含 Markdown 标题的文档 → 按标题层级切分（保留语义边界）
    if _has_markdown_headings(text):
        return MarkdownSplitter(
            target_size=target_size, min_size=min_size, max_size=max_size
        )

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
    overlap: int = 0,
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
    prev_content = ""  # 前一块「纯内容」（不含 overlap），用于取尾部重叠

    for i, content in enumerate(raw_chunks):
        if not content.strip():
            continue

        # 改进C: 剔除 base64 内嵌图片，避免污染向量化 / token统计 / LLM上下文
        content = _strip_inline_images(content)
        if not content.strip():
            continue

        # Overlap 接线: 把前一块纯内容尾部拼到当前块开头，保留边界上下文，
        # 避免语义被 chunk 边界切断（检索时边界处的关键信息不丢）。
        overlap_text = prev_content[-overlap:] if overlap > 0 and prev_content else ""
        final_content = (overlap_text + "\n" + content) if overlap_text else content

        chunks.append(
            Chunk(
                chunk_id=_make_chunk_id(source_file, i),
                content=final_content,
                char_count=count_chars(final_content),
                token_count=count_tokens(final_content),
                chunk_index=i,
                source_file=source_file,
                doc_type=doc_type,
                strategy=strategy,
                target_size=getattr(splitter, "target_size", 0),
                heading_path=_extract_headings(content),
                section_title=_extract_section_title(content),
                overlap_with_prev=bool(overlap_text),
                overlap_content=overlap_text,
            )
        )
        prev_content = content  # 存纯内容，避免重叠累积

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
