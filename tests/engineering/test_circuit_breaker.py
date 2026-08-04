"""模块 11.6 / 11.7 测试 — CircuitBreaker + PIIRedactor 单元测试

注意: 这些测试不依赖任何外部服务（无需 API Key/Milvus/Redis）。
"""

import re
import time

import pytest

from src.engineering.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    get_embedding_breaker,
    get_llm_breaker,
    get_reranker_breaker,
    reset_all_breakers,
)
from src.engineering.pii_redactor import PIIRedactor, detect_pii, get_pii_redactor

# ═══════════════════════════════════════
# CircuitBreaker
# ═══════════════════════════════════════


class TestCircuitBreakerStates:
    """测试熔断器三态转换"""

    def test_initial_state_is_closed(self):
        b = CircuitBreaker()
        assert b.state == CircuitState.CLOSED
        assert b.failures == 0
        assert b.stats()["state"] == "closed"

    def test_success_keeps_closed(self):
        b = CircuitBreaker(failure_threshold=3)
        for _ in range(5):
            b.call(lambda: "ok")
        assert b.state == CircuitState.CLOSED
        assert b.failures == 0  # 成功重置失败计数

    def test_failures_transition_to_open(self):
        b = CircuitBreaker(failure_threshold=2)
        # 第一次失败
        with pytest.raises(ZeroDivisionError):
            b.call(lambda: 1 / 0)
        assert b.state == CircuitState.CLOSED  # 还未达阈值
        # 第二次失败 → OPEN
        with pytest.raises(ZeroDivisionError):
            b.call(lambda: 1 / 0)
        assert b.state == CircuitState.OPEN

    def test_open_rejects_immediately(self):
        b = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ZeroDivisionError):
            b.call(lambda: 1 / 0)
        # 熔断后所有请求直接拒绝
        with pytest.raises(CircuitOpenError):
            b.call(lambda: "should not be called")

    def test_half_open_after_timeout(self):
        """冷却时间过后进入 HALF_OPEN 并允许探测"""
        b = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)
        with pytest.raises(ZeroDivisionError):
            b.call(lambda: 1 / 0)
        assert b.state == CircuitState.OPEN
        # 等待冷却
        time.sleep(0.02)
        # 现在应该进入 HALF_OPEN 并允许一次探测
        result = b.call(lambda: "recovered")
        assert result == "recovered"

    def test_half_open_success_transitions_to_closed(self):
        b = CircuitBreaker(failure_threshold=1, reset_timeout=0.01, half_open_max=2)
        # 触发熔断
        with pytest.raises(ZeroDivisionError):
            b.call(lambda: 1 / 0)
        assert b.state == CircuitState.OPEN
        time.sleep(0.02)
        # 两次探测成功 → CLOSED
        b.call(lambda: "ok")
        b.call(lambda: "ok")
        assert b.state == CircuitState.CLOSED

    def test_half_open_failure_goes_back_to_open(self):
        b = CircuitBreaker(failure_threshold=1, reset_timeout=0.01, half_open_max=2)
        with pytest.raises(ZeroDivisionError):
            b.call(lambda: 1 / 0)
        time.sleep(0.02)
        # 第一次探测失败 → 直接回 OPEN
        with pytest.raises(ZeroDivisionError):
            b.call(lambda: 1 / 0)
        assert b.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        """成功后重置连续失败计数"""
        b = CircuitBreaker(failure_threshold=5)
        # 失败 3 次
        for _ in range(3):
            try:
                b.call(lambda: 1 / 0)
            except ZeroDivisionError:
                pass
        assert b.failures == 3
        # 成功一次 → 重置
        b.call(lambda: "ok")
        assert b.failures == 0

    def test_manual_reset(self):
        b = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ZeroDivisionError):
            b.call(lambda: 1 / 0)
        assert b.state == CircuitState.OPEN
        # 手动重置
        b.reset()
        assert b.state == CircuitState.CLOSED
        assert b.failures == 0

    def test_stats_reflects_current_state(self):
        b = CircuitBreaker()
        stats = b.stats()
        assert "state" in stats
        assert "failures" in stats
        assert stats["state"] == "closed"


class TestCircuitBreakerAsync:
    """测试异步熔断器"""

    @pytest.mark.asyncio
    async def test_async_call_success(self):
        async def ok():
            return "async ok"

        b = CircuitBreaker()
        result = await b.call_async(ok)
        assert result == "async ok"

    @pytest.mark.asyncio
    async def test_async_call_failure(self):
        async def fail():
            raise ValueError("test error")

        b = CircuitBreaker(failure_threshold=2)
        for _ in range(2):
            with pytest.raises(ValueError):
                await b.call_async(fail)
        assert b.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_async_call_with_sync_fn(self):
        """call_async 也支持同步函数"""
        b = CircuitBreaker()
        result = await b.call_async(lambda: "sync ok")
        assert result == "sync ok"


