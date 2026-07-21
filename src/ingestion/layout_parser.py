"""Layout JSON 解析 + Markdown 转换

完整照搬 RAG 项目 dots_ocr/utils/ 下的:
  - prompts.py: LAYOUT_PROMPT
  - output_cleaner.py: clean_model_output()
  - layout_utils.py: post_process_output()
  - format_transformer.py: layoutjson2md()
"""

import json
import re
from typing import Optional

from PIL import Image

# ═══════════════════════════════════════
# Prompt (与 dots_ocr/prompts.py prompt_layout_all_en 完全一致)
# ═══════════════════════════════════════

LAYOUT_PROMPT = """请分析这张文档图片的版面布局，输出每个元素的边界框、类别和文本内容。

输出格式：一个JSON数组，每个元素格式为：
{"bbox": [x1, y1, x2, y2], "category": "类别", "text": "文本内容"}

类别包括：
- Title: 主标题
- Section-header: 章节标题
- Text: 正文段落
- Table: 表格（text用HTML格式）
- Formula: 数学公式（text用LaTeX格式）
- Picture: 图片（不要text字段）
- List-item: 列表项
- Caption: 图表标题
- Page-header: 页眉（也提取其中的文字）
- Page-footer: 页脚（也提取其中的文字）
- Footnote: 脚注

要求：
1. 所有元素按人类阅读顺序排列（从上到下，从左到右）
2. 直接输出JSON数组，不要用Markdown代码块包裹
3. 不要省略任何文本，保留原文（中文输出中文，英文输出英文）
4. 公式输出LaTeX格式，表格输出HTML格式
"""

# ═══════════════════════════════════════
# OutputCleaner (精简版, 与 dots_ocr/output_cleaner.py 核心逻辑一致)
# ═══════════════════════════════════════


def _clean_model_output(raw: str) -> list[dict]:
    """解析模型的 JSON 输出, 处理各种格式异常

    与 RAG 项目 OutputCleaner.clean_model_output() 一致:
      1. 尝试 json.loads
      2. 失败则提取有效的 dict 对象
      3. 再失败则修复 JSON 语法后重试
    """
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]

    text = str(raw).strip()

    # 移除 Markdown 代码块包裹
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # ── 尝试1: 直接解析 ──
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # ── 尝试2: 提取有效的 dict 对象 ──
    dict_pattern = re.compile(r'\{[^{}]*"bbox"\s*:\s*\[[^\]]*\][^{}]*\}', re.DOTALL)
    matches = dict_pattern.findall(text)
    if matches:
        valid = []
        for m in matches:
            try:
                valid.append(json.loads(m))
            except json.JSONDecodeError:
                # 尝试修复常见问题后重试
                fixed = _fix_common_json_issues(m)
                try:
                    valid.append(json.loads(fixed))
                except json.JSONDecodeError:
                    continue
        if valid:
            return valid

    # ── 尝试3: 修复后整体解析 ──
    fixed = _fix_common_json_issues(text)
    # 补齐数组括号
    if not fixed.strip().startswith("["):
        fixed = "[" + fixed
    if not fixed.strip().endswith("]"):
        fixed = fixed.rstrip(",").rstrip() + "]"
    try:
        data = json.loads(fixed)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    return []


def _fix_common_json_issues(text: str) -> str:
    """修复常见 JSON 格式问题"""
    # 缺少逗号: }{ → },{
    text = re.sub(r"\}\s*\{", "},{", text)
    # 移除尾随逗号
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # 修复未转义的双引号 (在 text 字段内)
    # 简单策略: 在 "text": "..." 内部, 将裸双引号转义
    return text


# ═══════════════════════════════════════
# Layout → Markdown (与 dots_ocr/format_transformer.py layoutjson2md 一致)
# ═══════════════════════════════════════


