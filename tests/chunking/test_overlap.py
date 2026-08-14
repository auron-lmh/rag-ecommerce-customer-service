"""chunk overlap 接线测试 — 相邻 chunk 之间保留边界重叠（P1 修复）"""

from src.chunking.router import chunk_document


def test_overlap_wired_between_chunks():
    """长文本切分后，相邻 chunk 有重叠内容"""
    # 构造足够长的文本（超过 target_size=512 token 才切分）
    sentence = "这是一段测试内容，包含足够多的字符用来验证分块重叠逻辑是否正确工作。"
    text = (sentence + "\n") * 60

    result = chunk_document(text, source_file="test.txt", overlap=50)

    # 至少切成多块
    assert len(result.chunks) >= 2

    overlapped = [c for c in result.chunks if c.overlap_with_prev]
    assert len(overlapped) > 0
    # 重叠内容 = 前一块纯内容尾部 50 字符
    assert overlapped[0].overlap_content


def test_no_overlap_when_zero():
    """overlap=0 时不产生重叠（向后兼容）"""
    sentence = "这是一段测试内容，包含足够多的字符用来验证分块重叠逻辑是否正确工作。"
    text = (sentence + "\n") * 60

    result = chunk_document(text, source_file="test.txt", overlap=0)

    assert all(not c.overlap_with_prev for c in result.chunks)
