"""模块2分块策略测试 — 4种策略 + 路由器 + 边界情况"""

from src.chunking.models import ChunkStrategy
from src.chunking.router import chunk_document
from src.chunking.strategies import (
    FAQSplitter,
    MarkdownSplitter,
    RecursiveSplitter,
    SemanticSplitter,
)
from src.chunking.token_counter import count_tokens
from src.ingestion.models import DocType

# ═══════════════════════════════════════
# Token 计数器
# ═══════════════════════════════════════


class TestTokenCounter:
    def test_count_chinese(self):
        tokens = count_tokens("这是一段中文测试文本用于验证token计数")
        assert tokens > 0

    def test_count_english(self):
        tokens = count_tokens("Hello world this is a test")
        assert tokens > 0

    def test_count_empty(self):
        tokens = count_tokens("")
        assert tokens == 0


# ═══════════════════════════════════════
# Markdown 切分器
# ═══════════════════════════════════════


class TestMarkdownSplitter:
    def test_basic_heading_split(self):
        text = "# 标题1\n\n正文内容在这里。\n\n## 标题2\n\n更多内容。"
        splitter = MarkdownSplitter(target_size=200)
        chunks = splitter.split(text)
        assert len(chunks) >= 2
        assert any("标题1" in c for c in chunks)
        assert any("标题2" in c for c in chunks)

    def test_no_headings(self):
        text = "这是一段没有任何标题的纯文本。它应该被切成段落块。"
        splitter = MarkdownSplitter(target_size=200)
        chunks = splitter.split(text)
        assert len(chunks) >= 1
        assert chunks[0]  # 至少有一块

    def test_code_block_preserved(self):
        text = "# 标题\n\n```python\nprint('hello')\nprint('world')\n```\n\n正文文字"
        splitter = MarkdownSplitter(target_size=200)
        chunks = splitter.split(text)
        all_text = " ".join(chunks)
        # 代码块应整体保留
        assert "print('hello')" in all_text

    def test_empty_text(self):
        splitter = MarkdownSplitter()
        assert splitter.split("") == []
        assert splitter.split("   ") == []


# ═══════════════════════════════════════
# FAQ 切分器
# ═══════════════════════════════════════


class TestFAQSplitter:
    def test_qa_pairs_preserved(self):
        text = """## Q1: 如何退货？

签收后7天内可申请退货。

## Q2: 退款多久到账？

1-3个工作日内原路返回。"""

        splitter = FAQSplitter(target_size=200)
        chunks = splitter.split(text)
        assert len(chunks) == 2
        assert "退货" in chunks[0]
        assert "退款" in chunks[1]
        # 确保 Q1 和 Q2 不在同一块
        assert not ("Q2" in chunks[0] and "Q1" in chunks[0])

    def test_chinese_qa_format(self):
        text = "问：怎么联系客服？\n答：在App内点击客服中心。\n\n问：服务时间？\n答：每天9:00-21:00。"
        splitter = FAQSplitter(target_size=200)
        chunks = splitter.split(text)
        assert len(chunks) == 2

    def test_no_qa_boundary(self):
        text = "这是一段纯文本，没有任何Q&A格式标记。"
        splitter = FAQSplitter(target_size=200)
        chunks = splitter.split(text)
        assert len(chunks) >= 1

    def test_long_answer_split(self):
        # 构造超长回答（确保token数超过max_size=500）
        long_answer = "A" * 8000
        text = f"## Q1: 问题\n\n{long_answer}"
        splitter = FAQSplitter(target_size=100, max_size=500)
        chunks = splitter.split(text)
        assert len(chunks) > 1
        # 第一个chunk应包含完整Q
        assert "Q1" in chunks[0]


# ═══════════════════════════════════════
# 递归切分器
# ═══════════════════════════════════════


class TestRecursiveSplitter:
    def test_short_text_no_split(self):
        text = "短文本"
        splitter = RecursiveSplitter(target_size=500)
        chunks = splitter.split(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_paragraph_split(self):
        # 足够长的文本才能触发切分
        text = "第一段内容。" * 30 + "\n\n" + "第二段内容。" * 30
        splitter = RecursiveSplitter(target_size=50, max_size=150)
        chunks = splitter.split(text)
        assert len(chunks) >= 2

    def test_long_text_splits(self):
        text = "测试文本。" * 200
        splitter = RecursiveSplitter(target_size=100, max_size=300)
        chunks = splitter.split(text)
        assert len(chunks) > 1
        # 每块不应超过 max_size
        for c in chunks:
            assert len(c) <= 600  # 字符～token比例

    def test_empty(self):
        splitter = RecursiveSplitter()
        assert splitter.split("") == []


# ═══════════════════════════════════════
# 语义切分器
# ═══════════════════════════════════════


class TestSemanticSplitter:
    def test_sentence_boundary_split(self):
        text = "这是第一句话。这是第二句话。这是第三句话。这是第四句话。"
        splitter = SemanticSplitter(target_size=10, max_size=50)
        chunks = splitter.split(text)
        assert len(chunks) >= 1

    def test_no_sentence_end(self):
        text = "这是一段没有标点符号的连续文本内容用来测试"
        splitter = SemanticSplitter(target_size=200)
        chunks = splitter.split(text)
        assert len(chunks) >= 1

    def test_mixed_cn_en(self):
        text = "中文内容。English text here. 继续中文。More English."
        splitter = SemanticSplitter(target_size=50, max_size=200)
        chunks = splitter.split(text)
        assert len(chunks) >= 1

    def test_empty(self):
        splitter = SemanticSplitter()
        assert splitter.split("") == []


# ═══════════════════════════════════════
# 路由器
# ═══════════════════════════════════════


class TestRouter:
    def test_faq_uses_faq_strategy(self):
        text = "## Q1: 问题1\n\n回答1\n\n## Q2: 问题2\n\n回答2"
        result = chunk_document(text, "faq.json", DocType.FAQ_JSON)
        assert result.strategy == ChunkStrategy.FAQ
        assert len(result.chunks) == 2

    def test_pdf_uses_markdown_strategy(self):
        text = "# 标题\n\n正文内容。"
        result = chunk_document(text, "doc.pdf", DocType.PDF)
        assert result.strategy == ChunkStrategy.MARKDOWN

    def test_unknown_doc_type_fallback(self):
        text = "纯文本内容"
        result = chunk_document(text, "data.txt", DocType.PLAIN_TEXT)
        assert len(result.chunks) >= 1

    def test_chunk_metadata_populated(self):
        text = "# 退货政策\n\n## 退款流程\n\n退款在1-3个工作日内到账。"
        result = chunk_document(text, "policy.pdf", DocType.PDF)
        for chunk in result.chunks:
            assert chunk.chunk_id
            assert chunk.strategy == ChunkStrategy.MARKDOWN
            assert chunk.total_chunks > 0

    def test_empty_text_returns_empty(self):
        result = chunk_document("", "empty.md", DocType.PLAIN_TEXT)
        assert len(result.chunks) == 0
