"""monitor PII 脱敏测试 — 审计库不存真实敏感信息（P1 修复）"""

import sqlite3

from src.engineering.monitor import QueryMonitor, QueryRecord


def test_record_redacts_pii(tmp_path):
    db = tmp_path / "test_monitor.db"
    monitor = QueryMonitor(db_path=db)
    monitor.record(QueryRecord(user_query="我的手机是13800138000，帮我查订单"))

    conn = sqlite3.connect(db)
    row = conn.execute("SELECT user_query FROM query_records").fetchone()
    conn.close()

    assert row[0] == "我的手机是[手机号]，帮我查订单"
    assert "13800138000" not in row[0]
