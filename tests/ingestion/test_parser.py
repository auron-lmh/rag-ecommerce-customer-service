"""模块1解析器测试 — FAQ/Office/Web 本地解析（无需API Key）"""

import json
import tempfile
from pathlib import Path

from src.ingestion.models import DocType, ParseStatus
from src.ingestion.router import parse_file


class TestFAQParser:
    """FAQ JSON解析器"""

    def test_parse_valid_faq(self):
        faq_data = [
            {"question": "测试问题1", "answer": "测试回答1", "keywords": ["测试"]},
            {"question": "测试问题2", "answer": "测试回答2", "keywords": ["测试"]},
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(faq_data, f, ensure_ascii=False)
            tmp_path = f.name

        result = parse_file(tmp_path, DocType.FAQ_JSON)

        assert result.status == ParseStatus.SUCCESS
        assert len(result.elements) == 2
        assert "Q1:" in result.markdown
        assert "Q2:" in result.markdown

        Path(tmp_path).unlink()

    def test_parse_empty_faq(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump([], f)
            tmp_path = f.name

        result = parse_file(tmp_path, DocType.FAQ_JSON)
        assert result.status == ParseStatus.SUCCESS
        assert len(result.elements) == 0

        Path(tmp_path).unlink()

    def test_invalid_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("not valid json")
            tmp_path = f.name

        result = parse_file(tmp_path, DocType.FAQ_JSON)
        assert result.status == ParseStatus.FAILED

        Path(tmp_path).unlink()


class TestRouterDetection:
    """类型自动检测"""

    def test_detect_pdf(self):
        from src.ingestion.router import _detect_type

        assert _detect_type("test.pdf") == DocType.PDF

    def test_detect_word(self):
        from src.ingestion.router import _detect_type

        assert _detect_type("test.docx") == DocType.WORD

    def test_detect_excel(self):
        from src.ingestion.router import _detect_type

        assert _detect_type("test.xlsx") == DocType.EXCEL

    def test_detect_image(self):
        from src.ingestion.router import _detect_type

        assert _detect_type("photo.png") == DocType.IMAGE
        assert _detect_type("photo.jpg") == DocType.IMAGE

    def test_detect_web(self):
        from src.ingestion.router import _detect_type

        assert _detect_type("https://example.com") == DocType.WEB

    def test_detect_faq(self):
        from src.ingestion.router import _detect_type

        assert _detect_type("faq.json") == DocType.FAQ_JSON


class TestPDFWithoutAPI:
    """PDF解析需要API Key时给出明确错误"""

    def test_pdf_without_api_key(self):
        """不配置 API Key 时应返回 FAILED 而不是崩"""
        import os

        # 临时清除API Key
        old_key = os.environ.get("BAILIAN_API_KEY", "")
        os.environ["BAILIAN_API_KEY"] = ""

        # 找个不存在的文件测试
        result = parse_file("nonexistent.pdf", DocType.PDF)
        assert result.status == ParseStatus.FAILED

        if old_key:
            os.environ["BAILIAN_API_KEY"] = old_key
