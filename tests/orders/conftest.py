"""订单服务测试 conftest — 强制走 mock 路径

宿主机 MySQL 可达会干扰确定性测试（真实库无 mock 订单号）。
这里把 _connect 打成抛异常 → query_order/query_tracking 降级到内置 mock，
让归属隔离测试可复现（与数据库实际状态无关）。
"""

import pytest

from src.orders import order_service


@pytest.fixture(autouse=True)
def _force_mock_path(monkeypatch):
    def _raise_connect(*args, **kwargs):
        raise ConnectionError("测试强制 mock 路径")

    monkeypatch.setattr(order_service.OrderService, "_connect", _raise_connect)
