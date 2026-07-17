"""模块1清洗器测试 — Markdown统一清洗"""

from src.ingestion.clean_markdown import (
    _clean_paragraph,
    _dedup_paragraphs,
    _is_noise_only,
    clean_markdown,
)
from src.ingestion.models import CleanedDocument, DocType


class TestCleanParagraph:
    """单个段落清洗"""

    def test_remove_copyright(self):
        text = "这是正文内容。版权所有 © 2024 保留所有权利"
        cleaned, removed = _clean_paragraph(text)
        assert "版权所有" not in cleaned
        assert "copyright" in removed

    def test_remove_urls(self):
        text = "查看详情 https://example.com/product/123 了解更多"
        cleaned, removed = _clean_paragraph(text)
        assert "https://" not in cleaned
        assert "url" in removed

    def test_keep_normal_text(self):
        text = "这是一段正常的商品描述文本，没有需要移除的噪音。"
        cleaned, removed = _clean_paragraph(text)
        assert text in cleaned or cleaned == text
        assert len(removed) == 0

    def test_remove_page_numbers(self):
        text = "5"  # 孤立的页码
        cleaned, removed = _clean_paragraph(text)
        assert cleaned == "" or "page_number" in removed

    def test_remove_promotion(self):
        text = "扫码关注公众号获取更多优惠"
        cleaned, removed = _clean_paragraph(text)
        assert "promotion" in removed


class TestIsNoiseOnly:
    """纯噪音检测"""

    def test_empty_is_noise(self):
        assert _is_noise_only("")
        assert _is_noise_only("   ")

    def test_punctuation_only_is_noise(self):
        assert _is_noise_only("。，！？")

    def test_too_short_is_noise(self):
        assert _is_noise_only("a b")

    def test_normal_text_is_not_noise(self):
        assert not _is_noise_only("这是正常的商品描述文本")


class TestDedup:
    """去重"""

    def test_duplicate_removed(self):
        docs = [
            CleanedDocument(
                chunk_id="1",
                content="完全相同的内容",
                char_count=10,
                source_file="test.md",
                doc_type=DocType.PDF,
            ),
            CleanedDocument(
                chunk_id="2",
                content="完全相同的内容",
                char_count=10,
                source_file="test.md",
                doc_type=DocType.PDF,
            ),
        ]
        result = _dedup_paragraphs(docs)
        assert len(result) == 1

    def test_unique_preserved(self):
        docs = [
            CleanedDocument(
                chunk_id="1",
                content="内容A",
                char_count=3,
                source_file="test.md",
                doc_type=DocType.PDF,
            ),
            CleanedDocument(
                chunk_id="2",
                content="内容B完全不同",
                char_count=6,
                source_file="test.md",
                doc_type=DocType.PDF,
            ),
        ]
        result = _dedup_paragraphs(docs)
        assert len(result) == 2


class TestCleanMarkdown:
    """完整清洗流水线"""

    def test_full_pipeline(self):
        markdown = """# 售后服务政策

## 退货说明

用户可在签收后7天内申请退货。商品须保持原包装完好。

扫码关注获取更多优惠

版权所有 © 2024 某电商平台 保留所有权利

## 退款流程

退款将在1-3个工作日内原路返回。"""

        chunks = clean_markdown(markdown, "policy.pdf", DocType.PDF)

        # 应该包含核心内容块
        assert len(chunks) > 0
        all_text = " ".join(c.content for c in chunks)
        assert "退货" in all_text
        assert "退款" in all_text
        # 噪音被移除
        assert "版权所有" not in all_text
        assert "扫码关注" not in all_text

    def test_empty_input(self):
        chunks = clean_markdown("", "empty.pdf", DocType.PDF)
        assert len(chunks) == 0

        chunks = clean_markdown("   ", "empty.pdf", DocType.PDF)
        assert len(chunks) == 0
