"""circuit_breaker 并发冒烟测试 — 加锁后多线程调用不崩、状态合法（P1 修复）"""

import threading

from src.engineering.circuit_breaker import CircuitBreaker, CircuitOpenError


def test_concurrent_calls_state_consistent():
    breaker = CircuitBreaker(failure_threshold=3, reset_timeout=10.0, half_open_max=2)

    def _ok():
        return "ok"

    def _fail():
        raise RuntimeError("fail")

    unexpected = []

    def worker(i):
        try:
            breaker.call(_ok if i % 2 == 0 else _fail)
        except (CircuitOpenError, RuntimeError):
            pass
        except Exception as e:  # pragma: no cover
            unexpected.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not unexpected  # 只有预期异常，无其他崩溃
    assert breaker.state.value in ("closed", "open", "half_open")
