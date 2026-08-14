"""retrieval_judge 降级测试 — LLM 返回坏 JSON / 内容异常时不崩溃，默认检索"""

from src.conversation.retrieval_judge import RetrievalJudge


def _judge_with_chat(monkeypatch, response):
    judge = RetrievalJudge()
    monkeypatch.setattr(judge._client, "chat", lambda **kw: response)
    return judge


def test_degrades_on_invalid_json(monkeypatch):
    """LLM 返回非 JSON → 降级默认检索，不抛 JSONDecodeError 崩溃"""
    judge = _judge_with_chat(monkeypatch, "这不是合法 JSON")
    need, reason = judge.should_retrieve(
        "怎么退货", [{"role": "user", "content": "你好"}]
    )
    assert need is True
    assert "默认检索" in reason


def test_degrades_on_none_content(monkeypatch):
    """history content 为 None → 触发 TypeError 应被降级捕获，而非崩溃"""
    judge = _judge_with_chat(monkeypatch, '{"need_retrieval": false}')
    need, reason = judge.should_retrieve(
        "怎么退货", [{"role": "user", "content": None}]
    )
    assert need is True
    assert "默认检索" in reason
