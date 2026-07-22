"""模块4: 意图路由系统 — LLM Function Calling / 6类意图 / SQL vs RAG vs 对比

使用:
    from src.routing import get_router
    router = get_router()
    result = router.route("怎么退货？")
    print(result.target)            # RouteTarget.RAG
    print(result.rewritten_query)   # "退货流程"
"""

from .classifier import IntentClassifier, get_classifier
from .models import Intent, IntentResult, RouteResult, RouteTarget
from .router import IntentRouter, get_router

__all__ = [
    "Intent",
    "IntentResult",
    "RouteResult",
    "RouteTarget",
    "IntentClassifier",
    "get_classifier",
    "IntentRouter",
    "get_router",
]
