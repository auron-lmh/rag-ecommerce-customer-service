"""指代消解测试 — 结合会话历史补全追问"""

from src.conversation.coreference import CoreferenceResolver


class _FakeClient:
    """模拟 LLM 客户端"""

    def __init__(self, response=None, fail=False):
        self._response = response
        self._fail = fail

    def chat_with_fallback(self, messages, fallback_value="", **kwargs):
        if self._fail:
            return fallback_value
        return self._response


def test_no_history_returns_original():
    r = CoreferenceResolver()
    assert r.resolve("那需要运费吗？", []) == "那需要运费吗？"


def test_no_query_returns_original():
    r = CoreferenceResolver()
    assert r.resolve("", [{"role": "user", "content": "退货流程是什么？"}]) == ""


def test_completes_with_history(monkeypatch):
    r = CoreferenceResolver()
    monkeypatch.setattr(
        "src.conversation.coreference.get_llm_client",
        lambda: _FakeClient(response="退货需要运费吗"),
    )
    out = r.resolve(
        "那需要运费吗？",
        [{"role": "user", "content": "退货流程是什么？"}],
    )
    assert out == "退货需要运费吗"


def test_llm_failure_falls_back(monkeypatch):
    """LLM 调用失败 → 降级用原 query（retrieval_judge 同款策略）"""
    r = CoreferenceResolver()
    monkeypatch.setattr(
        "src.conversation.coreference.get_llm_client",
        lambda: _FakeClient(fail=True),
    )
    out = r.resolve(
        "那需要运费吗？",
        [{"role": "user", "content": "退货流程是什么？"}],
    )
    assert out == "那需要运费吗？"


def test_only_uses_recent_history(monkeypatch):
    """只取最近几轮历史（滑动窗口），不应报错"""
    r = CoreferenceResolver()
    monkeypatch.setattr(
        "src.conversation.coreference.get_llm_client",
        lambda: _FakeClient(response="补全结果"),
    )
    long_history = [{"role": "user", "content": f"问题{i}"} for i in range(20)]
    out = r.resolve("它支持快充吗？", long_history)
    assert out == "补全结果"
