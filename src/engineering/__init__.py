"""模块7-11: 工程化模块 — 缓存/监控/日志/错误处理/安全防护

使用:
    from src.engineering import get_cache, get_monitor, get_logger, get_error_handler
    cache = get_cache()
    monitor = get_monitor()
    logger = get_logger()
    handler = get_error_handler()
"""

from .cache import CacheManager, MemoryCache, RedisCache, get_cache
from .error_handler import (
    ErrorHandler,
    LLMError,
    MilvusError,
    get_error_handler,
    handle_llm_error,
    handle_milvus_error,
    retry_on_error,
    safe_execute,
)
from .logger import StructuredLogger, get_logger
from .monitor import QueryMonitor, QueryRecord, estimate_cost, get_monitor

__all__ = [
    "CacheManager",
    "MemoryCache",
    "RedisCache",
    "get_cache",
    "QueryMonitor",
    "QueryRecord",
    "estimate_cost",
    "get_monitor",
    "StructuredLogger",
    "get_logger",
    "ErrorHandler",
    "LLMError",
    "MilvusError",
    "handle_llm_error",
    "handle_milvus_error",
    "get_error_handler",
    "retry_on_error",
    "safe_execute",
]
