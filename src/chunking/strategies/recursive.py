"""递归字符切分 — LangChain 风格的多分隔符递归切分

按优先级尝试分隔符:
  1. 空行 \n\n      → 段落边界（最强）
  2. 换行 \n         → 行边界
  3. 中文句号 。     → 句子边界
  4. 中文分号 ；     → 子句边界
  5. 英文句号 .      → 句子边界
  6. 逗号 ，         → 短语边界
  7. 空格 (字符级)   → 最后手段

每次尝试一个分隔符，如果切后仍有超大块 → 下一级分隔符递归。
"""

import re

from ..models import ChunkStrategy


class RecursiveSplitter:
    """递归字符切分器 — 通用兜底策略"""

    strategy = ChunkStrategy.RECURSIVE

    SEPARATORS = [
        "\n\n",
        "\n",
        "。",
        "；",
        "！",
        "？",
        r"\. ",
        "; ",
        "! ",
        r"\? ",
        "，",
        ", ",
        " ",
    ]

    def __init__(
        self,
        target_size: int = 512,
        min_size: int = 80,
        max_size: int = 1024,
    ):
        self.target_size = target_size
        self.min_size = min_size
        self.max_size = max_size

    def split(self, text: str) -> list[str]:
        if not text.strip():
            return []

        from ..token_counter import count_tokens

        total_tokens = count_tokens(text)
        if total_tokens <= self.max_size:
            return [text.strip()]

        return self._recursive_split(text, separator_index=0)

    def _recursive_split(self, text: str, separator_index: int) -> list[str]:
        """递归切分核心"""
        from ..token_counter import count_tokens

        if separator_index >= len(self.SEPARATORS):
            # 无可用的分隔符 → 硬切
            return self._character_split(text)

        sep = self.SEPARATORS[separator_index]
        chunks: list[str] = []

        for part in self._split_with_separator(text, sep):
            if not part.strip():
                continue

            tokens = count_tokens(part)
            if tokens <= self.max_size:
                chunks.append(part.strip())
            else:
                # 块太大 → 下一级分隔符
                sub = self._recursive_split(part, separator_index + 1)
                chunks.extend(sub)

        # 合并过小的相邻块
        merged = self._merge_small_chunks(chunks)
        return merged

    def _split_with_separator(self, text: str, sep: str) -> list[str]:
        """用分隔符切分，保留分隔符在切分点之后（而不是丢弃）"""
        if sep in ("\n\n", "\n", " "):
            return text.split(sep)

        # 对于标点分隔符，保留标点在末尾
        pattern = f"(?<={re.escape(sep)})"
        parts = re.split(pattern, text)
        return [p for p in parts if p.strip()]

    def _character_split(self, text: str) -> list[str]:
        """硬切兜底：按字符数均分"""
        from ..token_counter import count_chars

        chars = count_chars(text)
        target_chars = int(self.target_size * 1.5)

        if chars <= target_chars:
            return [text.strip()]

        chunks: list[str] = []
        start = 0
        while start < chars:
            end = min(start + target_chars, chars)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end
        return chunks

    def _merge_small_chunks(self, chunks: list[str]) -> list[str]:
        """合并过小的相邻块到前一个chunk"""
        from ..token_counter import count_tokens

        if len(chunks) <= 1:
            return chunks

        merged: list[str] = []
        buffer = ""
        buffer_tokens = 0

        for c in chunks:
            c_tokens = count_tokens(c)
            if c_tokens < self.min_size and buffer:
                # 小片段 → 合并到 buffer
                combined = f"{buffer}\n\n{c}"
                combined_tokens = count_tokens(combined)
                if combined_tokens <= self.max_size:
                    buffer = combined
                    buffer_tokens = combined_tokens
                    continue
                # 合并会超出限制 → 单独保留
                merged.append(buffer.strip())
                buffer = c
                buffer_tokens = c_tokens
            elif c_tokens < self.min_size:
                # 第一个就是小片段 → 暂存
                buffer = c
                buffer_tokens = c_tokens
            elif buffer_tokens + c_tokens <= self.max_size:
                buffer = f"{buffer}\n\n{c}" if buffer else c
                buffer_tokens += c_tokens
            else:
                if buffer:
                    merged.append(buffer.strip())
                buffer = c
                buffer_tokens = c_tokens

        if buffer:
            merged.append(buffer.strip())

        return merged if merged else chunks
