"""模块2: 智能分块策略

根据文档类型自动选择最优切分策略:
  FAQ          → FAQSplitter      (Q&A对保整，不拆散)
  PDF / Word   → MarkdownSplitter (标题层级感知)
  PPT / 网页   → SemanticSplitter (句子边界切分)
  Excel / 图片 → RecursiveSplitter (通用递归切分)

使用:
    from src.chunking import chunk_document
    from src.ingestion.models import DocType

    result = chunk_document(markdown_text, "policy.pdf", DocType.PDF)
    for chunk in result.chunks:
        print(f"[{chunk.chunk_index}/{chunk.total_chunks}] {chunk.content[:60]}...")
"""

from .models import Chunk, ChunkResult, ChunkStrategy
from .router import chunk_document
from .token_counter import count_tokens
