"""模块4 路由分发器 — 意图 → 处理器

使用方式:
    router = IntentRouter()
    result = router.route("怎么退货？")
    print(result.target)       # RouteTarget.RAG
    print(result.intent_result.intent)  # Intent.RETURN_REFUND
"""

import logging
from typing import Optional

from src.engineering.llm_client import get_llm_client

from .classifier import IntentClassifier, get_classifier
from .models import Intent, IntentResult, RouteResult, RouteTarget

logger = logging.getLogger(__name__)

# ── 意图 → 路由目标映射 ──

INTENT_ROUTE_MAP: dict[Intent, RouteTarget] = {
    Intent.RETURN_REFUND: RouteTarget.RAG,  # 售后问题 → 知识库检索
    Intent.PRODUCT_CONSULT: RouteTarget.RAG,  # 商品咨询 → 知识库检索
    Intent.LOGISTICS: RouteTarget.SQL,  # 物流查询 → SQL（预留）
    Intent.ORDER_QUERY: RouteTarget.SQL,  # 订单查询 → SQL（预留）
    Intent.COMPLAINT: RouteTarget.HUMAN,  # 投诉建议 → 转人工
    Intent.CHITCHAT: RouteTarget.DIRECT,  # 闲聊 → 直接回复
}

# ── 查询改写模板（RAG 路由用）──

QUERY_REWRITE_PROMPT = """你是电商客服查询改写器。将用户的口语化问题改写为适合向量检索的简洁查询。

规则:
1. 去掉语气词、客套话
2. 保留核心关键词
3. 补充隐含的电商上下文
4. 输出一句话，不超过 50 字

示例:
- "你好，请问我想退货的话应该怎么做呀" → "退货流程"
- "这个手机壳支持 iPhone 15 Pro Max 吗" → "手机壳 iPhone 15 Pro Max 兼容性"
- "我的快递怎么还没到啊" → "物流配送时间"

用户问题: {query}
改写结果:"""


class IntentRouter:
    """意图路由器 — 分类 + 路由 + 查询改写

    使用方式:
        router = IntentRouter()
        result = router.route("怎么退货？")
    """

    def __init__(self, classifier: Optional[IntentClassifier] = None):
        self.classifier = classifier or get_classifier()

    def route(self, query: str) -> RouteResult:
        """完整路由流程: 意图分类 → 路由决策 → 查询改写（RAG 路由时）"""

        # ── 步骤1: 意图分类 ──
        intent_result = self.classifier.classify(query)
        logger.info(
            "意图分类: %s (%.2f) — %s",
            intent_result.intent.value,
            intent_result.confidence,
            intent_result.reasoning,
        )

        # ── 步骤2: 路由决策 ──
        target = INTENT_ROUTE_MAP.get(intent_result.intent, RouteTarget.RAG)

        # 低置信度时降级到 RAG（宁可多检索，不要漏）
        if intent_result.confidence < 0.4 and target == RouteTarget.SQL:
            target = RouteTarget.RAG
            logger.info("低置信度 SQL 路由，降级为 RAG")

        # ── 步骤3: 查询改写（仅 RAG 路由）──
        rewritten = query
        if target in (RouteTarget.RAG, RouteTarget.HYBRID):
            rewritten = self._rewrite_query(query)

        return RouteResult(
            intent_result=intent_result,
            target=target,
            query=query,
            rewritten_query=rewritten,
            handler=target.value,
        )

    def _rewrite_query(self, query: str) -> str:
        """查询改写 — 口语化 → 检索友好"""
        try:
            client = get_llm_client()
            rewritten = client.chat_with_fallback(
                messages=[
                    {
                        "role": "user",
                        "content": QUERY_REWRITE_PROMPT.format(query=query),
                    }
                ],
                fallback_value=query,
                temperature=0.1,
                max_tokens=100,
                timeout=10,
            )
            # 防止 LLM 返回多余内容
            if len(rewritten) > 100:
                rewritten = rewritten[:100]
            logger.debug("查询改写: %s → %s", query, rewritten)
            return rewritten
        except Exception as e:
            logger.warning("查询改写失败，使用原始 query: %s", e)
            return query


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_router() -> IntentRouter:
    return IntentRouter()
