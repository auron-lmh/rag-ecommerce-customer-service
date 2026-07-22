"""模块14 评估指标 — Recall@K / MRR / Faithfulness / Keyword Coverage"""

from typing import Optional


def calculate_recall(retrieved_docs: list[str], ground_truth: str, k: int = 5) -> float:
    """计算 Recall@K

    Args:
        retrieved_docs: 检索到的文档列表
        ground_truth: 标准答案
        k: 取前 K 个结果

    Returns:
        0.0 或 1.0（是否命中）
    """
    if not retrieved_docs or not ground_truth:
        return 0.0

    top_k = retrieved_docs[:k]
    ground_truth_lower = ground_truth.lower()

    for doc in top_k:
        if ground_truth_lower in doc.lower():
            return 1.0
    return 0.0


def calculate_mrr(retrieved_docs: list[str], ground_truth: str) -> float:
    """计算 MRR (Mean Reciprocal Rank)

    Args:
        retrieved_docs: 检索到的文档列表
        ground_truth: 标准答案

    Returns:
        1/rank（如果命中），否则 0.0
    """
    if not retrieved_docs or not ground_truth:
        return 0.0

    ground_truth_lower = ground_truth.lower()

    for i, doc in enumerate(retrieved_docs):
        if ground_truth_lower in doc.lower():
            return 1.0 / (i + 1)
    return 0.0


def calculate_faithfulness(answer: str, sources: list[str]) -> float:
    """计算忠实度（简化版）

    Args:
        answer: 生成的回答
        sources: 参考文档

    Returns:
        忠实度分数 (0~1)
    """
    if not answer or not sources:
        return 0.0

    # 简化实现：检查回答中的关键信息是否在源文档中出现
    answer_words = set(answer.lower().split())
    source_text = " ".join(sources).lower()
    source_words = set(source_text.split())

    if not answer_words:
        return 0.0

    overlap = answer_words.intersection(source_words)
    return len(overlap) / len(answer_words)


def calculate_keyword_coverage(answer: str, must_contain_keywords: list[str]) -> float:
    """计算关键词覆盖率

    Args:
        answer: 生成的回答
        must_contain_keywords: 必须包含的关键词

    Returns:
        覆盖率 (0~1)
    """
    if not must_contain_keywords:
        return 1.0

    answer_lower = answer.lower()
    covered = sum(1 for kw in must_contain_keywords if kw.lower() in answer_lower)
    return covered / len(must_contain_keywords)


def calculate_latency_score(latency_ms: float, threshold_ms: float = 1000) -> float:
    """计算延迟分数

    Args:
        latency_ms: 实际延迟
        threshold_ms: 阈值

    Returns:
        分数 (0~1)，越快越高
    """
    if latency_ms <= 0:
        return 1.0
    if latency_ms >= threshold_ms * 3:
        return 0.0
    return max(0, 1 - latency_ms / (threshold_ms * 3))
