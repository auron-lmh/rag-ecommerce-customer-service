"""模块 11.6 熔断器 — 防止级联故障的快速失败机制

对标: AdnanSattar/enterprise-rag-stack/deployment/circuit_breaker.py

三态状态机:
    CLOSED ──(失败达阈值)→ OPEN ──(冷却超时)→ HALF_OPEN ──(探测成功)→ CLOSED
                                 └──(探测失败)→ OPEN

为什么需要熔断器:
  - LLMClient 已有 retry + fallback，但缺少熔断保护
  - DeepSeek 挂了 → 每个请求都等 retry 耗尽 → 30s 超时 → 雪崩
  - 熔断器让系统「快速失败」：连续 N 次失败 → 直接拒绝 → N 秒后探测恢复
  - 这是 Netflix Hystrix / Resilience4j 的标准模式

使用:
    from src.engineering.circuit_breaker import get_llm_breaker, CircuitOpenError

    breaker = get_llm_breaker()

    # 方式1: 直接调用
    try:
        result = breaker.call(llm_client.chat, messages=[...])
    except CircuitOpenError:
        return "服务暂时不可用"

    # 方式2: 异步调用
    result = await breaker.call_async(llm_client.achat, messages=[...])

    # 方式3: 查看状态
    stats = breaker.stats()  # {"state": "closed", "failures": 0, ...}
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 正常：请求放行
    OPEN = "open"  # 熔断：直接拒绝（快速失败）
    HALF_OPEN = "half_open"  # 半开：探测恢复（限制请求数）


class CircuitOpenError(Exception):
    """熔断器打开时抛出的异常"""

    pass


@dataclass
class CircuitBreaker:
    """三态熔断器

    参数:
        failure_threshold: 连续失败 N 次后进入 OPEN 状态
        reset_timeout:     OPEN 状态下等待 N 秒后进入 HALF_OPEN
        half_open_max:     HALF_OPEN 状态下最多放行 N 个探测请求

    状态转换:
        CLOSED:    所有请求放行。记录成功/失败。
                  连续失败 >= failure_threshold → OPEN

        OPEN:      所有请求直接拒绝（抛 CircuitOpenError），不调用实际服务。
                  reset_timeout 秒后 → HALF_OPEN

        HALF_OPEN: 最多放行 half_open_max 个请求作为「探测」。
                  探测全部成功 → CLOSED（恢复）
                  探测失败 → OPEN（重新熔断）

    面试要点:
        - CLOSED → OPEN 的触发条件是「连续失败」而非「累计失败」
        - HALF_OPEN 限制请求数，防止恢复阶段流量冲击
        - reset_timeout 设置要大于后端恢复时间（避免过早探测）
    """

    failure_threshold: int = 3
    reset_timeout: float = 60.0
    half_open_max: int = 2

    # ── 内部状态 ──
    state: CircuitState = field(default=CircuitState.CLOSED)
    failures: int = field(default=0)
    successes: int = field(default=0)
    last_failure_time: float = field(default=0)
    half_open_calls: int = field(default=0)
    _lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False
    )  # 并发保护（检查/计数/状态转换非原子，P1 修复）

    # ═══════════════════════════════════════════════
    # 公共 API
    # ═══════════════════════════════════════════════

    def call(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """同步调用（带熔断保护）

        如果熔断器 OPEN，直接抛 CircuitOpenError，不调用 fn。
        如果熔断器 HALF_OPEN，放行但限制请求数。
        如果 fn 抛异常，记录失败并可能触发熔断。

        Raises:
            CircuitOpenError: 熔断器打开
            Exception: fn 的原始异常
        """
        with self._lock:
            if not self._allow_request():
                raise CircuitOpenError(
                    f"熔断器 {self.state.value}，"
                    f"{self._cooldown_remaining():.0f}s 后重试"
                )

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1

        try:
            result = fn(*args, **kwargs)
        except CircuitOpenError:
            raise
        except Exception:
            with self._lock:
                self._on_failure()
            raise
        with self._lock:
            self._on_success()
        return result

    async def call_async(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """异步调用（带熔断保护）

        支持 async 函数和同步函数两种 fn。
        """
        with self._lock:
            if not self._allow_request():
                raise CircuitOpenError(
                    f"熔断器 {self.state.value}，"
                    f"{self._cooldown_remaining():.0f}s 后重试"
                )

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1

        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(*args, **kwargs)
            else:
                result = fn(*args, **kwargs)
        except CircuitOpenError:
            raise
        except Exception:
            with self._lock:
                self._on_failure()
            raise
        with self._lock:
            self._on_success()
        return result

    def stats(self) -> dict:
        """获取熔断器统计信息"""
        with self._lock:
            return {
                "state": self.state.value,
                "failures": self.failures,
                "successes": self.successes,
                "half_open_calls": self.half_open_calls,
                "cooldown_remaining_s": self._cooldown_remaining(),
            }

    def reset(self) -> None:
        """手动重置熔断器到 CLOSED 状态（测试/运维用）"""
        with self._lock:
            logger.info("手动重置熔断器: %s → CLOSED", self.state.value)
            self.state = CircuitState.CLOSED
            self.failures = 0
            self.successes = 0
            self.half_open_calls = 0

    # ═══════════════════════════════════════════════
    # 内部逻辑
    # ═══════════════════════════════════════════════

    def _allow_request(self) -> bool:
        """判断是否允许请求通过"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # 检查冷却时间是否已过
            if time.time() - self.last_failure_time >= self.reset_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # 限制探测请求数量
            return self.half_open_calls < self.half_open_max

        return False

    def _on_success(self) -> None:
        """记录成功"""
        self.failures = 0  # 重置失败计数（仅连续失败才触发熔断）

        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.half_open_max:
                self._transition_to(CircuitState.CLOSED)

    def _on_failure(self) -> None:
        """记录失败"""
        self.failures += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # 探测失败 → 立即重新熔断
            self._transition_to(CircuitState.OPEN)
        elif self.failures >= self.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """状态转换"""
        old_state = self.state.value
        self.state = new_state

        if new_state == CircuitState.OPEN:
            logger.warning(
                "熔断器 OPEN（连续 %d 次失败），冷却 %.0fs",
                self.failures,
                self.reset_timeout,
            )
        elif new_state == CircuitState.HALF_OPEN:
            logger.info("熔断器 HALF_OPEN（开始探测恢复）")
            self.half_open_calls = 0
            self.successes = 0
        elif new_state == CircuitState.CLOSED:
            logger.info("熔断器 CLOSED（服务已恢复，%d 次探测成功）", self.successes)

        # 非 OPEN → OPEN 时记录时间
        if new_state == CircuitState.OPEN:
            self.last_failure_time = time.time()

    def _cooldown_remaining(self) -> float:
        """OPEN 状态剩余冷却时间（秒）"""
        if self.state != CircuitState.OPEN:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.reset_timeout - elapsed)


