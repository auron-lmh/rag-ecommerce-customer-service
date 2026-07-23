"""模块7-11: 工程化模块 — 缓存/监控/日志/错误处理/安全防护/LLM客户端

使用:
    from src.engineering import get_cache, get_monitor, get_logger, get_error_handler, get_security
    from src.engineering import get_llm_client
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
from .llm_client import LLMClient, LLMClientError, get_llm_client, reset_llm_client
from .logger import StructuredLogger, get_logger
from .monitor import QueryMonitor, QueryRecord, estimate_cost, get_monitor
from .security import SecurityManager, check_output, get_security, sanitize_input
from .singleton import reset_singleton, singleton, singleton_factory

__all__ = [
    "CacheManager",
    "MemoryCache",
    "RedisCache",
    "get_cache",
    "LLMClient",
    "LLMClientError",
    "get_llm_client",
    "reset_llm_client",
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
    "SecurityManager",
    "get_security",
    "sanitize_input",
    "check_output",
    "singleton",
    "singleton_factory",
    "reset_singleton",
]
