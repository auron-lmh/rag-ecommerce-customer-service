"""模块7-11: 工程化模块 — 缓存/监控/日志/错误处理/安全防护

使用:
    from src.engineering import get_cache
    cache = get_cache()
    cache.set_query_result("怎么退货", results)
"""

from .cache import CacheManager, MemoryCache, RedisCache, get_cache

__all__ = [
    "CacheManager",
    "MemoryCache",
    "RedisCache",
    "get_cache",
]
