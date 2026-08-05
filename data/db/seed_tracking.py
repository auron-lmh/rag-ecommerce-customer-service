"""生成物流轨迹种子数据 — 给 orders 中 shipped/completed 订单补承运商/快递单号/轨迹

背景: 第一项目（电商客服 RAG）的"订单/物流查询"工具需要真实物流数据。
copilot 库 orders 表只有状态/时间，没有 carrier/快递单号/轨迹 —— 本脚本补齐。

幂等: 每次运行 TRUNCATE tracking 后重新生成。

运行:
    python data/seed_tracking.py                     # 用默认 root/123456 连本地库
    python data/seed_tracking.py --host mysql        # docker 网络内
"""

import argparse
import json
import random
from datetime import datetime, timedelta

import pymysql

RNG = random.Random(20260805)

CARRIERS = [
    ("顺丰速运", "SF", 0.22),
    ("圆通速递", "YT", 0.24),
    ("中通快递", "ZT", 0.24),
    ("韵达快递", "YD", 0.16),
    ("京东物流", "JD", 0.14),
]
BATCH = 5000


def pick_carrier():
    r = RNG.random()
    acc = 0
    for name, prefix, w in CARRIERS:
        acc += w
        if r <= acc:
            return name, prefix
    return CARRIERS[0][0], CARRIERS[0][1]


def build_events(order_no, status, city, ship_time, complete_time):
    """构造物流轨迹事件时间线（对象格式 [{ts, desc}, ...]）"""
    events = []
    t = ship_time
    events.append(
        {
            "ts": t.isoformat(sep=" ", timespec="minutes"),
            "desc": f"已发货，包裹从{city}发出",
        }
    )
    t2 = min(
        t + timedelta(days=1), complete_time or (datetime.now() - timedelta(hours=6))
    )
    events.append(
        {
            "ts": t2.isoformat(sep=" ", timespec="minutes"),
            "desc": f"已到达{city}转运中心",
        }
    )
    if status == "completed" and complete_time:
        t3 = complete_time - timedelta(hours=5)
        events.append(
            {
                "ts": t3.isoformat(sep=" ", timespec="minutes"),
                "desc": "派送中，快递员正在派送",
            }
        )
        events.append(
            {
                "ts": complete_time.isoformat(sep=" ", timespec="minutes"),
                "desc": "已签收，签收人: 王**",
            }
        )
    else:
        t3 = min(t2 + timedelta(hours=8), datetime.now() - timedelta(hours=2))
        events.append(
            {
                "ts": t3.isoformat(sep=" ", timespec="minutes"),
                "desc": "运输中，预计今日送达",
            }
        )
    return events


def main():
    ap = argparse.ArgumentParser(description="生成物流轨迹种子数据")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", default="123456")
    ap.add_argument("--database", default="copilot")
    args = ap.parse_args()

    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
    )
    cur = conn.cursor()

    print("[1/3] TRUNCATE tracking ...")
    cur.execute("TRUNCATE tracking")
    conn.commit()

    print("[2/3] 读取 shipped/completed 订单 ...")
    cur.execute("""
        SELECT order_no, status, city, ship_time, complete_time
        FROM orders WHERE status IN ('shipped','completed')
    """)
    rows = cur.fetchall()
    print(f"  待生成轨迹: {len(rows)} 单")

    print("[3/3] 生成 tracking ...")
    buf = []
    counter = RNG.randrange(10_0000, 90_0000)  # 单号序号基座
    for i, (order_no, status, city, ship_time, complete_time) in enumerate(rows):
        carrier, prefix = pick_carrier()
        counter += 1
        tracking_no = f"{prefix}{counter:012d}"
        events = build_events(order_no, status, city, ship_time, complete_time)
        t_status = "delivered" if status == "completed" else "shipped"
        buf.append(
            (
                order_no,
                carrier,
                tracking_no,
                t_status,
                json.dumps(events, ensure_ascii=False),
            )
        )
        if len(buf) >= BATCH:
            cur.executemany(
                "INSERT INTO tracking (order_no, carrier, tracking_number, status, events_json) VALUES (%s,%s,%s,%s,%s)",
                buf,
            )
            conn.commit()
            buf.clear()
            print(f"  {i+1}/{len(rows)}")
    if buf:
        cur.executemany(
            "INSERT INTO tracking (order_no, carrier, tracking_number, status, events_json) VALUES (%s,%s,%s,%s,%s)",
            buf,
        )
        conn.commit()
    cur.close()
    conn.close()

    cur2 = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
    ).cursor()
    cur2.execute("SELECT COUNT(*) FROM tracking")
    n = cur2.fetchone()[0]
    print(f"完成: tracking {n} 条")
    # 输出几条示例供演示用
    cur2.execute(
        "SELECT order_no, carrier, tracking_number, status FROM tracking LIMIT 5"
    )
    print("示例单号:")
    for r in cur2.fetchall():
        print("  ", r)


if __name__ == "__main__":
    main()
