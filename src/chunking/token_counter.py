"""Token 估算 — 优先用 tiktoken（精确），不可用时降级为字符估算

cl100k_base: OpenAI text-embedding-3 和大多数现代embedding模型使用
"""

from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=1)
def _get_tiktoken_encoder() -> Optional[object]:
    """懒加载tiktoken——只有真正需要时才导入"""
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except (ImportError, Exception):
        return None


def count_tokens(text: str) -> int:
    """计算文本的token数

    - 有tiktoken时: 精确cl100k_base token数
    - 无tiktoken时: 中英文混合估算（中文≈2 char/token, 英文≈4 char/token）
    """
    enc = _get_tiktoken_encoder()
    if enc is not None:
        return len(enc.encode(text))

    # ── 降级：中英文混合字符估算 ──
    chinese_chars = sum(1 for c in text if "一" <= c <= "鿿")
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 3.5)


def count_chars(text: str) -> int:
    """计算字符数（包含空白）"""
    return len(text)
