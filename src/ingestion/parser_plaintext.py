"""纯文本/Markdown 解析器 — 直接读取文件内容

适用: .txt / .md 文件，以及兜底所有无法识别格式的文本文件
"""

import time
from pathlib import Path

from .models import ParseResult, ParseStatus, RawDocument


def parse_plaintext(doc: RawDocument) -> ParseResult:
    """读取纯文本/Markdown 文件 → ParseResult"""
    t0 = time.time()
    result = ParseResult(document=doc, status=ParseStatus.SUCCESS)

    path = Path(doc.file_path)
    if not path.exists():
        result.status = ParseStatus.FAILED
        result.errors.append(f"文件不存在: {doc.file_path}")
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    try:
        # 自动检测编码
        content = _read_with_encoding(path)
    except Exception as e:
        result.status = ParseStatus.FAILED
        result.errors.append(f"读取文件失败: {e}")
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    if not content.strip():
        result.status = ParseStatus.PARTIAL
        result.warnings.append("文件内容为空")
        result.parse_time_ms = (time.time() - t0) * 1000
        return result

    # 如果是 .md 文件，保持原样；如果是 .txt，加标题
    if path.suffix.lower() == ".md":
        result.markdown = content
    else:
        result.markdown = f"# {path.stem}\n\n{content}"

    result.parse_time_ms = (time.time() - t0) * 1000
    return result


def _read_with_encoding(path: Path) -> str:
    """尝试多种编码读取文件"""
    for enc in ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 最后兜底
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
