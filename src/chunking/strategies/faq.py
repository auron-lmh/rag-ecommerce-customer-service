"""FAQ 绑定切分 — Q&A 对保持完整，不拆散

策略规则:
  1. 有明确 Q/A 边界 → 一个 Q+A 对 = 一个 chunk
  2. Q 较短但 A 特别长 → 在 A 内部按段落切分，每段保留 Q 作为上下文
  3. 无明确边界 → 降级到段落切分
"""

import re

from ..models import ChunkStrategy


class FAQSplitter:
    """FAQ Q&A 对绑定切分器

    核心原则: Q 和 A 必须同在一个 chunk，不能让检索到 A 却不知道 Q 问的是什么。
    """

    strategy = ChunkStrategy.FAQ

    def __init__(
        self,
        target_size: int = 512,
        min_size: int = 60,
        max_size: int = 1024,
    ):
        self.target_size = target_size
        self.min_size = min_size
        self.max_size = max_size

    # ── 预定义的分隔模式 ──
    QA_PATTERNS = [
        # Markdown格式 FAQ（支持行首和文中）
        r"(?:^|\n)(?=##\s*Q\d+[：:])",  # ## Q1: xxx
        r"(?:^|\n)(?=###\s*Q)",  # ### Q: xxx
        r"(?:^|\n)(?=\*\*Q\d*[：:])",  # **Q1:** xxx
        r"(?:^|\n)(?=Q\d+[.\、\s：:])",  # Q1. xxx / Q1: xxx
        # 纯文本 FAQ
        r"(?:^|\n)(?=问[：:])",  # 问：xxx
    ]

    def split(self, text: str) -> list[str]:
        if not text.strip():
            return []

        # 尝试识别 Q&A 对边界
        qa_chunks = self._split_by_qa_boundary(text)
        if qa_chunks:
            return qa_chunks

        # 无 Q&A 边界 → 段落切分兜底
        return self._paragraph_fallback(text)

    def _split_by_qa_boundary(self, text: str) -> list[str]:
        """按 Q&A 边界切分"""
        # 尝试每种模式
        for pattern in self.QA_PATTERNS:
            parts = re.split(pattern, text, flags=re.MULTILINE)
            if len(parts) > 1:
                chunks = self._process_qa_parts(parts)
                if chunks:
                    return chunks
        return []

    def _process_qa_parts(self, parts: list[str]) -> list[str]:
        """处理切分后的 Q&A 片段"""
        from ..token_counter import count_tokens

        chunks: list[str] = []

        for part in parts:
            part = part.strip()
            if not part:
                continue

            tokens = count_tokens(part)

            if tokens <= self.max_size:
                chunks.append(part)
            elif tokens <= self.target_size * 2:
                # 略超上限但能接受（不拆单个Q&A对）
                chunks.append(part)
            else:
                # A 特别长 → 在段落级切分，每个子块带 Q 前缀
                q_text = self._extract_question(part)
                sub_chunks = self._split_long_answer(part, q_text)
                chunks.extend(sub_chunks)

        return chunks

    def _extract_question(self, text: str) -> str:
        """从 Q&A 对中提取 Q 部分

        修复: 跳过 "## 第N页" 伪标题（PDF 分页标记），避免把页码误当问题。
        """
        for line in text.split("\n"):
            stripped = line.strip()
            # 跳过页码伪标题
            if re.match(r"^#{1,6}\s*第\s*\d+\s*页\s*$", stripped):
                continue
            # 匹配 Markdown 标题形式的 Q
            m = re.match(r"^#{2,6}\s*Q?\d*[：:\s]*(.+?)$", stripped)
            if m:
                return m.group(1)
            # 匹配 Q1: / 问： 形式
            m = re.match(r"^(?:Q\d*|[问问])[\.\、\s：:]+\s*(.+?)$", stripped)
            if m:
                return m.group(1)

        # 取首行（跳过页码伪标题）
        for line in text.split("\n"):
            stripped = line.strip()
            if re.match(r"^#{1,6}\s*第\s*\d+\s*页\s*$", stripped):
                continue
            if stripped:
                return stripped[:100]
        return ""

    def _split_long_answer(self, text: str, q_text: str) -> list[str]:
        """切分超长 A，每个子块前缀附上 Q"""
        from ..token_counter import count_tokens

        # 找出 A 部分的起始位置
        paragraphs = text.split("\n\n")
        chunks: list[str] = []
        buffer = ""
        buffer_tokens = 0

        for para in paragraphs:
            para_tokens = count_tokens(para)
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

        # 第一个 chunk 不需要额外标注（已含完整 Q）
        # 后续 chunk 需要标注所属 Q
        for i in range(1, len(chunks)):
            chunks[i] = f"_（接上问：{q_text}）_\n\n{chunks[i]}"

        return chunks if chunks else [text.strip()]

    def _paragraph_fallback(self, text: str) -> list[str]:
        """无 Q&A 边界时的段落切分兜底"""
        from ..token_counter import count_tokens

        paragraphs = text.split("\n\n")
        chunks: list[str] = []
        buffer = ""
        buffer_tokens = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = count_tokens(para)

            if para_tokens > self.max_size:
                if buffer:
                    chunks.append(buffer.strip())
                    buffer = ""
                    buffer_tokens = 0
                # 长段落硬切（在句号处断）
                sub = self._hard_split_on_sentence(para)
                chunks.extend(sub)
                continue

            if buffer_tokens + para_tokens <= self.max_size:
                buffer = f"{buffer}\n\n{para}" if buffer else para
                buffer_tokens += para_tokens
            else:
                chunks.append(buffer.strip())
                buffer = para
                buffer_tokens = para_tokens

        if buffer:
            chunks.append(buffer.strip())

        return chunks if chunks else [text.strip()]

    def _hard_split_on_sentence(self, text: str) -> list[str]:
        """在句号边界硬切"""
        from ..token_counter import count_chars

        target = int(self.target_size * 1.5)
        if count_chars(text) <= target:
            return [text.strip()]

        # 按句子边界切
        sentences = re.split(r"(?<=[。！？\.!\?])\s*", text)
        chunks: list[str] = []
        buffer = ""

        for s in sentences:
            if not s.strip():
                continue
            if len(buffer) + len(s) <= target:
                buffer += s
            else:
                if buffer:
                    chunks.append(buffer.strip())
                buffer = s

        if buffer:
            chunks.append(buffer.strip())

        return chunks if chunks else [text.strip()]
