"""classifier 降级测试 — LLM 返回 malformed 输出时降级关键词兜底，不崩溃（P1 修复）"""

from src.routing.classifier import IntentClassifier
from src.routing.models import Intent


def _classifier_with_chat(monkeypatch, response):
    cls = IntentClassifier()
    monkeypatch.setattr(cls._client, "chat", lambda **kw: response)
    return cls


def test_degrades_on_invalid_json(monkeypatch):
    """LLM 返回非 JSON → 降级关键词匹配，不抛 JSONDecodeError"""
    cls = _classifier_with_chat(monkeypatch, "这不是 JSON")
    result = cls.classify("我要退货")
    assert result.intent == Intent.RETURN_REFUND  # 关键词兜底命中"退货"


def test_degrades_on_bad_confidence(monkeypatch):
    """confidence 非数字 → 降级关键词匹配，不抛 ValueError"""
    cls = _classifier_with_chat(
        monkeypatch, '{"intent": "return_refund", "confidence": "abc"}'
    )
    result = cls.classify("我要退货")
    assert result.intent == Intent.RETURN_REFUND
