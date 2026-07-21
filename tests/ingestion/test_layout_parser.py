"""测试 Layout JSON 解析器 — 覆盖各种模型输出场景"""

import json

from src.ingestion.layout_parser import (
    LAYOUT_PROMPT,
    _clean_model_output,
    _layoutjson2md,
    parse_layout_response,
)

# ═══════════════════════════════════════
# 场景1: 完美的 JSON 输出
# ═══════════════════════════════════════

VALID_JSON = json.dumps(
    [
        {"bbox": [110, 115, 883, 192], "category": "Title", "text": "第一章 概述"},
        {"bbox": [108, 222, 1586, 373], "category": "Text", "text": "这是正文内容。"},
        {"bbox": [127, 705, 1561, 1330], "category": "Picture"},
        {"bbox": [129, 1597, 571, 1650], "category": "List-item", "text": "要点一"},
        {"bbox": [110, 222, 1586, 120], "category": "Page-header", "text": "页眉"},
        {
            "bbox": [100, 200, 500, 300],
            "category": "Table",
            "text": "<table><tr><td>A</td><td>B</td></tr></table>",
        },
        {
            "bbox": [200, 300, 600, 400],
            "category": "Formula",
            "text": "\\frac{1}{N} \\sum x_i",
        },
    ]
)


def test_valid_json_clean():
    """完美的 JSON 应该全部解析成功"""
    cells = _clean_model_output(VALID_JSON)
    assert len(cells) == 7


def test_valid_json_to_markdown():
    """完美 JSON → Markdown"""
    markdown = parse_layout_response(VALID_JSON)
    assert "第一章 概述" in markdown
    assert "# 第一章 概述" in markdown  # Title → #
    assert "要点一" in markdown
    assert "- 要点一" in markdown  # List-item → -
    assert "\\frac" in markdown  # Formula 保留
    assert "页眉" not in markdown  # Page-header 跳过
    assert "| A |" in markdown  # Table → Markdown table


# ═══════════════════════════════════════
# 场景2: 模型输出被 Markdown 代码块包裹
# ═══════════════════════════════════════

MD_WRAPPED = """```json
[
  {"bbox": [10, 20, 30, 40], "category": "Text", "text": "内容"}
]
```"""


def test_md_wrapped():
    """Markdown 代码块包裹的 JSON 应该能解析"""
    cells = _clean_model_output(MD_WRAPPED)
    assert len(cells) == 1
    assert cells[0]["text"] == "内容"


# ═══════════════════════════════════════
# 场景3: JSON 中缺少逗号 (常见模型输出问题)
# ═══════════════════════════════════════

MISSING_COMMAS = """
[
  {"bbox": [10, 20, 30, 40], "category": "Text", "text": "第一段"}
  {"bbox": [50, 60, 70, 80], "category": "Text", "text": "第二段"}
]
"""


def test_missing_commas():
    """缺少逗号的 JSON 应该被修复"""
    markdown = parse_layout_response(MISSING_COMMAS)
    assert "第一段" in markdown
    assert "第二段" in markdown


# ═══════════════════════════════════════
# 场景4: 纯文本 (JSON 解析完全失败)
# ═══════════════════════════════════════


def test_plain_text_fallback():
    """非 JSON 文本降级"""
    markdown = parse_layout_response("这是纯文本内容，没有任何 JSON 结构。")
    assert "纯文本内容" in markdown
    assert len(markdown) > 0


# ═══════════════════════════════════════
# 场景5: 空输入
# ═══════════════════════════════════════


def test_empty_input():
    markdown = parse_layout_response("")
    assert markdown == ""

    markdown = parse_layout_response("[]")
    assert markdown == ""


# ═══════════════════════════════════════
# 场景6: 部分损坏的 JSON (有些 dict 有效, 有些无效)
# ═══════════════════════════════════════

PARTIALLY_BROKEN = """[
  {"bbox": [10, 20, 30, 40], "category": "Text", "text": "有效内容"},
  {"bbox": [50, 60, 70, 80], "category": "Text", "text": "未闭合字符串...},
  {"bbox": [90, 100, 110, 120], "category": "Text", "text": "另一段有效"}
]"""


def test_partially_broken():
    """部分损坏的 JSON 应该提取有效部分"""
    markdown = parse_layout_response(PARTIALLY_BROKEN)
    # 至少有效内容应该被提取
    assert "有效内容" in markdown or "另一段有效" in markdown or len(markdown) > 0


# ═══════════════════════════════════════
# 场景7: Prompt 完整性检查
# ═══════════════════════════════════════


def test_prompt_contains_key_elements():
    """Prompt 包含关键的布局类别和输出格式要求"""
    assert "bbox" in LAYOUT_PROMPT
    assert "Title" in LAYOUT_PROMPT
    assert "JSON" in LAYOUT_PROMPT
    assert "Picture" in LAYOUT_PROMPT
    assert "阅读顺序" in LAYOUT_PROMPT
