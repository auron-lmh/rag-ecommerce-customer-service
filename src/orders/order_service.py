"""订单/物流查询服务 — RAG + 工具调用 混合架构中的"工具"侧

数据源（2026-08 升级为真实 MySQL）:
  - 主: 第二项目 copilot MySQL（orders + tracking 表，30万订单真实数据）
  - 备: 内置 mock（MySQL 不可达时降级，演示不中断）

背景:
  订单状态、物流轨迹是**实时数据**，绝不能塞进向量库
  （否则状态过期、AI 胡说）。本模块提供可替换的订单查询"工具":
    - 生产环境: 对接真实订单库 / 物流API（快递鸟、菜鸟、物流100）
    - 当前实现: 查 copilot MySQL（orders 订单状态 + tracking 物流轨迹）
    - MySQL 不可达: 降级内置 mock（ORD2026xxxxx / SFxxx）

使用:
    service = get_order_service()
    reply, found = service.reply_for(order_id="ORD000000001", tracking_number="")

mock 数据（仅兜底，生产/真实库不依赖）:
  - 订单号: ORD20260701001/002/003
  - 快递单号: SF1234567890 / YT9876543210
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

import pymysql

from src.config import settings

logger = logging.getLogger(__name__)

# copilot orders.status 枚举 → 中文
_ORDER_STATUS_CN = {
    "pending_payment": "待付款",
    "paid": "待发货",
    "shipped": "已发货",
    "completed": "已签收",
    "refunded": "已退款",
    "closed": "已关闭",
}
# tracking.status → 中文
_TRACK_STATUS_CN = {"shipped": "运输中", "delivered": "已签收"}


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


# ── mock 订单数据（仅 MySQL 不可达时兜底） ──

_SAMPLE_ORDERS = {
    "ORD20260701001": OrderInfo(
        order_id="ORD20260701001",
        status="已发货",
        created_at="2026-07-01 10:23",
        total_amount=299.0,
        carrier="顺丰速运",
        tracking_number="SF1234567890",
        estimated_delivery="2026-07-05",
    ),
    "ORD20260701002": OrderInfo(
        order_id="ORD20260701002",
        status="待发货",
        created_at="2026-07-03 15:41",
        total_amount=129.0,
    ),
    "ORD20260701003": OrderInfo(
        order_id="ORD20260701003",
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
        """按订单号查询订单。MySQL 优先，不可达降级 mock。"""
        if not order_id:
            return None
        oid = order_id.strip().upper()
        info, db_ok = self._query_order_db(oid)
        if info is not None:
            return info
        if not db_ok:  # 库不可达 → mock 兜底，演示不中断
            logger.info("MySQL 不可达，订单查询降级 mock")
            return _SAMPLE_ORDERS.get(oid)
        return None

    def query_tracking(self, tracking_number: str) -> Optional[TrackingInfo]:
        """按快递单号查询物流。MySQL 优先，不可达降级 mock。"""
        if not tracking_number:
            return None
        tno = tracking_number.strip().upper()
        info, db_ok = self._query_tracking_db(tno)
        if info is not None:
            return info
        if not db_ok:
            logger.info("MySQL 不可达，物流查询降级 mock")
            return _SAMPLE_TRACKING.get(tno)
        return None

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

    # ── MySQL 查询（copilot 库） ──

    def _connect(self) -> pymysql.Connection:
        return pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            connect_timeout=3,
            read_timeout=3,
        )

    def _query_order_db(self, order_no: str) -> tuple[Optional[OrderInfo], bool]:
        """查 orders(+tracking)。返回 (OrderInfo|None, db_ok)。"""
        try:
            conn = self._connect()
        except Exception as e:
            logger.warning("订单 MySQL 连接失败: %s", str(e)[:100])
            return None, False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT order_no, status, price, create_time, ship_time, complete_time
                       FROM orders WHERE order_no=%s LIMIT 1""",
                    (order_no,),
                )
                row = cur.fetchone()
                if not row:
                    return None, True
                order_no, status, price, create_time, ship_time, complete_time = row

                carrier, tracking_no = "", ""
                cur.execute(
                    """SELECT carrier, tracking_number FROM tracking
                       WHERE order_no=%s LIMIT 1""",
                    (order_no,),
                )
                tr = cur.fetchone()
                if tr:
                    carrier, tracking_no = tr

                est = ""
                if status == "completed" and complete_time:
                    est = complete_time.date().isoformat()
                elif status == "shipped" and ship_time:
                    est = (ship_time + timedelta(days=3)).date().isoformat()

                return (
                    OrderInfo(
                        order_id=order_no,
                        status=_ORDER_STATUS_CN.get(status, status),
                        created_at=str(create_time),
                        total_amount=float(price or 0),
                        carrier=carrier,
                        tracking_number=tracking_no,
                        estimated_delivery=est,
                    ),
                    True,
                )
        except Exception as e:
            logger.warning("订单 MySQL 查询异常: %s", str(e)[:100])
            return None, False
        finally:
            conn.close()

    def _query_tracking_db(
        self, tracking_number: str
    ) -> tuple[Optional[TrackingInfo], bool]:
        """查 tracking 表。返回 (TrackingInfo|None, db_ok)。"""
        try:
            conn = self._connect()
        except Exception as e:
            logger.warning("物流 MySQL 连接失败: %s", str(e)[:100])
            return None, False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT carrier, tracking_number, status, events_json
                       FROM tracking WHERE tracking_number=%s LIMIT 1""",
                    (tracking_number,),
                )
                row = cur.fetchone()
                if not row:
                    return None, True
                carrier, tno, status, events_json = row
                events = []
                try:
                    data = json.loads(events_json or "[]")
                    for e in data:  # 兼容 {"ts","desc"} 对象 或 [ts, desc] 数组两种格式
                        if isinstance(e, dict):
                            events.append(
                                (str(e.get("ts", "")), str(e.get("desc", "")))
                            )
                        elif isinstance(e, (list, tuple)) and len(e) >= 2:
                            events.append((str(e[0]), str(e[1])))
                except (json.JSONDecodeError, TypeError):
                    events = []
                return (
                    TrackingInfo(
                        tracking_number=tno,
                        carrier=carrier,
                        status=_TRACK_STATUS_CN.get(status, status),
                        events=events,
                    ),
                    True,
                )
        except Exception as e:
            logger.warning("物流 MySQL 查询异常: %s", str(e)[:100])
            return None, False
        finally:
            conn.close()

    # ── 格式化 ──

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
