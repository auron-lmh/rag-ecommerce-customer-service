"""Markdown 标题层级切分 — 按 # → ## → ### 逐级递归切分

策略:
  1. 先按一级标题 # 切分
  2. 段大小超过 target_size → 按二级标题 ## 递归
  3. 仍超过 → 按三级标题 ### 递归
  4. 仍超过 → 段落级别切分（空行为界）
  5. 最后兜底 → 固定窗口硬切
"""

import re
from typing import Optional

from ..models import ChunkStrategy


class MarkdownSplitter:
    """Markdown标题感知切分器

    与 BaseSplitter 不同，这个类以内容语义为优先：
    - 尽量不在标题中间切开
    - 尽量不在代码块/表格中间切开
    - 子标题跟随父标题保留 heading_path
    """

    strategy = ChunkStrategy.MARKDOWN

    def __init__(
        self,
        target_size: int = 512,
        min_size: int = 100,
        max_size: int = 1024,
    ):
        self.target_size = target_size
        self.min_size = min_size
        self.max_size = max_size

    def split(self, text: str) -> list[str]:
        """按Markdown标题层级切分"""
        if not text.strip():
            return []

        return self._split_by_headings(text, level=1)

    def _split_by_headings(self, text: str, level: int) -> list[str]:
        """递归按标题切分

        级别对应: level=1 → #, level=2 → ##, level=3 → ###
        """
        prefix = "#" * level + " "
        sections = re.split(rf"\n(?={prefix})", text, flags=re.MULTILINE)

        if len(sections) == 1:
            # 当前级别没有切出来 → 尝试下一个级别
            if level < 3:
                return self._split_by_headings(text, level + 1)
            # 没有标题 → 段落级切分
            return self._split_by_paragraphs(text)

        chunks: list[str] = []
        for section in sections:
            if not section.strip():
                continue

            from ..token_counter import count_tokens

            tokens = count_tokens(section)
            if tokens <= self.max_size:
                chunks.append(section.strip())
            else:
                # 段太大 → 递归到下一级标题
                if level < 3:
                    subs = self._split_by_headings(section, level + 1)
                else:
                    subs = self._split_by_paragraphs(section)
                for sub in subs:
                    if sub.strip():
                        chunks.append(sub.strip())

        return chunks

    def _split_by_paragraphs(self, text: str) -> list[str]:
        """段落级切分：以空行为界，保护代码块和表格"""
        from ..token_counter import count_tokens

        # 保护代码块和表格不被拆分
        protected_blocks = self._extract_protected_blocks(text)
        placeholder = "__PROTECTED_BLOCK_{}__"

        working_text = text
        saved_blocks: dict[str, str] = {}
        for i, block in enumerate(protected_blocks):
            key = placeholder.format(i)
            saved_blocks[key] = block
            working_text = working_text.replace(block, f"\n{key}\n")

        # 空行切分
        paragraphs = working_text.split("\n\n")
        chunks: list[str] = []
        buffer = ""
        buffer_tokens = 0

        for para in paragraphs:
            # 恢复受保护块
            for key, block in saved_blocks.items():
                para = para.replace(key, block)

            if not para.strip():
                continue

            para_tokens = count_tokens(para)

            # 单个段落超过上限 → 硬切
            if para_tokens > self.max_size:
                if buffer:
                    chunks.append(buffer.strip())
                    buffer = ""
                    buffer_tokens = 0
                hard_chunks = self._hard_split(para)
                chunks.extend(hard_chunks)
                continue

            # 合并到buffer
            if buffer_tokens + para_tokens <= self.max_size:
                buffer = f"{buffer}\n\n{para}" if buffer else para
                buffer_tokens += para_tokens
            else:
                if buffer:
                    chunks.append(buffer.strip())
                buffer = para
                buffer_tokens = para_tokens

        if buffer:
            chunks.append(buffer.strip())

        return chunks if chunks else [text.strip()]

    def _hard_split(self, text: str) -> list[str]:
        """兜底硬切：按目标大小的80%切，在句号/换行处断"""
        from ..token_counter import count_chars, count_tokens

        target_chars = int(self.target_size * 1.2)  # token → char 近似

        if count_chars(text) <= target_chars:
            return [text.strip()]

        chunks: list[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + target_chars, text_len)

            # 寻找最佳切分点（句号、分号、换行）
            if end < text_len:
                # 搜索范围内最近的句子边界
                search_start = max(start + target_chars // 2, start)
                best = end
                for pattern in [
                    r"\n\n",
                    r"\n",
                    r"。",
                    r"；",
                    r"！",
                    r"？",
                    r"\. ",
                    r"; ",
                ]:
                    match = None
                    # 在搜索范围内找最后一个匹配
                    for m in re.finditer(pattern, text[search_start:end]):
                        match = m
                    if match:
                        best = search_start + match.end()
                        break
                end = best

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(chunk_text)
            start = end

        return chunks

    def _extract_protected_blocks(self, text: str) -> list[str]:
        """提取受保护的块：代码块 ```...``` 和表格 |...|"""
        blocks = []
        # 代码块
        blocks.extend(m.group(0) for m in re.finditer(r"```[\s\S]*?```", text))
        # 表格（至少2行，以|开头）
        blocks.extend(
            m.group(0) for m in re.finditer(r"(?:^\|.+\|$\n?)+", text, re.MULTILINE)
        )
        return blocks
