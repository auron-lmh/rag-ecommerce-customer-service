"""模块8 成本监控 + 可观测性 — 每次查询记录完整链路

记录字段:
  - query_id, timestamp, user_query
  - intent（哪个意图）
  - retrieval_method（哪级降级）
  - retrieval_docs_count, retrieval_time_ms
  - hallucination_detected（是否检测到幻觉）
  - self_correction_rounds（纠正了几轮）
  - prompt_tokens, completion_tokens, total_tokens
  - llm_cost（元，按API定价折算）
  - embedding_cost（元）
  - cache_hit（是/否/部分）
  - total_time_ms
  - final_answer_length

存储: SQLite
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)

# SQLite 数据库路径
DB_PATH = settings.data_dir / "monitoring.db"

# API 定价（元/1000 tokens）——成本估算用，实际以各平台官方控制台为准（价格会随促销调整）
PRICING = {
    # DeepSeek 官方 (2026-04): deepseek-chat → deepseek-v4-flash，输入1元/百万, 输出2元/百万
    "deepseek-chat": {"input": 0.001, "output": 0.002},
    "deepseek-v4-flash": {"input": 0.001, "output": 0.002},
    # Qwen-Plus (官方约 0.87/2.1 元/百万)
    "qwen-plus": {"input": 0.001, "output": 0.002},
    # 视觉模型（相对贵，估算）
    "qwen3.7-plus": {"input": 0.004, "output": 0.012},
    "qwen3.7-plus-2026-05-26": {"input": 0.004, "output": 0.012},
    # OCR 视觉模型（估算）
    "qwen-vl-ocr-2025-08-28": {"input": 0.008, "output": 0},
    "qwen-vl-ocr-1028": {"input": 0.008, "output": 0},
    # Embedding / Reranker（估算，通常 0.5~1 元/百万）
    "qwen3-vl-embedding": {"input": 0.001, "output": 0},
    "qwen2.5-vl-embedding": {"input": 0.001, "output": 0},
    "qwen3-vl-rerank": {"input": 0.001, "output": 0},
}


@dataclass
class QueryRecord:
    """单次查询记录"""

    query_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    user_query: str = ""
    intent: str = ""
    retrieval_method: str = ""  # hybrid / rewritten / web_search / fallback
    degradation_level: int = 1
    retrieval_docs_count: int = 0
    retrieval_time_ms: float = 0
    hallucination_detected: bool = False
    self_correction_rounds: int = 0
    faithfulness: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_cost: float = 0
    embedding_cost: float = 0
    cache_hit: str = "miss"  # hit / miss / partial
    total_time_ms: float = 0
    final_answer_length: int = 0
    session_id: str = ""
    model_used: str = ""


class QueryMonitor:
    """查询监控器

    使用方式:
        monitor = QueryMonitor()
        record = QueryRecord(user_query="怎么退货", intent="return_refund")
        monitor.record(record)
        stats = monitor.get_daily_stats("2026-07-22")
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        """初始化 SQLite 数据库"""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_records (
                    query_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_query TEXT NOT NULL,
                    intent TEXT DEFAULT '',
                    retrieval_method TEXT DEFAULT '',
                    degradation_level INTEGER DEFAULT 1,
                    retrieval_docs_count INTEGER DEFAULT 0,
                    retrieval_time_ms REAL DEFAULT 0,
                    hallucination_detected BOOLEAN DEFAULT 0,
                    self_correction_rounds INTEGER DEFAULT 0,
                    faithfulness REAL DEFAULT 0,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    llm_cost REAL DEFAULT 0,
                    embedding_cost REAL DEFAULT 0,
                    cache_hit TEXT DEFAULT 'miss',
                    total_time_ms REAL DEFAULT 0,
                    final_answer_length INTEGER DEFAULT 0,
                    session_id TEXT DEFAULT '',
                    model_used TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON query_records(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_intent ON query_records(intent)
            """)
            conn.commit()

    def record(self, record: QueryRecord) -> None:
        """记录查询"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO query_records (
                    query_id, timestamp, user_query, intent, retrieval_method,
                    degradation_level, retrieval_docs_count, retrieval_time_ms,
                    hallucination_detected, self_correction_rounds, faithfulness,
                    prompt_tokens, completion_tokens, total_tokens,
                    llm_cost, embedding_cost, cache_hit,
                    total_time_ms, final_answer_length, session_id, model_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.query_id,
                    record.timestamp,
                    record.user_query,
                    record.intent,
                    record.retrieval_method,
                    record.degradation_level,
                    record.retrieval_docs_count,
                    record.retrieval_time_ms,
                    record.hallucination_detected,
                    record.self_correction_rounds,
                    record.faithfulness,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.total_tokens,
                    record.llm_cost,
                    record.embedding_cost,
                    record.cache_hit,
                    record.total_time_ms,
                    record.final_answer_length,
                    record.session_id,
                    record.model_used,
                ),
            )
            conn.commit()

        logger.debug(
            "记录查询: %s, intent=%s, tokens=%d, cost=%.4f",
            record.query_id,
            record.intent,
            record.total_tokens,
            record.llm_cost + record.embedding_cost,
        )

    def get_daily_stats(self, date: Optional[str] = None) -> dict:
        """获取每日统计

        Args:
            date: 日期字符串 (YYYY-MM-DD)，默认今天

        Returns:
            统计数据字典
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 基础统计
            row = conn.execute(
                """SELECT
                    COUNT(*) as total_queries,
                    SUM(llm_cost) as total_llm_cost,
                    SUM(embedding_cost) as total_embedding_cost,
                    SUM(llm_cost + embedding_cost) as total_cost,
                    AVG(total_time_ms) as avg_latency_ms,
                    SUM(CASE WHEN hallucination_detected = 1 THEN 1 ELSE 0 END) as hallucination_count,
                    SUM(CASE WHEN cache_hit = 'hit' THEN 1 ELSE 0 END) as cache_hits,
                    SUM(prompt_tokens) as total_prompt_tokens,
                    SUM(completion_tokens) as total_completion_tokens,
                    SUM(total_tokens) as total_tokens
                FROM query_records
                WHERE timestamp LIKE ?""",
                (f"{date}%",),
            ).fetchone()

            total = row["total_queries"] or 0
            hallucination_rate = (
                (row["hallucination_count"] or 0) / total if total > 0 else 0
            )
            cache_hit_rate = (row["cache_hits"] or 0) / total if total > 0 else 0

            # 意图分布
            intent_dist = conn.execute(
                """SELECT intent, COUNT(*) as count
                   FROM query_records
                   WHERE timestamp LIKE ?
                   GROUP BY intent
                   ORDER BY count DESC""",
                (f"{date}%",),
            ).fetchall()

            # P99 延迟
            p99_row = conn.execute(
                """SELECT total_time_ms
                   FROM query_records
                   WHERE timestamp LIKE ?
                   ORDER BY total_time_ms DESC
                   LIMIT 1 OFFSET ?""",
                (f"{date}%", max(0, int(total * 0.01) - 1)),
            ).fetchone()
            p99_latency = p99_row["total_time_ms"] if p99_row else 0

            return {
                "date": date,
                "total_queries": total,
                "total_cost": round(row["total_cost"] or 0, 4),
                "total_llm_cost": round(row["total_llm_cost"] or 0, 4),
                "total_embedding_cost": round(row["total_embedding_cost"] or 0, 4),
                "avg_latency_ms": round(row["avg_latency_ms"] or 0, 1),
                "p99_latency_ms": round(p99_latency, 1),
                "hallucination_rate": round(hallucination_rate, 4),
                "cache_hit_rate": round(cache_hit_rate, 4),
                "total_prompt_tokens": row["total_prompt_tokens"] or 0,
                "total_completion_tokens": row["total_completion_tokens"] or 0,
                "total_tokens": row["total_tokens"] or 0,
                "intent_distribution": [
                    {"intent": r["intent"], "count": r["count"]} for r in intent_dist
                ],
            }

    def get_recent_queries(self, limit: int = 20) -> list[dict]:
        """获取最近的查询记录"""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT query_id, timestamp, user_query, intent,
                          total_time_ms, llm_cost + embedding_cost as cost,
                          hallucination_detected, cache_hit
                   FROM query_records
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def check_alerts(self, date: Optional[str] = None) -> list[dict]:
        """检查告警规则"""
        stats = self.get_daily_stats(date)
        alerts = []

        # 幻觉率 > 5%
        if stats["hallucination_rate"] > 0.05:
            alerts.append(
                {
                    "type": "hallucination_rate",
                    "severity": "warning",
                    "message": f"幻觉率 {stats['hallucination_rate']:.1%} 超过 5%",
                    "value": stats["hallucination_rate"],
                    "threshold": 0.05,
                }
            )

        # P99 延迟 > 3s
        if stats["p99_latency_ms"] > 3000:
            alerts.append(
                {
                    "type": "p99_latency",
                    "severity": "warning",
                    "message": f"P99 延迟 {stats['p99_latency_ms']:.0f}ms 超过 3s",
                    "value": stats["p99_latency_ms"],
                    "threshold": 3000,
                }
            )

        # 单日成本超过 10 元
        if stats["total_cost"] > 10:
            alerts.append(
                {
                    "type": "daily_cost",
                    "severity": "warning",
                    "message": f"单日成本 {stats['total_cost']:.2f} 元超过预算",
                    "value": stats["total_cost"],
                    "threshold": 10,
                }
            )

        return alerts


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """估算 API 成本（元）"""
    pricing = PRICING.get(model, {"input": 0.001, "output": 0.002})
    input_cost = prompt_tokens / 1000 * pricing["input"]
    output_cost = completion_tokens / 1000 * pricing["output"]
    return round(input_cost + output_cost, 6)


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_monitor() -> QueryMonitor:
    return QueryMonitor()
