"""工具路由判定测试 — 订单/快递单号 → SQL 工具节点（改进1）"""

from src.routing.router import _has_tool_entity


class TestHasToolEntity:
    def test_with_order_id(self):
        assert _has_tool_entity({"order_id": "OD20260701001"}) is True

    def test_with_tracking_number(self):
        assert _has_tool_entity({"tracking_number": "SF1234567890"}) is True

    def test_without_entity(self):
        assert _has_tool_entity({}) is False

    def test_product_name_only(self):
        """仅有商品名 → 不触发工具路由（走 RAG 检索）"""
        assert _has_tool_entity({"product_name": "手机壳"}) is False

    def test_empty_string_entity(self):
        assert _has_tool_entity({"order_id": ""}) is False
        assert _has_tool_entity({"tracking_number": ""}) is False
