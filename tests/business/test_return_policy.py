"""退货结构化政策测试 — 子场景检测 + 结构化回答"""

from src.business.return_policy import get_return_policy


class TestDetectSubScenario:
    def test_freight(self):
        hits = get_return_policy().detect_sub_scenario("退货运费谁出")
        assert "freight" in hits

    def test_quality(self):
        hits = get_return_policy().detect_sub_scenario("质量问题能换货吗")
        assert "quality" in hits

    def test_window(self):
        hits = get_return_policy().detect_sub_scenario("多久内能退货")
        assert "window" in hits

    def test_refund_time(self):
        hits = get_return_policy().detect_sub_scenario("退款几天到账")
        assert "refund_time" in hits

    def test_process(self):
        hits = get_return_policy().detect_sub_scenario("怎么申请退货")
        assert "process" in hits

    def test_unrelated_no_hit(self):
        assert get_return_policy().detect_sub_scenario("我的订单到哪了") == []
        assert get_return_policy().detect_sub_scenario("") == []


class TestAnswer:
    def test_freight_answer_structured(self):
        reply, found = get_return_policy().answer("退货运费谁出")
        assert found is True
        assert "运费" in reply
        assert "买家承担" in reply or "商家承担" in reply

    def test_window_answer_contains_seven_day(self):
        reply, found = get_return_policy().answer("多久内能退货")
        assert found is True
        assert "7天无理由" in reply

    def test_quality_answer_contains_evidence(self):
        reply, found = get_return_policy().answer("质量问题能换货吗")
        assert found is True
        assert "拍照" in reply

    def test_unrelated_returns_empty(self):
        reply, found = get_return_policy().answer("我的订单到哪了")
        assert found is False
        assert reply == ""

    def test_multi_scenario_combined(self):
        """质量问题+运费 组合问题 → 两类政策都给出"""
        reply, found = get_return_policy().answer("质量问题退货运费谁出")
        assert found is True
        assert "质量问题" in reply
        assert "运费" in reply


class TestRouteDecision:
    def _route(self, intent, query):
        from src.graph.workflow import route_decision

        return route_decision(
            {
                "target": "rag",
                "needs_human": False,
                "intent": intent,
                "query": query,
            }
        )

    def test_return_freight_routes_to_policy(self):
        assert self._route("return_refund", "退货运费谁出") == "policy"

    def test_return_process_routes_to_policy(self):
        assert self._route("return_refund", "怎么退货") == "policy"

    def test_return_unrelated_keeps_rag(self):
        assert self._route("return_refund", "我买的鞋什么时候发货") == "rag"

    def test_non_return_intent_keeps_rag(self):
        assert self._route("product_consult", "这手机怎么样") == "rag"
