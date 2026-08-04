"""模块7 缓存系统 — 三层缓存策略

三层缓存:
  第1层: Query缓存（完全相同的query → 直接返回缓存结果）
  第2层: Embedding缓存（文档chunk的embedding → 预热到缓存）
  第3层: LLM响应缓存（语义相似的问题 → 返回相似回答）

支持两种后端:
  - MemoryCache: 内存缓存（开发/测试）
  - RedisCache: Redis 缓存（生产）
"""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """缓存后端抽象基类"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除缓存"""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查是否存在"""

    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""

    @abstractmethod
    def clear_by_prefix(self, prefix: str) -> int:
        """按 key 前缀删除缓存（返回删除条数）

        用于知识更新后定向失效（如清空 query 层缓存），避免全量清空。
        """

    @abstractmethod
    def stats(self) -> dict:
        """缓存统计"""


class MemoryCache(CacheBackend):
    """内存缓存 — 开发/测试用（线程安全）

    使用方式:
        cache = MemoryCache(max_size=1000)
        cache.set("key", "value", ttl=3600)
        value = cache.get("key")
    """

    def __init__(self, max_size: int = 10000):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expire_at)
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._lock = __import__("threading").Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._store:
                value, expire_at = self._store[key]
                if time.time() < expire_at:
                    self._hits += 1
                    return value
                else:
                    del self._store[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        with self._lock:
            # LRU 淘汰
            if len(self._store) >= self._max_size:
                self._evict()
            self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None  # get() 内部已有锁

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def clear_by_prefix(self, prefix: str) -> int:
        """按 key 前缀删除缓存（返回删除条数）"""
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
            return len(keys)

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "backend": "memory",
                "size": len(self._store),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0,
            }

    def _evict(self) -> None:
        """淘汰过期和最旧的缓存（调用方需持有 self._lock）"""
        now = time.time()
        # 先淘汰过期的
        expired = [k for k, (_, exp) in self._store.items() if now >= exp]
        for k in expired:
            del self._store[k]

        # 还是超限就淘汰最旧的
        if len(self._store) >= self._max_size:
            oldest_key = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest_key]


class RedisCache(CacheBackend):
    """Redis 缓存 — 生产用

    使用方式:
        cache = RedisCache(host="192.168.191.128", port=6379)
        cache.set("key", "value", ttl=3600)
        value = cache.get("key")
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "rag:",
    ):
        self._prefix = prefix
        self._hits = 0
        self._misses = 0
        try:
            import redis

            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_timeout=5,
            )
            self._client.ping()
            logger.info("Redis 连接成功: %s:%d", host, port)
        except Exception as e:
            logger.warning("Redis 连接失败，降级为内存缓存: %s", e)
            self._client = None
            self._fallback = MemoryCache()

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        if not self._client:
            return self._fallback.get(key)
        try:
            data = self._client.get(self._key(key))
            if data:
                self._hits += 1
                return json.loads(data)
            self._misses += 1
            return None
        except Exception as e:
            logger.warning("Redis get 失败: %s", e)
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        if not self._client:
            self._fallback.set(key, value, ttl)
            return
        try:
            self._client.setex(
                self._key(key), ttl, json.dumps(value, ensure_ascii=False)
            )
        except Exception as e:
            logger.warning("Redis set 失败: %s", e)

    def delete(self, key: str) -> None:
        if not self._client:
            self._fallback.delete(key)
            return
        try:
            self._client.delete(self._key(key))
        except Exception as e:
            logger.warning("Redis delete 失败: %s", e)

    def exists(self, key: str) -> bool:
        if not self._client:
            return self._fallback.exists(key)
        try:
            return bool(self._client.exists(self._key(key)))
        except Exception:
            return False

    def clear(self) -> None:
        if not self._client:
            self._fallback.clear()
            return
        try:
            keys = self._client.keys(f"{self._prefix}*")
            if keys:
                self._client.delete(*keys)
        except Exception as e:
            logger.warning("Redis clear 失败: %s", e)

    def clear_by_prefix(self, prefix: str) -> int:
        """按 key 前缀删除缓存（返回删除条数）"""
        if not self._client:
            return self._fallback.clear_by_prefix(prefix)
        try:
            keys = self._client.keys(f"{self._prefix}{prefix}*")
            if keys:
                self._client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.warning("Redis clear_by_prefix(%s) 失败: %s", prefix, e)
            return 0

    def stats(self) -> dict:
        total = self._hits + self._misses
        base = {
            "backend": "redis" if self._client else "memory (fallback)",
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0,
        }
        if self._client:
            try:
                info = self._client.info("memory")
                base["used_memory"] = info.get("used_memory_human", "N/A")
                keys = self._client.keys(f"{self._prefix}*")
                base["size"] = len(keys)
            except Exception:
                pass
        return base


