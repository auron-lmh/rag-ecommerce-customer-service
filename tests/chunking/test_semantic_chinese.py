"""SemanticSplitter 中文切分测试 — 句号后无空格也能切分（P1 修复）"""

from src.chunking.strategies.semantic import SemanticSplitter


def test_chinese_sentence_split_without_space():
    """中文句号后无空格（常见写法）→ 应能切分成多句（修复前 \s+ 匹配不到，返回 1 句）"""
    splitter = SemanticSplitter(target_size=50, min_size=10, max_size=200)
    text = "这是第一句话。这是第二句话。这是第三句话。这是第四句话。"
    sentences = splitter._split_sentences(text)
    assert len(sentences) >= 4


def test_english_sentence_split_still_works():
    """英文句号后有空格 → 仍正常切分（回归保护）"""
    splitter = SemanticSplitter(target_size=50, min_size=10, max_size=200)
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    sentences = splitter._split_sentences(text)
    assert len(sentences) >= 4