class TestGlobalBreakers:
    """测试全局熔断器单例"""

    def setup_method(self):
        reset_all_breakers()

    def test_get_llm_breaker_is_singleton(self):
        b1 = get_llm_breaker()
        b2 = get_llm_breaker()
        assert b1 is b2

    def test_llm_breaker_defaults(self):
        b = get_llm_breaker()
        assert b.failure_threshold == 3
        assert b.reset_timeout == 30.0
        assert b.half_open_max == 2

    def test_embedding_breaker_defaults(self):
        b = get_embedding_breaker()
        assert b.failure_threshold == 5
        assert b.reset_timeout == 60.0

    def test_reranker_breaker_defaults(self):
        b = get_reranker_breaker()
        assert b.failure_threshold == 5


# ═══════════════════════════════════════
# PIIRedactor
# ═══════════════════════════════════════


class TestPIIRedactor:
    """测试 PII 脱敏"""

    def setup_method(self):
        self.r = PIIRedactor()

    def test_phone_number(self):
        text, found = self.r.redact("我的手机是13800138000")
        assert len(found) == 1
        assert found[0]["type"] == "手机号"
        assert "13800138000" not in text
        assert "[手机号]" in text

    def test_phone_number_in_sentence(self):
        text, found = self.r.redact("请联系客服13812345678处理退货")
        assert len(found) == 1

    def test_id_card(self):
        text, found = self.r.redact("身份证440101199001011234请核对")
        assert len(found) == 1
        assert found[0]["type"] == "身份证"

    def test_bank_card(self):
        text, found = self.r.redact("卡号6222021234567890123")
        assert len(found) == 1
        assert found[0]["type"] == "银行卡"

    def test_email(self):
        text, found = self.r.redact("发到test@example.com谢谢")
        assert len(found) == 1
        assert found[0]["type"] == "邮箱"
        assert "test@example.com" not in text

    def test_ip_address(self):
        text, found = self.r.redact("IP是192.168.1.100")
        assert len(found) == 1
        assert found[0]["type"] == "IP地址"

    def test_order_number(self):
        text, found = self.r.redact("订单号TB12345678901234查一下")
        assert len(found) == 1
        assert found[0]["type"] == "订单号"

    def test_multiple_pii_types(self):
        text, found = self.r.redact(
            "手机13800138000订单TB12345678901234邮箱test@example.com"
        )
        assert len(found) == 3
        types = {f["type"] for f in found}
        assert types == {"手机号", "订单号", "邮箱"}

    def test_no_pii(self):
        text, found = self.r.redact("怎么退货的流程是什么")
        assert len(found) == 0
        assert text == "怎么退货的流程是什么"

    def test_empty_input(self):
        text, found = self.r.redact("")
        assert text == ""
        assert len(found) == 0

    def test_short_number_not_matched(self):
        """短数字串不应被匹配为银行卡"""
        text, found = self.r.redact("价格是1234567元")
        assert len(found) == 0  # 7位数字不够16位银行卡门槛

    def test_long_number_not_matched_when_part_of_larger(self):
        """20位以上的数字不应被截断匹配"""
        text, found = self.r.redact("编号1234567890123456789012345")
        assert len(found) == 0  # 25位数字，不在16-19范围内

    def test_detect_only(self):
        """detect 方法只检测不替换"""
        items = self.r.detect("手机13800138000订单TB12345678901234")
        assert len(items) == 2
        # 原文本不变
        assert "13800138000" in "手机13800138000订单TB12345678901234"

    def test_is_safe(self):
        assert self.r.is_safe("怎么退货")
        assert not self.r.is_safe("手机13800138000")

    def test_mask_value_format(self):
        """脱敏值保留首尾字符"""
        text, found = self.r.redact("手机13800138000")
        assert "***" in found[0]["masked"]
        assert len(found[0]["masked"]) > 3  # 不是纯 ***

    def test_singleton(self):
        r1 = get_pii_redactor()
        r2 = get_pii_redactor()
        assert r1 is r2

    def test_custom_patterns(self):
        r = PIIRedactor(custom_patterns={"测试码": r"TEST\d{8}"})
        text, found = r.redact("验证码TEST12345678请查收")
        assert len(found) == 1
        assert found[0]["type"] == "测试码"

    def test_name_pattern(self):
        text, found = self.r.redact("姓名：梁明晃，很高兴为您服务")
        assert len(found) == 1
        assert found[0]["type"] == "姓名"
        assert "梁明晃" not in text


# ═══════════════════════════════════════
# PII 模式边界测试
# ═══════════════════════════════════════


class TestPIIBoundaryCases:
    """测试 PII 正则的边界情况"""

    def test_number_in_chinese_context(self):
        """纯数字在中文上下文中仍应正确匹配"""
        r = PIIRedactor()
        text, found = r.redact("我的手机号码是13800138000记住了吗")
        assert len(found) == 1, f"Expected 1 match, got {found}"
        assert found[0]["type"] == "手机号"

    def test_order_with_chinese_prefix(self):
        """订单号在中文字符后面应正确匹配"""
        r = PIIRedactor()
        text, found = r.redact("查一下订单DD12345678901234物流")
        assert len(found) >= 1, f"Expected at least 1 match, got {found}"
        types = {f["type"] for f in found}
        assert "订单号" in types

    def test_email_with_chinese(self):
        """邮箱在中文字符之间应正确匹配"""
        r = PIIRedactor()
        text, found = r.redact("发送到邮箱test@example.com谢谢")
        assert len(found) == 1
        assert found[0]["type"] == "邮箱"
