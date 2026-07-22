"""模块9 结构化日志 — structlog + 日志轮转

日志级别:
  INFO:  正常查询完成
  WARNING: 检索降级触发、幻觉检测触发
  ERROR: Milvus连接失败、LLM API超时、文档解析失败

使用:
    from src.engineering import get_logger
    logger = get_logger()
    logger.info("query_completed", query_id="xxx", intent="return_refund")
"""

import logging
import logging.handlers
import sys
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


class StructuredLogger:
    """结构化日志封装

    使用方式:
        logger = StructuredLogger("app")
        logger.info("query_completed", query_id="xxx", intent="return_refund")
        logger.warning("degradation_triggered", level=2, query="怎么退货")
        logger.error("milvus_connection_failed", host="192.168.191.128")
    """

    def __init__(self, name: str = "app"):
        self._logger = logging.getLogger(name)
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """配置日志处理器"""
        if self._logger.handlers:
            return

        self._logger.setLevel(logging.DEBUG)

        # 格式: 时间 | 级别 | 模块 | 消息 | 额外字段
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        # 应用日志（轮转，保留30天）
        app_handler = logging.handlers.TimedRotatingFileHandler(
            APP_LOG,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        app_handler.setLevel(logging.DEBUG)
        app_handler.setFormatter(formatter)
        self._logger.addHandler(app_handler)

        # 错误日志
        error_handler = logging.handlers.TimedRotatingFileHandler(
            ERROR_LOG,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self._logger.addHandler(error_handler)

    def _format_extra(self, **kwargs) -> str:
        """格式化额外字段"""
        if not kwargs:
            return ""
        parts = [f"{k}={v}" for k, v in kwargs.items()]
        return " | " + " ".join(parts)

    def info(self, event: str, **kwargs) -> None:
        """INFO 级别日志"""
        extra = self._format_extra(**kwargs)
        self._logger.info("%s%s", event, extra)

    def warning(self, event: str, **kwargs) -> None:
        """WARNING 级别日志"""
        extra = self._format_extra(**kwargs)
        self._logger.warning("%s%s", event, extra)

    def error(self, event: str, **kwargs) -> None:
        """ERROR 级别日志"""
        extra = self._format_extra(**kwargs)
        self._logger.error("%s%s", event, extra)

    def debug(self, event: str, **kwargs) -> None:
        """DEBUG 级别日志"""
        extra = self._format_extra(**kwargs)
        self._logger.debug("%s%s", event, extra)

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
        """记录查询完成（结构化）"""
        self.info(
            "query_completed",
            query_id=query_id,
            query=query[:50],
            intent=intent,
            degradation_level=degradation_level,
            retrieval_ms=f"{retrieval_ms:.0f}",
            total_ms=f"{total_ms:.0f}",
            tokens=tokens,
            cost=f"{cost:.4f}",
            cache_hit=cache_hit,
            hallucination=hallucination,
            correction_rounds=correction_rounds,
        )

    def degradation_triggered(
        self,
        query_id: str,
        query: str,
        from_level: int,
        to_level: int,
        reason: str,
    ) -> None:
        """记录降级触发"""
        self.warning(
            "degradation_triggered",
            query_id=query_id,
            query=query[:50],
            from_level=from_level,
            to_level=to_level,
            reason=reason,
        )

    def hallucination_detected(
        self,
        query_id: str,
        query: str,
        faithfulness: float,
        correction_rounds: int,
    ) -> None:
        """记录幻觉检测"""
        self.warning(
            "hallucination_detected",
            query_id=query_id,
            query=query[:50],
            faithfulness=f"{faithfulness:.2f}",
            correction_rounds=correction_rounds,
        )

    def api_error(
        self,
        service: str,
        error: str,
        query_id: str = "",
    ) -> None:
        """记录 API 错误"""
        self.error(
            "api_error",
            service=service,
            error=str(error)[:200],
            query_id=query_id,
        )


# ── 模块级单例 ──

_logger_instance: Optional[StructuredLogger] = None


def get_logger(name: str = "app") -> StructuredLogger:
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger(name)
    return _logger_instance
