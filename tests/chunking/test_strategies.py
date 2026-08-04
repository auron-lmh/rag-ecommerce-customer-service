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


# ═══════════════════════════════════════
# 改进A: 内容级 QA 自动检测（PDF 含问答 → FAQ 保整）
# ═══════════════════════════════════════


class TestFAQAutoDetect:
    def test_pdf_qa_content_routes_to_faq(self):
        """PDF 内容若为 QA 形式，应自动走 FAQ 保整策略"""
        text = "Q1：如何申请退货？\n签收后7天内可申请退货。\n\nQ2：退款多久到账？\n1-3个工作日内原路返回。"
        result = chunk_document(text, "faq.pdf", DocType.PDF)
        assert result.strategy == ChunkStrategy.FAQ
        assert len(result.chunks) >= 2

    def test_pdf_markdown_qa_heads_routes_to_faq(self):
        """Markdown 标题式 Q&A 也应触发 FAQ 策略"""
        text = "## Q1: 如何退货？\n\n签收后7天内可申请退货。\n\n## Q2: 退款多久到账？\n\n1-3个工作日。"
        result = chunk_document(text, "faq.pdf", DocType.PDF)
        assert result.strategy == ChunkStrategy.FAQ
        # Q1 和 Q2 不拆散在同一块
        assert not (
            "Q2" in result.chunks[0].content and "Q1" in result.chunks[0].content
        )

    def test_plain_pdf_keeps_markdown_strategy(self):
        """无 QA 标记的 PDF 不误判，仍走 Markdown 策略"""
        text = "# 退货政策\n\n## 退款流程\n\n退款在1-3个工作日内到账。"
        result = chunk_document(text, "policy.pdf", DocType.PDF)
        assert result.strategy == ChunkStrategy.MARKDOWN

    def test_single_qa_marker_is_not_enough(self):
        """仅 1 个 QA 标记不触发（避免普通正文误判）"""
        text = "# 常见问题\n\n## Q1: 如何退货？\n\n签收后7天内可申请退货。"
        result = chunk_document(text, "doc.pdf", DocType.PDF)
        assert result.strategy == ChunkStrategy.MARKDOWN


# ═══════════════════════════════════════
# 改进C: base64 内嵌图片从 chunk 内容剥离
# ═══════════════════════════════════════


class TestBase64Strip:
    B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

    def test_chunk_content_strips_base64(self):
        text = (
            f"用户咨询内容。\n\n![图片](data:image/jpeg;base64,{self.B64})\n\n"
            "客服回复内容。"
        )
        result = chunk_document(text, "chat.pdf", DocType.PDF)
        all_content = " ".join(c.content for c in result.chunks)
        assert "base64" not in all_content
        assert "data:image" not in all_content
        # 图片前后的文字应保留
        assert "用户咨询内容" in all_content
        assert "客服回复内容" in all_content

    def test_png_base64_stripped(self):
        text = f"![商品图](data:image/png;base64,{self.B64})"
        result = chunk_document(text, "doc.pdf", DocType.PDF)
        all_content = " ".join(c.content for c in result.chunks)
        assert "data:image" not in all_content

    def test_strip_helper(self):
        from src.chunking.router import _strip_inline_images

        assert "base64" not in _strip_inline_images(
            f"![图片](data:image/jpeg;base64,{self.B64})"
        )
        assert _strip_inline_images("普通文本") == "普通文本"
        assert _strip_inline_images("") == ""


# ═══════════════════════════════════════
# 改进: .md 含标题 → MarkdownSplitter
# ═══════════════════════════════════════


class TestMarkdownHeadingDetect:
    def test_md_with_headings_uses_markdown(self):
        """MD 文档含标题 → 按标题层级切分"""
        text = "# 退货政策\n\n## 退货流程\n\n第一步：申请售后\n\n## 运费规则\n\n质量问题商家承担"
        result = chunk_document(text, "policy.md", DocType.PLAIN_TEXT)
        assert result.strategy == ChunkStrategy.MARKDOWN
        assert any("退货流程" in c.content for c in result.chunks)

    def test_md_without_headings_uses_recursive(self):
        """MD 文档无标题 → 递归切分"""
        text = "这是一段没有标题的纯文本内容，用于验证路由。"
        result = chunk_document(text, "notes.md", DocType.PLAIN_TEXT)
        assert result.strategy == ChunkStrategy.RECURSIVE

    def test_empty_text_no_headings(self):
        result = chunk_document("", "empty.md", DocType.PLAIN_TEXT)
        assert len(result.chunks) == 0


# ═══════════════════════════════════════
# 切分策略尺寸记录（检测"切分策略变更"）
# ═══════════════════════════════════════


class TestChunkSizeRecording:
    def test_target_size_recorded(self):
        """chunk 记录切分目标尺寸（用于检测策略变更）"""
        text = "## Q1: 怎么退货？\n\n签收后7天内可申请退货。\n\n## Q2: 退款多久到账？\n\n1-3个工作日。"
        result = chunk_document(text, "faq.md", DocType.FAQ_JSON, target_size=200)
        assert result.chunks[0].target_size == 200

    def test_target_size_default(self):
        result = chunk_document("普通文本内容", "a.txt", DocType.PLAIN_TEXT)
        assert result.chunks[0].target_size == 512
