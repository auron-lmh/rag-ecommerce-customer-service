"""模块14 评估指标 — LLM忠实度评估 / Embedding语义召回 / 关键词覆盖 / 延迟

指标说明:
    recall@K       → Embedding 余弦相似度判断相关性 (替代子串匹配)
    mrr            → Embedding 相似度计算首位相关文档排名
    faithfulness   → LLM G-Eval 风格评估 (替代单词重叠率)
    keyword_coverage → 字符串匹配 (天然适合关键词覆盖)
    latency_score  → 延迟归一化 (非 LLM 指标)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Embedding 相关性阈值
RELEVANCE_THRESHOLD = 0.70

# LLM Faithfulness 评估 Prompt
FAITHFULNESS_PROMPT = """你是一个严格的评估专家。请判断以下回答是否忠实于参考文档。

参考文档:
{retrieved_docs}

待评估回答:
{answer}

评估规则:
1. 回答中的每个事实断言都必须在参考文档中找到明确依据
2. 如果回答添加了参考文档中没有的信息，标记为不忠实
3. 如果回答说"无法确认"/"建议咨询人工客服"，视为诚实（高忠实度）

请输出JSON格式:
{{
    "faithfulness_score": 0.85,
    "is_faithful": true,
    "hallucinated_claims": ["编造的事实1", "编造的事实2"],
    "reasoning": "评估理由"
}}

