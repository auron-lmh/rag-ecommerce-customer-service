"""分类器兜底测试 — 优惠券/指代词不判 chitchat（让记忆实机生效）"""

from src.routing.classifier import IntentClassifier
from src.routing.models import Intent


def _fb(q: str):
    return IntentClassifier()._fallback_classify(q)


class TestCouponNotChitchat:
    def test_coupon_usage(self):
        assert _fb("优惠券怎么用").intent == Intent.PRODUCT_CONSULT

    def test_coupon_with_coreference(self):
        assert _fb("上次那个券怎么用").intent == Intent.PRODUCT_CONSULT

    def test_coupon_combined(self):
        assert _fb("这个能和其他优惠券一起用吗").intent == Intent.PRODUCT_CONSULT

    def test_redpacket(self):
        assert _fb("红包怎么领").intent == Intent.PRODUCT_CONSULT


class TestCoreferenceNotChitchat:
    def test_it_support(self):
        assert _fb("它支持快充吗").intent == Intent.PRODUCT_CONSULT

    def test_that_one(self):
        assert _fb("那个能退吗").intent in (
            Intent.PRODUCT_CONSULT,
            Intent.RETURN_REFUND,
        )

    def test_last_time(self):
        assert _fb("上次说的怎么操作").intent == Intent.PRODUCT_CONSULT


class TestPureChitchatStillChitchat:
    def test_greeting(self):
        assert _fb("你好").intent == Intent.CHITCHAT

    def test_time_question(self):
        assert _fb("现在几点了").intent == Intent.CHITCHAT

    def test_thanks(self):
        assert _fb("谢谢你的帮助").intent == Intent.CHITCHAT