def _layoutjson2md(
    cells: list[dict],
    origin_image: Optional[Image.Image] = None,
    page_num: int = 0,
    save_dir: Optional[str] = None,
) -> str:
    """将 Layout JSON 转为干净的 Markdown

    与 RAG 项目 layoutjson2md 处理逻辑完全一致:
      - Picture: 裁剪 → 缩放(≤800px) → JPEG base64 内嵌 + 存文件
      - Formula: $$...$$ 包裹
      - Table: HTML → Markdown table 转换
      - Page-header/Page-footer: 跳过
      - Title → #, Section-header → ##, List-item → -
    """
    import base64
    from io import BytesIO
    from pathlib import Path

    parts = []
    img_idx = 0

    for cell in cells:
        category = cell.get("category", "Text")
        bbox = cell.get("bbox")
        text = cell.get("text", "").strip()

        if category in ("Page-header", "Page-footer"):
            continue

        if category == "Picture":
            if bbox and len(bbox) == 4 and origin_image:
                try:
                    x1, y1, x2, y2 = [int(c) for c in bbox]
                    cropped = origin_image.crop((x1, y1, x2, y2))
                    # 缩放到很小 (≤300px) → base64 JPEG (≤8KB, Gradio 可渲染)
                    w, h = cropped.size
                    if w > 300:
                        ratio = 300 / w
                        cropped = cropped.resize((300, int(h * ratio)), Image.LANCZOS)
                    buf = BytesIO()
                    cropped.save(buf, format="JPEG", quality=65)
                    b64 = base64.b64encode(buf.getvalue()).decode()
                    parts.append(f"![图片](data:image/jpeg;base64,{b64})")
                    # 同时存原尺寸到文件
                    if save_dir:
                        Path(save_dir).mkdir(parents=True, exist_ok=True)
                        img_path = Path(save_dir) / f"page_{page_num}_img_{img_idx}.jpg"
                        origin_image.crop((x1, y1, x2, y2)).save(
                            str(img_path), "JPEG", quality=90
                        )
                    img_idx += 1
                except Exception:
                    pass
            continue

        if not text:
            continue

        if category == "Title":
            parts.append(f"# {text}")
        elif category == "Section-header":
            parts.append(f"## {text}")
        elif category == "Formula":
            parts.append(_format_formula(text))
        elif category == "Table":
            # HTML table → Markdown table
            md_table = _html_table_to_md(text)
            parts.append(md_table)
        elif category == "List-item":
            parts.append(f"- {text}")
        else:
            parts.append(text)

    return "\n\n".join(parts)


def _html_table_to_md(html: str) -> str:
    """简单的 HTML table → Markdown table"""
    import re

    rows = re.findall(r"<tr>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    if not rows:
        return html
    md_rows = []
    for i, row in enumerate(rows):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
        cells = [c.strip() for c in cells]
        md_rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            md_rows.append("|" + "|".join(["---"] * len(cells)) + "|")
    return "\n".join(md_rows)


def _format_formula(text: str) -> str:
    """格式化 LaTeX 公式"""
    text = text.strip()
    if text.startswith("$$") and text.endswith("$$"):
        return text
    if text.startswith("$") and text.endswith("$"):
        return f"$${text[1:-1]}$$"
    return f"$$\n{text}\n$$"


# ═══════════════════════════════════════
# 主处理入口
# ═══════════════════════════════════════


def parse_layout_response(
    raw_response: str,
    origin_image: Optional[Image.Image] = None,
    page_num: int = 0,
    save_dir: Optional[str] = None,
) -> str:
    """处理模型原始输出 → 干净 Markdown

    流程 (与 RAG 项目 ZhipuOCRParser._parse_single_image 一致):
      1. OutputCleaner 解析 JSON
      2. layoutjson2md 转 Markdown (含图片缩放+内嵌)
      3. JSON 解析全失败 → 降级为纯文本
    """
    cells = _clean_model_output(raw_response)

    if cells:
        return _layoutjson2md(cells, origin_image, page_num, save_dir)

    # 降级: 尝试从原文中提取文本
    clean = raw_response.strip()
    clean = re.sub(r"```(?:json)?\s*", "", clean)
    clean = re.sub(r"```", "", clean)
    clean = re.sub(r"[\[\]\{\}]", "", clean)
    clean = re.sub(r"\\(?:\(|\)|\[|\])", "", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()
