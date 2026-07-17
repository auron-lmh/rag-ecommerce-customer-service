"""模块1: 多格式数据摄入

架构: 双引擎 + 统一清洗层

PDF/扫描件 → 阿里百炼 qwen-vl-ocr (API)    ──→ Markdown ─┐
Office文档  → python-docx/openpyxl (本地)    ──→ Markdown ─┤
图片        → 智谱GLM-4V/阿里Qwen-VL (API)   ──→ 描述     ─┼── 统一清洗层 → CleanedDocument
网页        → requests+BS4 (本地)            ──→ 文本     ─┤
FAQ JSON    → json (本地)                     ──→ Markdown ─┘

使用:
    from src.ingestion.router import parse_file
    from src.ingestion.clean_markdown import clean_markdown

    result = parse_file("document.pdf")
    if result.status == ParseStatus.SUCCESS:
        chunks = clean_markdown(result.markdown, "document.pdf", result.document.doc_type)
"""

from .clean_markdown import clean_markdown
from .loader import (
    create_sample_faq,
    create_sample_product_csv,
    load_directory,
    load_faq_json,
)
from .models import CleanedDocument, DocType, ParseResult, ParseStatus, RawDocument
from .router import parse_file
