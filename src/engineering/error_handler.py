"""模块11 错误处理 — 生产级异常处理

处理策略:
  LLM API: 超时→重试 / 429→等待重试 / 5xx→切换备用模型
  Milvus: 连接失败→重试→降级为纯文本检索
  Redis: 连接失败→跳过缓存（不阻塞主流程）
  通用: 所有异常不暴露给用户，记录到日志
"""

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 重试参数
MAX_RETRIES = 3
BASE_BACKOFF = 2.0


class ServiceError(Exception):
    """服务异常基类"""

    def __init__(self, message: str, service: str = "", code: str = ""):
        super().__init__(message)
        self.service = service
        self.code = code


class LLMError(ServiceError):
    """LLM API 异常"""

    pass


class MilvusError(ServiceError):
    """Milvus 异常"""

    pass


class CacheError(ServiceError):
    """缓存异常"""

    pass


def retry_on_error(
    max_retries: int = MAX_RETRIES,
    base_backoff: float = BASE_BACKOFF,
    exceptions: tuple = (Exception,),
) -> Callable:
    """重试装饰器

    使用:
        @retry_on_error(max_retries=3, exceptions=(ConnectionError,))
        def call_api():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_retries:
                        wait = base_backoff**attempt
                        logger.warning(
                            "重试 %d/%d: %s, 等待 %.1fs",
                            attempt + 1,
                            max_retries,
                            str(e)[:100],
                            wait,
                        )
                        time.sleep(wait)
                    else:
                        logger.error("重试耗尽: %s", str(e)[:200])
            raise last_error

        return wrapper

    return decorator


def safe_execute(
    func: Callable,
    fallback: Any = None,
    service: str = "",
    log_error: bool = True,
) -> Any:
    """安全执行 — 捕获异常，返回降级值

    使用:
        result = safe_execute(lambda: cache.get("key"), fallback=None)
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error("safe_execute 失败 [%s]: %s", service, str(e)[:200])
        return fallback


def handle_llm_error(error: Exception, query_id: str = "") -> str:
    """处理 LLM API 错误 — 返回用户友好的错误消息

    Args:
        error: 异常对象
        query_id: 查询ID

    Returns:
        用户友好的错误消息
    """
    error_str = str(error).lower()

    # 超时
    if "timeout" in error_str:
        logger.error("LLM 超时 [%s]: %s", query_id, error)
        return "抱歉，系统响应超时，请稍后重试。"

    # 429 限流
    if "429" in error_str or "rate limit" in error_str:
        logger.warning("LLM 限流 [%s]: %s", query_id, error)
        return "系统繁忙，请稍后重试。"

    # 5xx 服务端错误
    if "500" in error_str or "502" in error_str or "503" in error_str:
        logger.error("LLM 服务错误 [%s]: %s", query_id, error)
        return "服务暂时不可用，请稍后重试。"

    # 内容过滤
    if "content_filter" in error_str or "safety" in error_str:
        logger.warning("LLM 内容过滤 [%s]: %s", query_id, error)
        return "您的问题无法处理，请重新表述。"

    # API Key 无效
    if "401" in error_str or "403" in error_str or "invalid api key" in error_str:
        logger.error("LLM 认证失败 [%s]: %s", query_id, error)
        return "服务配置错误，请联系管理员。"

    # 额度耗尽
    if "quota" in error_str or "insufficient" in error_str:
        logger.error("LLM 额度耗尽 [%s]: %s", query_id, error)
        return "服务额度不足，请联系管理员。"

    # 通用错误
    logger.error("LLM 未知错误 [%s]: %s", query_id, error)
    return "系统暂时繁忙，请稍后重试。"


def handle_milvus_error(error: Exception, query_id: str = "") -> str:
    """处理 Milvus 错误

    Returns:
        错误消息
    """
    error_str = str(error).lower()

    if "connection" in error_str or "unavailable" in error_str:
        logger.error("Milvus 连接失败 [%s]: %s", query_id, error)
        return "知识库连接失败，请稍后重试。"

    if "timeout" in error_str:
        logger.error("Milvus 超时 [%s]: %s", query_id, error)
        return "知识库查询超时，请稍后重试。"

    logger.error("Milvus 错误 [%s]: %s", query_id, error)
    return "知识库暂时不可用，请稍后重试。"


def handle_embedding_error(error: Exception, query_id: str = "") -> str:
    """处理 Embedding 错误"""
    logger.error("Embedding 错误 [%s]: %s", query_id, error)
    return "文本处理失败，请稍后重试。"


class ErrorHandler:
    """统一错误处理器

    使用:
        handler = ErrorHandler()
        with handler.context("query", query_id="abc123"):
            result = risky_operation()
    """

    def __init__(self, logger_instance: Optional[Any] = None):
        self._logger = logger_instance or logging.getLogger(__name__)

    def context(self, service: str, **extra):
        """错误上下文管理器"""
        return ErrorContext(self._logger, service, **extra)

    def wrap(self, func: Callable, service: str, fallback: Any = None) -> Callable:
        """包装函数，自动处理错误"""

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self._logger.error(
                    "[%s] %s: %s", service, type(e).__name__, str(e)[:200]
                )
                return fallback

        return wrapper


class ErrorContext:
    """错误上下文管理器"""

    def __init__(self, logger: Any, service: str, **extra):
        self._logger = logger
        self._service = service
        self._extra = extra

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            extra_str = " ".join(f"{k}={v}" for k, v in self._extra.items())
            self._logger.error(
                "[%s] %s: %s %s",
                self._service,
                exc_type.__name__,
                str(exc_val)[:200],
                extra_str,
            )
            # 不抑制异常，只记录
            return False


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_error_handler() -> ErrorHandler:
    return ErrorHandler()