# ═══════════════════════════════════════
# 缓存管理器 — 统一接口
# ═══════════════════════════════════════


class CacheManager:
    """缓存管理器 — 三层缓存统一管理

    使用方式:
        cache = CacheManager()  # 自动选择后端
        cache.set_query_result("怎么退货", results)
        cached = cache.get_query_result("怎么退货")
    """

    def __init__(self, backend: Optional[CacheBackend] = None):
        self._backend = backend or self._create_backend()

    def _create_backend(self) -> CacheBackend:
        """根据配置创建缓存后端"""
        from src.config import settings

        if settings.redis_host:
            return RedisCache(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
            )
        return MemoryCache()

    # ── 第1层: Query 缓存 ──

    def get_query_result(self, query: str) -> Optional[dict]:
        """获取查询缓存"""
        key = self._query_key(query)
        return self._backend.get(key)

    def set_query_result(self, query: str, result: dict, ttl: int = 3600) -> None:
        """设置查询缓存"""
        key = self._query_key(query)
        self._backend.set(key, result, ttl)

    def _query_key(self, query: str) -> str:
        """生成查询缓存 key"""
        return f"query:{hashlib.md5(query.encode()).hexdigest()}"

    # ── 第2层: Embedding 缓存 ──

    def get_embedding(self, text: str) -> Optional[list[float]]:
        """获取 embedding 缓存"""
        key = self._embedding_key(text)
        return self._backend.get(key)

    def set_embedding(self, text: str, vector: list[float], ttl: int = 86400) -> None:
        """设置 embedding 缓存（默认24小时）"""
        key = self._embedding_key(text)
        self._backend.set(key, vector, ttl)

    def _embedding_key(self, text: str) -> str:
        """生成 embedding 缓存 key"""
        return f"emb:{hashlib.md5(text.encode()).hexdigest()}"

    # ── 第3层: LLM 响应缓存 ──

    def get_llm_response(self, prompt: str) -> Optional[str]:
        """获取 LLM 响应缓存"""
        key = self._llm_key(prompt)
        return self._backend.get(key)

    def set_llm_response(self, prompt: str, response: str, ttl: int = 3600) -> None:
        """设置 LLM 响应缓存"""
        key = self._llm_key(prompt)
        self._backend.set(key, response, ttl)

    def _llm_key(self, prompt: str) -> str:
        """生成 LLM 响应缓存 key"""
        return f"llm:{hashlib.md5(prompt.encode()).hexdigest()}"

    def clear_query_cache(self) -> int:
        """定向失效检索缓存（第1层）——知识更新后调用

        核心: 缓存失效必须绑定源数据变更事件（行业实践）。
        新政策/文档入库成功后调用，清空所有 query 缓存，
        避免缓存 TTL 内用户仍拿到旧政策答案。
        只清 query 层，保留 embedding / LLM 缓存（LLM 缓存 key 含 context，
        文档变化后 prompt 变化 → 天然失效，无需清理）。
        """
        return self._backend.clear_by_prefix("query:")

    # ── 统计 ──

    def stats(self) -> dict:
        """缓存统计"""
        return self._backend.stats()

    def clear(self) -> None:
        """清空所有缓存"""
        self._backend.clear()


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_cache() -> CacheManager:
    return CacheManager()