# ═══════════════════════════════════════════════
# 装饰器
# ═══════════════════════════════════════════════


def with_circuit_breaker(breaker: CircuitBreaker):
    """装饰器：将函数包装在熔断器中

    使用:
        llm_breaker = get_llm_breaker()

        @with_circuit_breaker(llm_breaker)
        def call_deepseek(messages):
            ...
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return breaker.call(fn, *args, **kwargs)

        @wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await breaker.call_async(fn, *args, **kwargs)

        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper

    return decorator


# ═══════════════════════════════════════════════
# 全局熔断器实例（按服务分类，不同阈值）
# ═══════════════════════════════════════════════

_llm_breaker: Optional[CircuitBreaker] = None
_embedding_breaker: Optional[CircuitBreaker] = None
_reranker_breaker: Optional[CircuitBreaker] = None


def get_llm_breaker() -> CircuitBreaker:
    """LLM API 熔断器

    阈值设计:
      failure_threshold=3:  LLM 连续 3 次失败 → 熔断
      reset_timeout=30s:    30 秒后探测恢复（LLM 恢复通常快）
      half_open_max=2:      最多 2 个探测请求
    """
    global _llm_breaker
    if _llm_breaker is None:
        _llm_breaker = CircuitBreaker(
            failure_threshold=3,
            reset_timeout=30.0,
            half_open_max=2,
        )
    return _llm_breaker


def get_embedding_breaker() -> CircuitBreaker:
    """Embedding API 熔断器

    阈值设计（比 LLM 更宽容）:
      failure_threshold=5:  Embedding 偶尔失败可接受，不急着熔断
      reset_timeout=60s:    冷却时间更长
      half_open_max=3:      更多探测请求
    """
    global _embedding_breaker
    if _embedding_breaker is None:
        _embedding_breaker = CircuitBreaker(
            failure_threshold=5,
            reset_timeout=60.0,
            half_open_max=3,
        )
    return _embedding_breaker


def get_reranker_breaker() -> CircuitBreaker:
    """Reranker API 熔断器

    阈值设计:
      failure_threshold=5:  与 Embedding 相同，Reranker 非关键路径
      reset_timeout=60s:    Reranker 不可用时检索仍可返回未排序结果
    """
    global _reranker_breaker
    if _reranker_breaker is None:
        _reranker_breaker = CircuitBreaker(
            failure_threshold=5,
            reset_timeout=60.0,
            half_open_max=3,
        )
    return _reranker_breaker


def reset_all_breakers() -> None:
    """重置所有熔断器（仅测试用）"""
    for breaker in [_llm_breaker, _embedding_breaker, _reranker_breaker]:
        if breaker is not None:
            breaker.reset()
