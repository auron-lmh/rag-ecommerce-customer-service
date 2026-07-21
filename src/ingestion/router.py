"""模块1 路由器 — 按文件类型自动选择解析器

双引擎架构:
  PDF/扫描件 → 阿里百炼文档解析API (qwen-vl-ocr)
  Office文档  → python-docx / openpyxl (本地, 秒级)
  图片        → 智谱GLM-4V / 阿里Qwen-VL (API)
  网页        → requests + BeautifulSoup (本地)
  FAQ JSON    → json (本地)
"""

from pathlib import Path
from typing import Optional

from .models import DocType, ParseResult, ParseStatus, RawDocument

# 已知的解析器映射
_PARSER_IMPORTED: dict[DocType, object] = {}


def parse_file(file_path: str, doc_type: Optional[DocType] = None) -> ParseResult:
    """统一入口 — 检测文件类型，自动路由到对应解析器

    Args:
        file_path: 文件路径或URL
        doc_type: 手动指定类型，不指定则自动推断

    Returns:
        ParseResult
    """
    if doc_type is None:
        doc_type = _detect_type(file_path)

    is_url = file_path.startswith(("http://", "https://"))
    if is_url:
        # URL 不能用 Path.resolve() —— Windows 上会变成 C:\https:\... 垃圾路径
        from urllib.parse import urlparse

        parsed = urlparse(file_path)
        title = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
        doc = RawDocument(
            file_path=file_path,
            doc_type=DocType.WEB if doc_type == DocType.PLAIN_TEXT else doc_type,
            file_size_bytes=0,
            title=title,
        )
    else:
        path = Path(file_path)
        doc = RawDocument(
            file_path=str(path.resolve()),
            doc_type=doc_type,
            file_size_bytes=path.stat().st_size if path.exists() else 0,
            title=path.stem,
        )

    try:
        if doc_type == DocType.PDF:
            return _route_pdf(doc)
        elif doc_type in (DocType.WORD, DocType.EXCEL, DocType.PPT):
            return _route_office(doc)
        elif doc_type == DocType.IMAGE:
            return _route_image(doc)
        elif doc_type == DocType.WEB:
            return _route_web(doc)
        elif doc_type == DocType.FAQ_JSON:
            return _route_faq_json(doc)
        else:
            return ParseResult(
                document=doc,
                status=ParseStatus.SKIPPED,
                errors=[f"不支持的文档格式: {doc_type}"],
            )
    except ImportError as e:
        return ParseResult(
            document=doc,
            status=ParseStatus.FAILED,
            errors=[f"解析器依赖缺失: {e}"],
        )
    except Exception as e:
        return ParseResult(
            document=doc,
            status=ParseStatus.FAILED,
            errors=[f"解析失败: {e}"],
        )


def _detect_type(file_path: str) -> DocType:
    """从文件扩展名推断类型"""
    ext = Path(file_path).suffix.lower()
    mapping = {
        ".pdf": DocType.PDF,
        ".docx": DocType.WORD,
        ".doc": DocType.WORD,
        ".xlsx": DocType.EXCEL,
        ".xls": DocType.EXCEL,
        ".pptx": DocType.PPT,
        ".ppt": DocType.PPT,
        ".png": DocType.IMAGE,
        ".jpg": DocType.IMAGE,
        ".jpeg": DocType.IMAGE,
        ".gif": DocType.IMAGE,
        ".webp": DocType.IMAGE,
        ".bmp": DocType.IMAGE,
        ".json": DocType.FAQ_JSON,
        ".txt": DocType.PLAIN_TEXT,
        ".md": DocType.PLAIN_TEXT,
        ".html": DocType.WEB,
        ".htm": DocType.WEB,
    }
    if ext in mapping:
        return mapping[ext]
    if file_path.startswith("http"):
        return DocType.WEB
    return DocType.PLAIN_TEXT


# ═══════════════════════════════════════════════
# 路由分发
# ═══════════════════════════════════════════════


def _route_pdf(doc: RawDocument) -> ParseResult:
    from .parser_pdf import parse_pdf_bailian

    return parse_pdf_bailian(doc)


def _route_office(doc: RawDocument) -> ParseResult:
    from .parser_office import parse_office

    return parse_office(doc)


def _route_image(doc: RawDocument) -> ParseResult:
    from .parser_image import parse_image

    return parse_image(doc)


def _route_web(doc: RawDocument) -> ParseResult:
    from .parser_web import parse_webpage

    return parse_webpage(doc)


def _route_faq_json(doc: RawDocument) -> ParseResult:
    from .parser_faq import parse_faq_json

    return parse_faq_json(doc)
