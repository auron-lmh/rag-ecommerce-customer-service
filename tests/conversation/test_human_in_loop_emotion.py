"""人工介入情绪升级测试 — 愤怒/极端转人工"""

from src.conversation.human_in_loop import get_human_handler


class TestEmotionEscalation:
    def test_extreme_escalates(self):
        """情绪极端 → 直接升级人工，高优先级"""
        handler = get_human_handler()
        r = handler.check_needs_human(
            query="垃圾公司，我要起诉你", intent="complaint", emotion="extreme"
        )
        assert r["needs_human"] is True
        assert r["priority"] == "high"
        assert r["scenario"] == "high_emotion"

    def test_angry_refund_escalates(self):
        """愤怒 + 退款意图 → 升级人工"""
        handler = get_human_handler()
        r = handler.check_needs_human(
            query="退款！凭什么不退！", intent="return_refund", emotion="angry"
        )
        assert r["needs_human"] is True
        assert r["priority"] == "high"

    def test_angry_product_consult_not_forced(self):
        """愤怒但非高敏意图（商品咨询）→ 不因情绪强制升级"""
        handler = get_human_handler()
        r = handler.check_needs_human(
            query="这手机太坑了",
            intent="product_consult",
            emotion="angry",
            confidence=0.9,
        )
        assert r["needs_human"] is False

    def test_calm_normal(self):
        """平静 + 普通问题 + 高置信度 → 不升级"""
        handler = get_human_handler()
        r = handler.check_needs_human(
            query="怎么退货？",
            intent="return_refund",
            emotion="calm",
            confidence=0.9,
        )
        assert r["needs_human"] is False

    def test_high_emotion_template_exists(self):
        """高情绪安抚话术模板应存在"""
        handler = get_human_handler()
        template = handler.get_human_response_template("high_emotion")
        assert "抱歉" in template or "安抚" in template or "优先" in template
        assert template  # 非空
