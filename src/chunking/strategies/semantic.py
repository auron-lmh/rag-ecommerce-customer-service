"""语义边界切分 — 优先在句子边界断，保证语义完整性

与 RecursiveSplitter 的区别:
  - Recursive: 多分隔符递归 → 最终可能在任何位置断
  - Semantic: 只在句号/问号/感叹号后断 → 保证每个chunk都是完整句子
  - 如果在 max_size 内找不到句子边界 → 降级到递归切分

适用: 政策文档、帮助文档、产品描述等需要语义连续性的场景
"""

import re

from ..models import ChunkStrategy


class SemanticSplitter:
    """句子边界感知切分器"""

    strategy = ChunkStrategy.SEMANTIC

    # 句子结束标记（带上下文的正则）
    # 修复: \s+ 要求句末标点后必须有空白，中文「。下一句」无空格导致匹配不到，
    #       语义分块在中文场景名存实亡。改 \s* 允许零空白。
    SENTENCE_END = re.compile(r"(?<=[。！？\.!\?])\s*(?=[A-Z一-鿿぀-ゟ゠-ヿ])")

    # 子句结束标记（较短停顿）
    CLAUSE_END = re.compile(r"(?<=[；，;,])\s*(?=[一-鿿A-Z])")

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

        if count_tokens(text) <= self.max_size:
            return [text.strip()]

        # 句子级切分
        sentences = self._split_sentences(text)
        return self._assemble_chunks(sentences)

    def _split_sentences(self, text: str) -> list[str]:
        """将文本拆分为句子列表"""
        # 先在句子结束标记处切
        parts = self.SENTENCE_END.split(text)
        sentences = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 再尝试在子句标记处切（仅对过长的部分）
            from ..token_counter import count_tokens

            if count_tokens(part) > self.max_size:
                sub_parts = self.CLAUSE_END.split(part)
                sentences.extend(p.strip() for p in sub_parts if p.strip())
            else:
                sentences.append(part)

        return sentences

    def _assemble_chunks(self, sentences: list[str]) -> list[str]:
        """将句子组装成不超过 max_size 的chunk"""
        from ..token_counter import count_tokens

        chunks: list[str] = []
        buffer = ""
        buffer_tokens = 0

        for sentence in sentences:
            s_tokens = count_tokens(sentence)

            # ── 单句超过上限 ──
            if s_tokens > self.max_size:
                # 先保存 buffer
                if buffer:
                    chunks.append(buffer.strip())
                    buffer = ""
                    buffer_tokens = 0
                # 长句递归切分兜底
                from .recursive import RecursiveSplitter

                fallback = RecursiveSplitter(
                    target_size=self.target_size,
                    min_size=self.min_size,
                    max_size=self.max_size,
                )
                chunks.extend(fallback.split(sentence))
                continue

            # ── 加入 buffer ──
            if buffer_tokens + s_tokens <= self.target_size:
                buffer = f"{buffer}\n{sentence}" if buffer else sentence
                buffer_tokens += s_tokens
            elif buffer_tokens + s_tokens <= self.max_size:
                # 在 target 与 max 之间：接受但要检查是否值得
                # 如果再加一句就超 max，则保存 buffer 并重置
                buffer = f"{buffer}\n{sentence}" if buffer else sentence
                buffer_tokens += s_tokens
            else:
                chunks.append(buffer.strip())
                buffer = sentence
                buffer_tokens = s_tokens

        if buffer:
            chunks.append(buffer.strip())

        return chunks if chunks else [" ".join(sentences).strip()] if sentences else []
