"""指标金标准测试 — 固定向量验证各指标计算（防止指标回退）"""

import numpy as np
import pytest

from src.evaluation import metrics

# 固定向量（mock _embed_text 用）
V_DOC = np.array([1.0, 0.0], dtype=np.float32)  # 与 GT 余弦=1
V_NONE = np.array([0.0, 1.0], dtype=np.float32)  # 与 GT 余弦=0
V_GT = np.array([1.0, 0.0], dtype=np.float32)


def _mock_embed(text: str) -> np.ndarray:
    if "related" in text or "标准答案" in text:
        return V_DOC
    return V_NONE


@pytest.fixture(autouse=True)
def _mock(monkeypatch):
    monkeypatch.setattr(metrics, "_embed_text", _mock_embed)


GT = "标准答案"


class TestRecall:
    def test_hit(self):
        assert metrics.calculate_recall(["related 文档1"], GT, k=5) == 1.0

    def test_miss(self):
        assert metrics.calculate_recall(["无关 文档"], GT, k=5) == 0.0

    def test_empty(self):
        assert metrics.calculate_recall([], GT, k=5) == 0.0


class TestMRR:
    def test_first_rank(self):
        assert metrics.calculate_mrr(["related 文档"], GT) == 1.0

    def test_second_rank(self):
        assert metrics.calculate_mrr(["无关 文档", "related 文档"], GT) == 0.5

    def test_miss(self):
        assert metrics.calculate_mrr(["无关 文档"], GT) == 0.0


class TestPrecision:
    def test_mixed(self):
        assert (
            metrics.calculate_precision(["related 文档", "无关 文档"], GT, k=5) == 0.5
        )

    def test_empty(self):
        assert metrics.calculate_precision([], GT, k=5) == 0.0


class TestNDCG:
    def test_all_relevant(self):
        assert (
            metrics.calculate_ndcg(["related 文档1", "related 文档2"], GT, k=5) == 1.0
        )

    def test_bounded(self):
        ndcg = metrics.calculate_ndcg(
            ["related 文档1", "无关 文档", "related 文档2"], GT, k=5
        )
        assert 0.0 < ndcg < 1.0


class TestKeywordCoverage:
    def test_partial(self):
        assert (
            metrics.calculate_keyword_coverage("答案 包含 退货", ["退货", "退款"])
            == 0.5
        )

    def test_empty_keywords(self):
        assert metrics.calculate_keyword_coverage("答案", []) == 1.0


class TestLatencyScore:
    def test_fast_high_score(self):
        assert metrics.calculate_latency_score(100) > 0.5

    def test_slow_low_score(self):
        assert metrics.calculate_latency_score(10000) < 0.5

    def test_zero_and_negative(self):
        assert metrics.calculate_latency_score(0) >= 0
        assert metrics.calculate_latency_score(-1) >= 0
