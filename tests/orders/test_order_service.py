"""订单/物流查询服务测试 — 工具调用（改进1）"""

from src.orders.order_service import get_order_service


class TestOrderService:
    def test_query_order_found(self):
        """命中订单 → 返回真实状态"""
        service = get_order_service()
        reply, found = service.reply_for(order_id="OD20260701001")
        assert found is True
        assert "已发货" in reply
        assert "顺丰速运" in reply

    def test_query_order_not_found(self):
        """未命中订单 → found=False + 提示"""
        service = get_order_service()
        reply, found = service.reply_for(order_id="OD9999999999")
        assert found is False
        assert "未查询到" in reply

    def test_query_tracking_found(self):
        """命中快递单号 → 返回物流轨迹"""
        service = get_order_service()
        reply, found = service.reply_for(tracking_number="SF1234567890")
        assert found is True
        assert "顺丰速运" in reply
        assert "运输中" in reply

    def test_query_tracking_not_found(self):
        service = get_order_service()
        reply, found = service.reply_for(tracking_number="SF0000000000")
        assert found is False
        assert "未查询到" in reply

    def test_no_entity_returns_empty(self):
        """无单号 → 空回复，走转人工"""
        service = get_order_service()
        reply, found = service.reply_for()
        assert found is False
        assert reply == ""

    def test_order_id_case_insensitive(self):
        """单号大小写不敏感"""
        service = get_order_service()
        reply, found = service.reply_for(order_id="od20260701001")
        assert found is True
        assert "已发货" in reply

    def test_order_precedes_tracking(self):
        """同时给订单号+快递单号时，优先查订单"""
        service = get_order_service()
        reply, found = service.reply_for(
            order_id="OD20260701001", tracking_number="YT9876543210"
        )
        assert found is True
        assert "订单 OD20260701001" in reply
