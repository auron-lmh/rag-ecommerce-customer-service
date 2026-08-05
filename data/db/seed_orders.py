"""Seed copilot 业务库（users / orders / refunds）。

对应 docs/04-数据库设计.md §4.2。
剧情: 近30天退款率环比 +30%；退款原因中 logistics_slow 占比 15% -> 35%。
幂等: 每次运行先 TRUNCATE 再灌入（数据规模：5万用户 / 30万订单 / 约3万退款）。

用法:
    python data/seed_orders.py                 # 用默认 root/123456 连本地库
    python data/seed_orders.py --user root --password 'xxx'
"""

import argparse
import bisect
import random
import sys
from datetime import datetime, timedelta

import pymysql

RNG = random.Random(42)  # 固定种子 -> 可复现
NOW = datetime.now()

# ---------------- 规模配置 ----------------
USERS = 50_000
ORDERS = 300_000
BATCH = 2_000
START = datetime(2023, 8, 4)  # 近 3 年

# 近30天判定窗口
RECENT_WINDOW = timedelta(days=30)

# ---------------- 分布配置 ----------------
# (值, 权重)。城市权重约等于订单量级（一线 > 二线 > 三线）
CITIES = [
    ("北京", 800),
    ("上海", 900),
    ("广州", 600),
    ("深圳", 700),
    ("杭州", 500),
    ("成都", 500),
    ("武汉", 400),
    ("西安", 350),
    ("南京", 400),
    ("苏州", 350),
    ("重庆", 450),
    ("长沙", 300),
    ("郑州", 300),
    ("青岛", 250),
    ("天津", 300),
    ("合肥", 250),
    ("福州", 200),
    ("厦门", 200),
    ("昆明", 200),
    ("哈尔滨", 150),
]
VIP_WEIGHTS = [(0, 60), (1, 25), (2, 12), (3, 3)]

# 退款原因：旧数据 vs 近30天（logistics_slow 15% -> 35%）
REASONS_OLD = [
    ("quality", 25),
    ("logistics_slow", 15),
    ("no_longer_want", 20),
    ("wrong_item", 15),
    ("price_change", 10),
    ("other", 15),
]
REASONS_RECENT = [
    ("quality", 22),
    ("logistics_slow", 35),
    ("no_longer_want", 15),
    ("wrong_item", 10),
    ("price_change", 8),
    ("other", 10),
]

# 退款单状态
REFUND_STATUS = [("refunded", 80), ("applying", 10), ("approved", 7), ("rejected", 3)]
# 非退款订单状态
ORDER_STATUS = [
    ("completed", 84),
    ("shipped", 7),
    ("paid", 4),
    ("pending_payment", 3),
    ("closed", 2),
]


def weighted(choices):
    total = sum(w for _, w in choices)
    r = RNG.randint(1, total)
    for val, w in choices:
        r -= w
        if r <= 0:
            return val
    return choices[-1][0]


def rand_dt(start, end):
    span = int((end - start).total_seconds())
    return start + timedelta(seconds=RNG.randint(0, max(span, 0)))


def add_months(dt, months):
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    return dt.replace(year=y, month=m, day=1)


def pick_create_time(month_weights, cum):
    """按月度业务增长加权，返回一个订单时间。"""
    m = bisect.bisect_left(cum, RNG.random() * cum[-1])
    ms = add_months(START, m)
    me = min(add_months(ms, 1) - timedelta(seconds=1), NOW)
    return rand_dt(ms, me)


