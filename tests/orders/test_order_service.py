"""订单/物流查询服务测试 — 工具调用（改进1）+ 模块33 用户归属隔离（修复）

mock 订单归属 seed_user_id=1（normal 演示账号）。
- 本人(user_id=1)可查自己的订单/物流
- 他人(user_id=2)查不到 → 防枚举单号越权
- admin(is_admin=True)可查任意（客服场景）
"""

from src.orders.order_service import get_order_service

# mock 订单号（与 _SAMPLE_ORDERS 键一致）
_OWN = "ORD20260701001"
_TRACK = "SF1234567890"


class TestOrderService:
    def test_query_order_found(self):
        """本人(uid=1)命中订单 → 返回真实状态"""
        service = get_order_service()
        reply, found = service.reply_for(order_id=_OWN, user_id=1)
        assert found is True
        assert "已发货" in reply
        assert "顺丰速运" in reply

    def test_query_order_not_found(self):
        """未命中订单 → found=False + 提示"""
        service = get_order_service()
        reply, found = service.reply_for(order_id="ORD9999999999", user_id=1)
        assert found is False
        assert "未查询到" in reply

    def test_query_tracking_found(self):
        """本人命中快递单号 → 返回物流轨迹"""
        service = get_order_service()
        reply, found = service.reply_for(tracking_number=_TRACK, user_id=1)
        assert found is True
        assert "顺丰速运" in reply
        assert "运输中" in reply

    def test_query_tracking_not_found(self):
        service = get_order_service()
        reply, found = service.reply_for(tracking_number="SF0000000000", user_id=1)
        assert found is False
        assert "未查询到" in reply

    def test_no_entity_returns_empty(self):
        """无单号 → 空回复，走转人工"""
        service = get_order_service()
        reply, found = service.reply_for(user_id=1)
        assert found is False
        assert reply == ""

    def test_order_id_case_insensitive(self):
        """单号大小写不敏感"""
        service = get_order_service()
        reply, found = service.reply_for(order_id=_OWN.lower(), user_id=1)
        assert found is True
        assert "已发货" in reply

    def test_order_precedes_tracking(self):
        """同时给订单号+快递单号时，优先查订单"""
        service = get_order_service()
        reply, found = service.reply_for(
            order_id=_OWN, tracking_number="YT9876543210", user_id=1
        )
        assert found is True
        assert "订单" in reply


class TestOrderUserIsolation:
    """模块33 修复: 订单/物流按用户归属隔离，防枚举单号越权"""

    def test_other_user_cannot_query_order(self):
        """他人(uid=2)查 uid=1 的订单 → 查不到（不泄漏金额/物流）"""
        service = get_order_service()
        reply, found = service.reply_for(order_id=_OWN, user_id=2)
        assert found is False
        assert "未查询到" in reply
        assert "299" not in reply  # 不泄漏订单金额

    def test_other_user_cannot_query_tracking(self):
        """他人(uid=2)查 uid=1 的快递单号 → 查不到"""
        service = get_order_service()
        reply, found = service.reply_for(tracking_number=_TRACK, user_id=2)
        assert found is False

    def test_admin_can_query_any(self):
        """admin 可查任意订单（客服代查场景）"""
        service = get_order_service()
        reply, found = service.reply_for(order_id=_OWN, user_id=None, is_admin=True)
        assert found is True

    def test_no_user_id_fails_closed(self):
        """无 user_id 且非 admin → 查不到（fail-closed，防漏配越权）"""
        service = get_order_service()
        reply, found = service.reply_for(order_id=_OWN)
        assert found is False
