"""模块12 对话路由 — POST /api/chat

意图路由 + RAG 检索 + 生成回复（预留 LLM 生成）
"""

import logging

from fastapi import APIRouter, Depends

from src.api.deps import get_retriever
from src.api.models import ChatRequest, ChatResponse, SearchResultItem
from src.embedding.retriever import Retriever
from src.routing import RouteTarget, get_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["对话"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    retriever: Retriever = Depends(get_retriever),
) -> ChatResponse:
    """智能客服对话 — 意图路由 + 检索 + 回复

    流程:
      1. 意图分类 (LLM Function Calling)
      2. 路由决策 (RAG / SQL / 直接回复 / 转人工)
      3. 查询改写 (RAG 路由时)
      4. 语义检索 (RAG 路由时)
      5. 生成回复 (预留)
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

    # ── RAG 路由: 检索 ──
    if route_result.target in (RouteTarget.RAG, RouteTarget.HYBRID):
        search_response = retriever.search(
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
            for r in search_response.results
        ]
        response.search_time_ms = search_response.elapsed_ms

        # TODO: 调用 LLM 生成最终回复
        # 暂时返回检索结果的拼接
        if response.results:
            context = "\n".join(r.text[:200] for r in response.results[:3])
            response.reply = f"[RAG 检索到 {len(response.results)} 条结果]\n\n{context}"
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
