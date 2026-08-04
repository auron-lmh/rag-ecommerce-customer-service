"""路由指代词护栏测试 — chitchat + 指代词 → 强制走 RAG"""

from src.routing.models import Intent, IntentResult, RouteTarget
from src.routing.router import IntentRouter, _has_coreference


class TestHasCoreference:
    def test_coreference_detected(self):
        assert _has_coreference("上次那个券怎么用") is True
        assert _has_coreference("它支持快充吗") is True
        assert _has_coreference("那个能退吗") is True

    def test_no_coreference(self):
        assert _has_coreference("你好") is False
        assert _has_coreference("怎么退货") is False
        assert _has_coreference("现在几点了") is False


class _FakeClassifier:
    def __init__(self, intent: Intent):
        self._intent = intent

    def classify(self, query: str) -> IntentResult:
        return IntentResult(intent=self._intent, confidence=0.5, reasoning="fake")


class TestCoreferenceGuard:
    def test_chitchat_with_coreference_reroutes_to_rag(self):
        """LLM 误判 chitchat + 含指代词 → 改走 RAG（记忆/检索生效）"""
        r = IntentRouter(classifier=_FakeClassifier(Intent.CHITCHAT))
        result = r.route("上次那个券怎么用")
        assert result.intent_result.intent == Intent.PRODUCT_CONSULT
        assert result.target == RouteTarget.RAG

    def test_chitchat_without_coreference_stays_direct(self):
        """纯闲聊无指代词 → 保持 chitchat/direct"""
        r = IntentRouter(classifier=_FakeClassifier(Intent.CHITCHAT))
        result = r.route("你好")
        assert result.intent_result.intent == Intent.CHITCHAT
        assert result.target == RouteTarget.DIRECT
