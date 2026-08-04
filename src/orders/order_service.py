"""订单/物流查询服务 — RAG + 工具调用 混合架构中的"工具"侧

背景:
  订单状态、物流轨迹是**实时数据**，绝不能塞进向量库
  （否则状态过期、AI 胡说）。本模块提供可替换的订单查询"工具":
    - 生产环境: 对接真实订单库 / 物流API（快递鸟、菜鸟、物流100）
    - 演示环境: 内置 mock 数据，演示 "RAG + 工具调用 + 转人工" 混合架构

使用:
    service = get_order_service()
    reply, found = service.reply_for(order_id="OD20260701001", tracking_number="")

mock 数据（演示用，生产替换为真实数据库查询）:
  - 订单号:   OD20260701001（已发货）/ OD20260701002（待发货）/ OD20260701003（已签收）
  - 快递单号: SF1234567890（运输中）/ YT9876543210（已签收）
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class OrderInfo:
    """订单信息"""

    order_id: str
    status: str
    created_at: str = ""
    total_amount: float = 0.0
    carrier: str = ""
    tracking_number: str = ""
    estimated_delivery: str = ""


@dataclass
class TrackingInfo:
    """物流轨迹信息"""

    tracking_number: str
    carrier: str
    status: str
    events: list = field(default_factory=list)  # [(时间, 描述), ...]


# ── mock 订单数据（演示用）──

_SAMPLE_ORDERS = {
    "OD20260701001": OrderInfo(
        order_id="OD20260701001",
        status="已发货",
        created_at="2026-07-01 10:23",
        total_amount=299.0,
        carrier="顺丰速运",
        tracking_number="SF1234567890",
        estimated_delivery="2026-07-05",
    ),
    "OD20260701002": OrderInfo(
        order_id="OD20260701002",
        status="待发货",
        created_at="2026-07-03 15:41",
        total_amount=129.0,
        carrier="",
        tracking_number="",
        estimated_delivery="",
    ),
    "OD20260701003": OrderInfo(
        order_id="OD20260701003",
        status="已签收",
        created_at="2026-06-20 09:12",
        total_amount=59.9,
        carrier="圆通速递",
        tracking_number="YT9876543210",
        estimated_delivery="2026-06-24",
    ),
}

_SAMPLE_TRACKING = {
    "SF1234567890": TrackingInfo(
        tracking_number="SF1234567890",
        carrier="顺丰速运",
        status="运输中",
        events=[
            ("2026-07-04 09:15", "已发货，包裹从杭州发出"),
            ("2026-07-04 18:40", "已到达杭州转运中心"),
            ("2026-07-05 08:30", "运输中，预计今日送达"),
        ],
    ),
    "YT9876543210": TrackingInfo(
        tracking_number="YT9876543210",
        carrier="圆通速递",
        status="已签收",
        events=[
            ("2026-06-22 10:00", "已发货，包裹从上海发出"),
            ("2026-06-23 16:20", "已到达北京转运中心"),
            ("2026-06-24 11:05", "已签收，签收人: 王**"),
        ],
    ),
}


class OrderService:
    """订单/物流查询服务（工具调用）

    对外暴露:
      - query_order(order_id)      → OrderInfo | None
      - query_tracking(tracking)   → TrackingInfo | None
      - reply_for(order_id, tracking) → (格式化回答, 是否命中)
    """

    def query_order(self, order_id: str) -> Optional[OrderInfo]:
        """按订单号查询订单"""
        if not order_id:
            return None
        info = _SAMPLE_ORDERS.get(order_id.strip().upper())
        if info:
            logger.info("订单查询命中: %s", order_id)
        else:
            logger.info("订单查询未命中: %s", order_id)
        return info

    def query_tracking(self, tracking_number: str) -> Optional[TrackingInfo]:
        """按快递单号查询物流"""
        if not tracking_number:
            return None
        info = _SAMPLE_TRACKING.get(tracking_number.strip().upper())
        if info:
            logger.info("物流查询命中: %s", tracking_number)
        else:
            logger.info("物流查询未命中: %s", tracking_number)
        return info

    def reply_for(
        self, order_id: str = "", tracking_number: str = ""
    ) -> tuple[str, bool]:
        """生成客服回复

        Args:
            order_id: 订单号（有则优先查订单）
            tracking_number: 快递单号

        Returns:
            (reply, found) — found=True 表示工具命中并给出真实状态
        """
        if order_id:
            info = self.query_order(order_id)
            if info:
                return self._format_order_reply(info), True
            return (
                f"未查询到订单 {order_id} 的记录，请核对订单号，或联系人工客服查询。",
                False,
            )

        if tracking_number:
            info = self.query_tracking(tracking_number)
            if info:
                return self._format_tracking_reply(info), True
            return (
                f"未查询到快递单号 {tracking_number} 的物流记录，请核对单号，或联系人工客服。",
                False,
            )

        return "", False

    @staticmethod
    def _format_order_reply(info: OrderInfo) -> str:
        """格式化订单回答"""
        lines = [
            f"订单 {info.order_id}：{info.status}",
            f"- 下单时间: {info.created_at}",
            f"- 订单金额: ¥{info.total_amount:.2f}",
        ]
        if info.carrier and info.tracking_number:
            lines.append(f"- 承运商: {info.carrier} ({info.tracking_number})")
        if info.estimated_delivery:
            lines.append(f"- 预计送达: {info.estimated_delivery}")
        return "\n".join(lines)

    @staticmethod
    def _format_tracking_reply(info: TrackingInfo) -> str:
        """格式化物流回答"""
        lines = [f"快递单号 {info.tracking_number}：{info.status}（{info.carrier}）"]
        for ts, desc in info.events:
            lines.append(f"- {ts} {desc}")
        return "\n".join(lines)


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_order_service() -> OrderService:
    """获取订单服务单例"""
    return OrderService()