def main():
    ap = argparse.ArgumentParser(description="灌入 copilot 演示数据")
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

    # 幂等：先清空
    print("[1/3] TRUNCATE ...")
    for t in ("refunds", "orders", "users"):
        cur.execute(f"TRUNCATE {t}")
    conn.commit()

    # 月度增长权重：末月约为首月 2.5 倍
    month_count = (NOW.year - START.year) * 12 + (NOW.month - START.month) + 1
    month_weights = [1 + 1.5 * m / (month_count - 1) for m in range(month_count)]
    # 最后一个自然月是部分月（如 8月只过了4天），权重按已过天数折算，避免近端假性暴涨
    last_start = add_months(START, month_count - 1)
    last_len = (add_months(START, month_count) - last_start).days
    month_weights[-1] *= max((NOW - last_start).days, 1) / last_len
    cum = []
    acc = 0.0
    for w in month_weights:
        acc += w
        cum.append(acc)

    # ---------- users ----------
    print("[2/3] 生成 users ...")
    users = []
    for i in range(1, USERS + 1):
        vip = weighted(VIP_WEIGHTS)
        users.append(
            (
                f"user{i}",
                vip,
                RNG.randint(0, 10000),
                weighted(CITIES),
                f"1{RNG.randint(100000000, 999999999)}",
                rand_dt(datetime(2019, 1, 1), NOW),
            )
        )
    for i in range(0, len(users), BATCH):
        cur.executemany(
            "INSERT INTO users (username, vip_level, score, city, phone, register_time) VALUES (%s,%s,%s,%s,%s,%s)",
            users[i : i + BATCH],
        )
    conn.commit()
    print(f"  users: {len(users)}")

    # ---------- orders + refunds ----------
    print("[3/3] 生成 orders + refunds ...")
    orders, refunds = [], []
    refund_cnt = 0
    for i in range(1, ORDERS + 1):
        create_time = pick_create_time(month_weights, cum)
        is_recent = (NOW - create_time) <= RECENT_WINDOW

        will_refund = RNG.random() < (0.13 if is_recent else 0.095)
        price = round(RNG.lognormvariate(4.2, 0.9), 2)  # 中位 ~67，均值 ~100
        no = f"ORD{i:09d}"
        uid = RNG.randint(1, USERS)
        cty = weighted(CITIES)

        if will_refund:
            status = "refunded"
            reason = weighted(REASONS_RECENT if is_recent else REASONS_OLD)
            r_amount = (
                price if RNG.random() < 0.7 else round(price * RNG.uniform(0.3, 0.9), 2)
            )
            r_status = weighted(REFUND_STATUS)
            r_time = min(create_time + timedelta(days=RNG.randint(1, 7)), NOW)
            refunds.append(
                (
                    no,
                    uid,
                    reason,
                    r_amount,
                    r_status,
                    r_time,
                    NOW if r_status in ("refunded", "approved", "rejected") else None,
                )
            )
            refund_cnt += 1
        else:
            status = weighted(ORDER_STATUS)

        # 派生时间（按下单->支付->发货->完成，不超过 NOW）
        paid = (
            None
            if status in ("pending_payment", "closed")
            else min(create_time + timedelta(hours=RNG.randint(1, 24)), NOW)
        )
        ship = None
        complete = None
        if status in ("shipped", "completed", "refunded"):
            ship = min(paid + timedelta(days=RNG.randint(1, 2)), NOW)
        if status in ("completed", "refunded"):
            complete = min(ship + timedelta(days=RNG.randint(2, 5)), NOW)

        orders.append((no, uid, price, status, cty, create_time, paid, ship, complete))

        if len(orders) >= BATCH:
            cur.executemany(
                "INSERT INTO orders (order_no, user_id, price, status, city, create_time, paid_time, ship_time, complete_time) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                orders,
            )
            if refunds:
                cur.executemany(
                    "INSERT INTO refunds (order_no, user_id, reason, amount, status, create_time, finish_time) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    refunds,
                )
            orders, refunds = [], []
            conn.commit()
            sys.stdout.write(f"\r  orders: {i}/{ORDERS}  refunds: {refund_cnt}")

    # 收尾剩余批次
    if orders:
        cur.executemany(
            "INSERT INTO orders (order_no, user_id, price, status, city, create_time, paid_time, ship_time, complete_time) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            orders,
        )
    if refunds:
        cur.executemany(
            "INSERT INTO refunds (order_no, user_id, reason, amount, status, create_time, finish_time) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            refunds,
        )
    conn.commit()
    cur.close()
    conn.close()
    print(
        f"\n完成: users={USERS} orders={ORDERS} refunds={refund_cnt}  refund_rate={refund_cnt / ORDERS:.2%}"
    )


if __name__ == "__main__":
    main()
