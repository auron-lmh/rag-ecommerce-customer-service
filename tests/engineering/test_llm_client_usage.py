"""llm_client usage 捕获测试 — token 消耗不再丢失（P1 修复）"""

from src.engineering.llm_client import LLMClient


def test_usage_accumulation_and_reset():
    client = LLMClient()
    client.reset_usage()
    client._record_usage(
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    )
    client._record_usage(
        {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28}
    )
    assert client.total_usage == {
        "prompt_tokens": 30,
        "completion_tokens": 13,
        "total_tokens": 43,
    }

    client.reset_usage()
    assert client.total_usage["total_tokens"] == 0


def test_empty_usage_no_crash():
    client = LLMClient()
    client.reset_usage()
    client._record_usage({})
    assert client.total_usage["total_tokens"] == 0
    assert client.last_usage == {}
