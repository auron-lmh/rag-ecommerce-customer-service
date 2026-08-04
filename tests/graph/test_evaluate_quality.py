"""evaluate_quality 高敏承诺门槛测试 + 转人工交接包"""

from src.graph.workflow import _build_handoff_payload, evaluate_quality


def _state(**overrides) -> dict:
    base = {
        "answer": "您的退款将在3天内到账",
        "faithfulness": 0.75,
        "degradation_level": 1,
        "loop_count": 0,
        "query": "退款多久到账",
        "intent": "return_refund",
        "emotion": "calm",
        "entities": {"order_id": "OD20260701001"},
        "memory_context": "【相关实体】- coupon: 满300减50券",
        "human_reason": "需人工核验",
        "correction_rounds": 1,
    }
    base.update(overrides)
    return base


class TestHighStakesThreshold:
    def test_high_stakes_low_faithfulness_fails(self):
        """含退款承诺 + 忠实度0.75(<0.85) → 评估不通过（转人工）"""
        r = evaluate_quality(_state(faithfulness=0.75))
        assert r["evaluation_passed"] is False

    def test_high_stakes_high_faithfulness_passes(self):
        """含退款承诺 + 忠实度0.9(≥0.85) → 通过"""
        r = evaluate_quality(_state(faithfulness=0.9))
        assert r["evaluation_passed"] is True

    def test_plain_answer_mid_faithfulness_passes(self):
        """普通回答（无高敏承诺）+ 忠实度0.75(≥0.7) → 通过"""
        r = evaluate_quality(
            _state(answer="您的订单已发货，预计明天送达", faithfulness=0.75)
        )
        assert r["evaluation_passed"] is True

    def test_plain_answer_low_faithfulness_fails(self):
        """普通回答 + 忠实度0.5(<0.7) → 不通过"""
        r = evaluate_quality(_state(answer="您的订单已发货", faithfulness=0.5))
        assert r["evaluation_passed"] is False


class TestHandoffPayload:
    def test_payload_contains_key_info(self):
        payload = _build_handoff_payload(_state())
        assert payload["user_query"] == "退款多久到账"
        assert payload["intent"] == "return_refund"
        assert payload["emotion"] == "calm"
        assert payload["entities"]["order_id"] == "OD20260701001"
        assert "满300减50券" in payload["memory_summary"]
        assert payload["unresolved_reason"] == "需人工核验"

    def test_payload_attempted_actions(self):
        payload = _build_handoff_payload(_state())
        assert "degradation_level" in payload["attempted_actions"]
        assert "correction_rounds" in payload["attempted_actions"]

    def test_payload_empty_entities_filtered(self):
        payload = _build_handoff_payload(
            _state(entities={"order_id": "", "product_name": "手机壳"})
        )
        assert payload["entities"] == {"product_name": "手机壳"}
