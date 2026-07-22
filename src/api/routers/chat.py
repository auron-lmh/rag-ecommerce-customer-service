"""模块12 对话路由 — POST /api/chat

意图路由 + 多级降级检索 + 幻觉检测自纠正生成
"""

import logging

from fastapi import APIRouter, Depends

from src.api.deps import get_retriever
from src.api.models import ChatRequest, ChatResponse, SearchResultItem
from src.embedding.degradation import get_degradation_strategy
from src.embedding.retriever import Retriever
from src.generation import get_corrector
from src.routing import RouteTarget, get_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["对话"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    retriever: Retriever = Depends(get_retriever),
) -> ChatResponse:
    """智能客服对话 — 意图路由 + 多级降级检索 + 幻觉检测自纠正

    流程:
      1. 意图分类 (LLM Function Calling)
      2. 路由决策 (RAG / SQL / 直接回复 / 转人工)
      3. 查询改写 (RAG 路由时)
      4. 多级降级检索 (Level 1→2→3→4)
      5. 幻觉检测 + 自纠正闭环 (最多2轮)
    """
    router_instance = get_router()
    route_result = router_instance.route(req.query)

    response = ChatResponse(
        query=req.query,
        intent=route_result.intent_result.intent.value,
        confidence=route_result.intent_result.confidence,
        target=route_result.target.value,
        rewritten_query=route_result.rewritten_query,
        reasoning=route_result.intent_result.reasoning,
        results=[],
        reply="",
    )

    # ── RAG 路由: 多级降级检索 + 幻觉检测自纠正 ──
    if route_result.target in (RouteTarget.RAG, RouteTarget.HYBRID):
        # 多级降级检索
        strategy = get_degradation_strategy(retriever)
        degradation_result = strategy.search_with_degradation(
            query=route_result.rewritten_query,
            top_k=req.top_k,
            use_rerank=req.use_reranker,
        )

        response.results = [
            SearchResultItem(
                chunk_id=r.chunk_id,
                text=r.text,
                score=r.score,
                doc_type=r.doc_type,
                source_file=r.source_file,
                heading_path=r.heading_path,
            )
            for r in degradation_result.response.results
        ]
        response.search_time_ms = degradation_result.response.elapsed_ms
        response.degradation_level = degradation_result.level
        response.degradation_method = degradation_result.method

        # 幻觉检测自纠正生成
        if response.results:
            corrector = get_corrector(retriever)
            gen_result = corrector.generate_with_correction(
                query=route_result.rewritten_query,
                top_k=req.top_k,
                use_rerank=req.use_reranker,
            )
            response.reply = gen_result.answer
            response.faithfulness = gen_result.faithfulness
            response.correction_rounds = gen_result.correction_rounds
            response.was_corrected = gen_result.was_corrected
        elif degradation_result.level == 4:
            response.reply = (
                "抱歉，我目前的知识库中没有找到关于该问题的信息。"
                "建议您通过以下方式获取帮助：联系人工客服。"
            )
        else:
            response.reply = "抱歉，没有找到相关信息。"

    # ── SQL 路由: 预留 ──
    elif route_result.target == RouteTarget.SQL:
        response.reply = "订单/物流查询功能开发中，请提供订单号以便人工查询。"

    # ── 直接回复: 闲聊 ──
    elif route_result.target == RouteTarget.DIRECT:
        response.reply = "您好！我是电商智能客服，请问有什么可以帮您？"

    # ── 转人工 ──
    elif route_result.target == RouteTarget.HUMAN:
        response.reply = "您的问题已记录，将为您转接人工客服。"

    return response
