"""模块7-11: 工程化模块 — 缓存/监控/日志/错误处理/安全防护/LLM客户端/熔断器/PII脱敏

使用:
    from src.engineering import get_cache, get_monitor, get_logger, get_error_handler, get_security
    from src.engineering import get_llm_client, get_llm_breaker, get_pii_redactor
"""

from .cache import CacheManager, MemoryCache, RedisCache, get_cache
from .circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    get_embedding_breaker,
    get_llm_breaker,
    get_reranker_breaker,
    reset_all_breakers,
    with_circuit_breaker,
)
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
from .pii_redactor import PIIRedactor, detect_pii, get_pii_redactor, redact_text
from .security import SecurityManager, check_output, get_security, sanitize_input
from .singleton import reset_singleton, singleton, singleton_factory

__all__ = [
    # 缓存
    "CacheManager",
    "MemoryCache",
    "RedisCache",
    "get_cache",
    # LLM 客户端
    "LLMClient",
    "LLMClientError",
    "get_llm_client",
    "reset_llm_client",
    # 熔断器
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "get_llm_breaker",
    "get_embedding_breaker",
    "get_reranker_breaker",
    "reset_all_breakers",
    "with_circuit_breaker",
    # 监控
    "QueryMonitor",
    "QueryRecord",
    "estimate_cost",
    "get_monitor",
    # 日志
    "StructuredLogger",
    "get_logger",
    # 错误处理
    "ErrorHandler",
    "LLMError",
    "MilvusError",
    "handle_llm_error",
    "handle_milvus_error",
    "get_error_handler",
    "retry_on_error",
    "safe_execute",
    # 安全
    "SecurityManager",
    "get_security",
    "sanitize_input",
    "check_output",
    # PII 脱敏
    "PIIRedactor",
    "get_pii_redactor",
    "redact_text",
    "detect_pii",
    # 单例
    "singleton",
    "singleton_factory",
    "reset_singleton",
]
