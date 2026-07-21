"""统一Markdown清洗流水线

所有解析器输出统一为 Markdown → 此模块统一清洗:
  1. 去除页眉/页脚/水印
  2. 去除版权声明/广告/推荐链接
  3. 规范空白行
  4. 段落级去重
  5. 最小长度过滤
"""

import hashlib
import re
from typing import Optional

from .models import CleanedDocument, DocType


def clean_markdown(
    markdown_text: str,
    source_file: str,
    doc_type: DocType,
    metadata: Optional[dict] = None,
) -> list[CleanedDocument]:
    """Markdown统一清洗流水线

    Args:
        markdown_text: 原始Markdown文本
        source_file: 来源文件路径
        doc_type: 文档类型
        metadata: 额外元数据

    Returns:
        清洗后的 CleanedDocument 列表（一个文件可能产出多个块）
    """

    if not markdown_text or not markdown_text.strip():
        return []

    cleaned_list = []
    metadata = metadata or {}

    # 步骤1: 按段落拆分（以空行为界）
    paragraphs = _split_paragraphs(markdown_text)

    # 步骤2: 逐段清洗
    for i, para in enumerate(paragraphs):
        if not para.strip():
            continue

        # 2a. 取出去除噪音
        cleaned, removed = _clean_paragraph(para)

        # 2b. 跳过短段落
        if len(cleaned) < 10:
            continue

        # 2c. 跳过纯噪音段落
        if _is_noise_only(cleaned):
            continue

        cleaned_list.append(
            CleanedDocument(
                chunk_id=_make_chunk_id(source_file, i),
                content=cleaned,
                char_count=len(cleaned),
                source_file=source_file,
                doc_type=doc_type,
                removed_noise=removed,
                metadata={**metadata, "paragraph_index": i},
            )
        )

    # 步骤3: 段落级去重
    cleaned_list = _dedup_paragraphs(cleaned_list)

    return cleaned_list


# ═══════════════════════════════════════
# 段落拆分
# ═══════════════════════════════════════


def _split_paragraphs(text: str) -> list[str]:
    """按空行/标题/表格边界拆分Markdown"""
    # 先按空行拆分
    raw = text.split("\n\n")
    paragraphs = []
    for block in raw:
        stripped = block.strip()
        if stripped:
            # 如果块内包含多行表格，保持完整
            if stripped.startswith("|") and stripped.endswith("|"):
                paragraphs.append(stripped)
            else:
                # 按行进一步拆分（但保留多行段落）
                lines = stripped.split("\n")
                current = []
                for line in lines:
                    line = line.strip()
                    # 标题行 → 保存之前的段落，开始新的
                    # ★ 只有整行为加粗短文本（≤60字，形如 **小标题**）才视为伪标题
                    is_bold_pseudo_heading = (
                        line.startswith("**")
                        and line.endswith("**")
                        and len(line) <= 60
                        and line.count("**") == 2
                    )
                    if line.startswith("#") or is_bold_pseudo_heading:
                        if current:
                            paragraphs.append(" ".join(current))
                            current = []
                        paragraphs.append(line)
                    elif line.startswith("|"):
                        # 表格行
                        if current:
                            paragraphs.append(" ".join(current))
                            current = []
                        paragraphs.append(line)
                    elif line:
                        current.append(line)
                if current:
                    paragraphs.append(" ".join(current))

    return [p for p in paragraphs if p.strip()]


# ═══════════════════════════════════════
# 段落清洗
# ═══════════════════════════════════════

# 噪音模式（正则, 噪音类型）
_NOISE_PATTERNS: list[tuple[str, str]] = [
    # 页眉页脚
    (r"^\d+$", "page_number"),  # 纯数字行（可能是页码）
    (r"^第\d+页\s*/\s*共\d+页$", "page_header"),
    (r"^\d+\s*/\s*\d+$", "page_header"),
    (r"^\s*\d+\s*$", "page_number"),  # 孤立的页码
    # 版权声明
    (r"版权所有\s*©?\s*.*?\d{4}.*?保留.*?权利", "copyright"),
    (r"Copyright\s*©\s*\d{4}.*?All Rights Reserved", "copyright"),
    (r"未经许可.*?不得.*?(转载|复制|使用)", "copyright"),
    # URL
    (r"https?://\S+", "url"),
    (r"www\.\S+\.\S+", "url"),
    # 广告/推广
    (r"(扫码|扫一扫|长按识别).*?(关注|加入|下载)", "promotion"),
    (r"(广告|推广|推荐阅读|热门文章|相关推荐)", "promotion"),
    (r"点击(上方|下方|这里)?.*?(查看|了解|购买|下载)", "promotion"),
    # 水印
    (r"(仅供.*?使用|内部资料|机密|CONFIDENTIAL|DRAFT|草稿)", "watermark"),
    # 连续特殊字符
    (r"[-=_*]{4,}", "separator"),
]


def _clean_paragraph(text: str) -> tuple[str, list[str]]:
    """清洗单个段落，返回 (清洗后文本, [被移除的噪音类型])"""
    removed = []

    for pattern, noise_type in _NOISE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            removed.append(noise_type)

    # 清理空白
    text = re.sub(r"\n{3,}", "\n\n", text)  # 多个换行 → 2个
    text = re.sub(r"[ \t]{2,}", " ", text)  # 多个空格 → 1个
    text = re.sub(r"^\s+", "", text)  # 行首空白
    text = re.sub(r"\s+$", "", text)  # 行尾空白

    return text.strip(), removed


def _is_noise_only(text: str) -> bool:
    """判断是否纯噪音段落"""
    # 去除空白后为空
    if not text.strip():
        return True
    # 只有标点符号和空白
    punctuation_only = re.compile(
        r"^[\s"
        r"　-〿"  # CJK标点：，。！？、；：（）【】《》
        r"＀-￯"  # 全角标点
        r" -⁯"  # 通用标点
        r"\x00-\x2f"  # ASCII标点
        r"\x3a-\x40"
        r"\x5b-\x60"
        r"\x7b-\x7e"
        r"\-|/\\]+$"
    )
    if punctuation_only.match(text):
        return True
    # 太短（有效字符 < 3）
    alphanum = re.sub(r"[\s\W]", "", text)
    if len(alphanum) < 3:
        return True
    return False


# ═══════════════════════════════════════
# 去重
# ═══════════════════════════════════════


def _dedup_paragraphs(docs: list[CleanedDocument]) -> list[CleanedDocument]:
    """段落级去重 — 用前200字符做指纹"""
    seen: set[str] = set()
    result = []

    for doc in docs:
        # 提取纯文本指纹（去Markdown标记）
        plain = re.sub(r"[#*`\[\]()|_\-]", "", doc.content[:200])
        fingerprint = hashlib.md5(plain.encode()).hexdigest()

        if fingerprint not in seen:
            seen.add(fingerprint)
            result.append(doc)
        else:
            doc.is_duplicate = True

    return result


def _make_chunk_id(source_file: str, index: int) -> str:
    raw = f"{source_file}#p{index}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]
