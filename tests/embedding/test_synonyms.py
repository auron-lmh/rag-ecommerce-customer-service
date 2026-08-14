"""同义词扩展测试 — 口语词映射到标准术语，提升 BM25 关键词召回"""

from src.embedding.synonyms import expand_query_with_synonyms


def test_expand_variant_to_standard():
    """query 含变体（口语）→ 补上标准词 + 其他变体"""
    q = expand_query_with_synonyms("怎么退钱")
    assert "退款" in q  # 补上标准词
    assert "返款" in q


def test_expand_standard_adds_variants():
    """query 含标准词 → 补上变体"""
    q = expand_query_with_synonyms("退款多久到账")
    assert "退钱" in q
    assert "返款" in q


def test_no_synonym_no_change():
    """无关词不扩展，原样返回"""
    q = expand_query_with_synonyms("今天天气怎么样")
    assert q == "今天天气怎么样"
