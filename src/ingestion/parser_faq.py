"""FAQ JSON解析器 — Q+A 绑定解析"""

import json
import time
from pathlib import Path

from .models import ParseResult, ParseStatus, RawDocument


def parse_faq_json(doc: RawDocument) -> ParseResult:
    """解析FAQ JSON → Markdown

    预期格式:
    [
        {"question": "...", "answer": "...", "keywords": ["..."]},
        ...
    ]
    """
    t0 = time.time()
    result = ParseResult(document=doc, status=ParseStatus.SUCCESS)

    try:
        with open(doc.file_path, "r", encoding="utf-8") as f:
            faq_data = json.load(f)

        if not isinstance(faq_data, list):
            result.status = ParseStatus.FAILED
            result.errors.append("FAQ JSON必须是数组格式 [{question, answer}, ...]")
            return result

        markdown_lines = [f"# {Path(doc.file_path).stem}", ""]

        for i, item in enumerate(faq_data, 1):
            q = item.get("question", "")
            a = item.get("answer", "")
            keywords = item.get("keywords", [])

            if q and a:
                markdown_lines.append(f"## Q{i}: {q}")
                markdown_lines.append("")
                markdown_lines.append(a)
                markdown_lines.append("")
                if keywords:
                    markdown_lines.append(f"*关键词: {', '.join(keywords)}*")
                markdown_lines.append("")

                result.elements.append(
                    {
                        "type": "faq",
                        "question": q,
                        "answer": a,
                        "keywords": keywords,
                    }
                )

        result.markdown = "\n".join(markdown_lines)
        result.parse_time_ms = (time.time() - t0) * 1000

    except json.JSONDecodeError as e:
        result.status = ParseStatus.FAILED
        result.errors.append(f"JSON格式错误: {e}")
    except Exception as e:
        result.status = ParseStatus.FAILED
        result.errors.append(f"FAQ解析失败: {e}")

    result.parse_time_ms = (time.time() - t0) * 1000
    return result