其中 faithfulness_score 为 0~1 的忠实度分数。"""


def _get_embedder():
    """延迟加载 embedder（避免循环导入）"""
    try:
        from src.embedding.embedder import get_embedder

        return get_embedder()
    except Exception as e:
        logger.debug("Embedder 不可用: %s", e)
        return None


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _embed_text(text: str) -> Optional[list[float]]:
    """将文本转为向量"""
    embedder = _get_embedder()
    if embedder is None:
        return None
    try:
        vec = embedder.embed_query(text)
        if hasattr(vec, "tolist"):
            return vec.tolist()
        return list(vec)
    except Exception as e:
        logger.warning("Embedding 失败: %s", e)
        return None


# ═══════════════════════════════════════
# Recall / MRR — Embedding 语义相似度
# ═══════════════════════════════════════


def calculate_recall(retrieved_docs: list[str], ground_truth: str, k: int = 5) -> float:
    """Recall@K — 用 Embedding 语义相似度判断文档相关性

    替代原来的子串匹配实现。如果 Embedder 不可用，自动降级为子串匹配。

    Args:
        retrieved_docs: 检索到的文档文本列表
        ground_truth: 标准答案/主题
        k: 取前 K 个结果

    Returns:
        0.0 或 1.0（至少一篇文档相关则为 1.0）
    """
    if not retrieved_docs or not ground_truth:
        return 0.0

    top_k = retrieved_docs[:k]

    # 尝试 Embedding 相似度
    gt_vec = _embed_text(ground_truth)
    if gt_vec is not None:
        for doc in top_k:
            doc_vec = _embed_text(doc)
            if doc_vec is None:
                continue
            sim = _cosine_sim(gt_vec, doc_vec)
            if sim >= RELEVANCE_THRESHOLD:
                return 1.0
        return 0.0

    # 降级: 子串匹配
    logger.debug("Embedder 不可用，Recall 降级为子串匹配")
    ground_truth_lower = ground_truth.lower()
    for doc in top_k:
        if ground_truth_lower in doc.lower():
            return 1.0
    return 0.0


def calculate_mrr(retrieved_docs: list[str], ground_truth: str) -> float:
    """MRR (Mean Reciprocal Rank) — 用 Embedding 语义相似度

    替代原来的子串匹配实现。如果 Embedder 不可用，自动降级为子串匹配。

    Args:
        retrieved_docs: 检索到的文档文本列表
        ground_truth: 标准答案/主题

    Returns:
        1/rank（如果找到相关文档），否则 0.0
    """
    if not retrieved_docs or not ground_truth:
        return 0.0

    # 尝试 Embedding 相似度
    gt_vec = _embed_text(ground_truth)
    if gt_vec is not None:
        for i, doc in enumerate(retrieved_docs):
            doc_vec = _embed_text(doc)
            if doc_vec is None:
                continue
            sim = _cosine_sim(gt_vec, doc_vec)
            if sim >= RELEVANCE_THRESHOLD:
                return 1.0 / (i + 1)
        return 0.0

    # 降级: 子串匹配
    logger.debug("Embedder 不可用，MRR 降级为子串匹配")
    ground_truth_lower = ground_truth.lower()
    for i, doc in enumerate(retrieved_docs):
        if ground_truth_lower in doc.lower():
            return 1.0 / (i + 1)
    return 0.0


# ═══════════════════════════════════════
# Faithfulness — LLM G-Eval 评估
# ═══════════════════════════════════════


def calculate_faithfulness(
    answer: str,
    sources: list[str],
    use_llm: bool = True,
) -> float:
    """忠实度评估 — LLM G-Eval 风格 (替代单词重叠率)

    Args:
        answer: 生成的回答
        sources: 参考文档列表
        use_llm: 是否使用 LLM 评估（默认 True）

    Returns:
        忠实度分数 (0~1)
    """
    if not answer or not sources:
        return 0.0

    if use_llm:
        llm_score = calculate_faithfulness_llm(answer, sources)
        if llm_score is not None:
            return llm_score
        logger.debug("LLM 忠实度评估不可用，降级为 embedding 评估")

    # 降级: Embedding 相似度
    return calculate_faithfulness_fast(answer, sources)


def calculate_faithfulness_llm(answer: str, sources: list[str]) -> Optional[float]:
    """LLM-based 忠实度评估 — 调用 LLM 判断回答是否忠实于文档

    Args:
        answer: 生成的回答
        sources: 参考文档列表

    Returns:
        忠实度分数 (0~1)，如果 LLM 不可用返回 None
    """
    from src.engineering.llm_client import get_llm_client

    docs_text = "\n\n".join(
        f"[文档{i+1}] {d[:1000]}" for i, d in enumerate(sources[:5])
    )

    try:
        client = get_llm_client()
        data = client.chat_json(
            messages=[
                {
                    "role": "user",
                    "content": FAITHFULNESS_PROMPT.format(
                        retrieved_docs=docs_text,
                        answer=answer,
                    ),
                }
            ],
            temperature=0.1,
            max_tokens=1024,
            timeout=30,
        )
        score = float(data.get("faithfulness_score", 0.5))
        return max(0.0, min(1.0, score))

    except Exception as e:
        logger.warning("LLM 忠实度评估失败: %s", e)
        return None


def calculate_faithfulness_fast(answer: str, sources: list[str]) -> float:
    """快速忠实度评估 — Embedding 相似度（LLM 不可用时的降级方案）

    将回答和合并的源文档转为向量，计算余弦相似度。
    比原来的单词重叠率更可靠。
    """
    if not answer or not sources:
        return 0.0

    # 合并源文档
    merged_sources = " ".join(sources)
    if not merged_sources.strip():
        return 0.0

    answer_vec = _embed_text(answer)
    source_vec = _embed_text(merged_sources)

    if answer_vec is not None and source_vec is not None:
        sim = _cosine_sim(answer_vec, source_vec)
        # Embedding 相似度通常在 0.6-0.9，线性映射到 0-1
        return max(0.0, min(1.0, sim))

    # 最终降级: 原来的单词重叠率
    logger.debug("Embedding 不可用，Faithfulness 降级为单词重叠率")
    answer_words = set(answer.lower().split())
    source_text = merged_sources.lower()
    source_words = set(source_text.split())

    if not answer_words:
        return 0.0

    overlap = answer_words.intersection(source_words)
    return len(overlap) / len(answer_words)


# ═══════════════════════════════════════
# Keyword Coverage — 保留原实现（天然适合字符串匹配）
# ═══════════════════════════════════════


def calculate_keyword_coverage(answer: str, must_contain_keywords: list[str]) -> float:
    """关键词覆盖率 — 检查回答是否包含必须的关键词

    Args:
        answer: 生成的回答
        must_contain_keywords: 必须包含的关键词列表

    Returns:
        覆盖率 (0~1)
    """
    if not must_contain_keywords:
        return 1.0

    answer_lower = answer.lower()
    covered = sum(1 for kw in must_contain_keywords if kw.lower() in answer_lower)
    return covered / len(must_contain_keywords)


# ═══════════════════════════════════════
# Latency Score — 保留原实现（非 LLM 指标）
# ═══════════════════════════════════════


def calculate_latency_score(latency_ms: float, threshold_ms: float = 1000) -> float:
    """延迟分数 — 越快越高

    Args:
        latency_ms: 实际延迟（毫秒）
        threshold_ms: 阈值（毫秒）

    Returns:
        分数 (0~1)，越快越高
    """
    if latency_ms <= 0:
        return 1.0
    if latency_ms >= threshold_ms * 3:
        return 0.0
    return max(0.0, 1.0 - latency_ms / (threshold_ms * 3))
