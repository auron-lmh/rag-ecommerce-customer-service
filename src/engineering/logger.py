"""模块9 结构化日志 — JSON 格式 + 日志轮转

日志级别:
  INFO:  正常查询完成
  WARNING: 检索降级触发、幻觉检测触发
  ERROR: Milvus连接失败、LLM API超时、文档解析失败

控制台输出: 人类可读格式（带颜色级别）
文件输出:   JSON 行格式（方便 ELK/Loki/日志聚合工具采集）

使用:
    from src.engineering import get_logger
    logger = get_logger()
    logger.info("query_completed", query_id="xxx", intent="return_refund")
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.config import settings

# 日志目录
LOG_DIR = settings.log_dir
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志文件路径
APP_LOG = LOG_DIR / "app.log"
ERROR_LOG = LOG_DIR / "error.log"
QUERY_LOG = LOG_DIR / "query.log"


# ═══════════════════════════════════════════════
# JSON 格式化器 — 文件输出用
# ═══════════════════════════════════════════════


class JsonFormatter(logging.Formatter):
    """JSON 行格式化器

    输出格式（每行一条 JSON）:
        {"timestamp": "2026-07-25T10:30:00.123Z", "level": "INFO",
         "logger": "app", "event": "query_completed",
         "query_id": "abc123", "intent": "return_refund", "latency_ms": 520}

    优势:
      - 可直接导入 ELK/Loki/Grafana
      - 支持结构化字段搜索：jq '.intent' 或 grep '"intent":"return_refund"'
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.")
            + f"{int(time.time() * 1000) % 1000:03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }

        # 合并额外字段（如果有的话）
        if hasattr(record, "extra_fields") and record.extra_fields:
            log_entry.update(record.extra_fields)

        # 异常信息
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])

        return json.dumps(log_entry, ensure_ascii=False)


class PrettyFormatter(logging.Formatter):
    """控制台格式化器 — 人类可读 + 颜色级别"""

    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]
        timestamp = datetime.now().strftime("%H:%M:%S")
        return (
            f"{timestamp} {color}{record.levelname:<7}{reset} "
            f"| {record.name} | {record.getMessage()}"
        )


# ═══════════════════════════════════════════════
# 结构化日志类
# ═══════════════════════════════════════════════


class StructuredLogger:
    """结构化日志封装

    双输出模式:
      - 控制台: 人类可读（PrettyFormatter）
      - 文件:   JSON 行格式（JsonFormatter）

    使用方式:
        logger = StructuredLogger("app")
        logger.info("query_completed", query_id="xxx", intent="return_refund")
    """

    def __init__(self, name: str = "app"):
        self._logger = logging.getLogger(name)
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """配置日志处理器（双输出：控制台=人类可读，文件=JSON）"""
        if self._logger.handlers:
            return

        self._logger.setLevel(logging.DEBUG)

        # ── 控制台: 人类可读格式 ──
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(PrettyFormatter())
        self._logger.addHandler(console_handler)

        # ── 应用日志: JSON 格式（轮转，保留30天） ──
        app_handler = logging.handlers.TimedRotatingFileHandler(
            APP_LOG, when="midnight", interval=1, backupCount=30, encoding="utf-8"
        )
        app_handler.setLevel(logging.DEBUG)
        app_handler.setFormatter(JsonFormatter())
        self._logger.addHandler(app_handler)

        # ── 错误日志: JSON 格式 ──
        error_handler = logging.handlers.TimedRotatingFileHandler(
            ERROR_LOG, when="midnight", interval=1, backupCount=30, encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JsonFormatter())
        self._logger.addHandler(error_handler)

        # ── 查询日志: JSON 格式 ──
        query_handler = logging.handlers.TimedRotatingFileHandler(
            QUERY_LOG, when="midnight", interval=1, backupCount=30, encoding="utf-8"
        )
        query_handler.setLevel(logging.INFO)
        query_handler.setFormatter(JsonFormatter())
        self._logger.addHandler(query_handler)

    # ── 内部 ──

    def _log(self, level: int, event: str, **kwargs) -> None:
        """底层日志方法 — 将 kwargs 注入 LogRecord 的 extra_fields"""
        record = self._logger.makeRecord(
            self._logger.name, level, "(unknown)", 0, event, None, None
        )
        # 将结构化的 kwargs 注入 record，供 JsonFormatter 使用
        record.extra_fields = kwargs if kwargs else {}
        self._logger.handle(record)

    # ── 公共 API ──

    def info(self, event: str, **kwargs) -> None:
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs) -> None:
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs) -> None:
        self._log(logging.ERROR, event, **kwargs)

    def debug(self, event: str, **kwargs) -> None:
        self._log(logging.DEBUG, event, **kwargs)

    # ── 预定义结构化日志方法 ──

    def query_completed(
        self,
        query_id: str,
        query: str,
        intent: str,
        degradation_level: int,
        retrieval_ms: float,
        total_ms: float,
        tokens: int,
        cost: float,
        cache_hit: str,
        hallucination: bool = False,
        correction_rounds: int = 0,
    ) -> None:
        self._log(
            logging.INFO,
            "query_completed",
            query_id=query_id,
            query=query[:50],
            intent=intent,
            degradation_level=degradation_level,
            retrieval_ms=round(retrieval_ms, 1),
            total_ms=round(total_ms, 1),
            tokens=tokens,
            cost=round(cost, 4),
            cache_hit=cache_hit,
            hallucination=hallucination,
            correction_rounds=correction_rounds,
        )

    def degradation_triggered(
        self, query_id: str, query: str, from_level: int, to_level: int, reason: str
    ) -> None:
        self._log(
            logging.WARNING,
            "degradation_triggered",
            query_id=query_id,
            query=query[:50],
            from_level=from_level,
            to_level=to_level,
            reason=reason,
        )

    def hallucination_detected(
        self, query_id: str, query: str, faithfulness: float, correction_rounds: int
    ) -> None:
        self._log(
            logging.WARNING,
            "hallucination_detected",
            query_id=query_id,
            query=query[:50],
            faithfulness=round(faithfulness, 2),
            correction_rounds=correction_rounds,
        )

    def api_error(self, service: str, error: str, query_id: str = "") -> None:
        self._log(
            logging.ERROR,
            "api_error",
            service=service,
            error=str(error)[:200],
            query_id=query_id,
        )

    def circuit_breaker_event(
        self, event: str, state: str, failures: int, service: str = "llm"
    ) -> None:
        """熔断器状态变更日志"""
        level = logging.WARNING if state == "open" else logging.INFO
        self._log(
            level,
            f"circuit_breaker_{event}",
            service=service,
            state=state,
            consecutive_failures=failures,
        )


def setup_root_logging() -> None:
    """配置 root logger，让全项目模块的 logging.getLogger(__name__) 日志落到结构化 handler。

    业务模块用裸 logging.getLogger(__name__)，此前 root 无 handler 导致日志丢失
    （仅 WARNING+ 打到 stderr，无文件输出）。app 启动（lifespan）时调用一次，幂等。
    """
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(PrettyFormatter())
    root.addHandler(console)

    app_handler = logging.handlers.TimedRotatingFileHandler(
        APP_LOG, when="midnight", interval=1, backupCount=30, encoding="utf-8"
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(JsonFormatter())
    root.addHandler(app_handler)

    error_handler = logging.handlers.TimedRotatingFileHandler(
        ERROR_LOG, when="midnight", interval=1, backupCount=30, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JsonFormatter())
    root.addHandler(error_handler)


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_logger() -> StructuredLogger:
    return StructuredLogger("rag-system")
