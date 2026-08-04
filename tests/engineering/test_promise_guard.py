"""高敏承诺护栏测试 — 价格/退款/政策承诺需更高忠实度"""

from src.engineering.promise_guard import (
    HIGH_STAKE_FAITHFULNESS,
    detect_high_stakes,
    needs_human_review,
)


class TestDetectHighStakes:
    def test_price_detected(self):
        assert "价格" in detect_high_stakes("这款手机售价2999元")

    def test_refund_detected(self):
        assert "退款赔偿" in detect_high_stakes("您的退款将在3天内到账")

    def test_policy_promise_detected(self):
        assert "政策承诺" in detect_high_stakes("支持7天无理由退货")

    def test_warranty_detected(self):
        assert "政策承诺" in detect_high_stakes("本商品保修两年")

    def test_plain_answer_no_hits(self):
        assert detect_high_stakes("您好，请问有什么可以帮您？") == []
        assert detect_high_stakes("您的订单已发货") == []

    def test_empty(self):
        assert detect_high_stakes("") == []
        assert detect_high_stakes(None) == []


class TestNeedsHumanReview:
    def test_high_stakes_low_faithfulness_needs_review(self):
        need, cats = needs_human_review("您的退款将在3天内到账", 0.75)
        assert need is True
        assert cats

    def test_high_stakes_high_faithfulness_ok(self):
        need, cats = needs_human_review("您的退款将在3天内到账", 0.9)
        assert need is False
        assert cats  # 仍标记为高敏，但忠实度达标

    def test_plain_answer_never_review(self):
        need, cats = needs_human_review("您的订单已发货", 0.1)
        assert need is False
        assert cats == []

    def test_threshold_constant(self):
        assert HIGH_STAKE_FAITHFULNESS == 0.85
