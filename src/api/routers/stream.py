"""模块12 流式对话路由 — POST /api/chat/stream (SSE)

流式输出 + 多轮对话管理
"""

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from src.api.deps import get_retriever
from src.conversation import (
    Message,
    get_retrieval_judge,
    get_session_manager,
    get_streaming_generator,
)
from src.embedding.degradation import get_degradation_strategy
from src.embedding.retriever import Retriever
from src.routing import RouteTarget, get_router

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["流式对话"])


@router.post("/chat/stream")
async def chat_stream(
    query: str,
    session_id: str = Query(default="default"),
    top_k: int = Query(default=5, ge=1, le=20),
    use_reranker: bool = Query(default=True),
    retriever: Retriever = Depends(get_retriever),
):
    """流式客服对话 — SSE 输出

    流程:
      1. 意图分类
      2. 智能重检索判断（多轮对话时）
      3. 多级降级检索
      4. 流式生成回答
    """
    session_manager = get_session_manager()
    streaming_gen = get_streaming_generator()
    retrieval_judge = get_retrieval_judge()

    # 获取会话历史
    session = session_manager.get_session(session_id)
    if not session:
        session = session_manager.create_session(session_id)

    history = [{"role": m.role, "content": m.content} for m in session.messages[-6:]]

    # 意图分类
    router_instance = get_router()
    route_result = router_instance.route(query)

    # 智能重检索判断
    need_retrieval = True
    if history:
        need_retrieval, reason = retrieval_judge.should_retrieve(query, history)
        logger.info("重检索判断: %s, reason: %s", need_retrieval, reason)

    async def event_generator() -> AsyncGenerator[str, None]:
        docs = []
        sources = []

        # 检索阶段
        if need_retrieval and route_result.target in (
            RouteTarget.RAG,
            RouteTarget.HYBRID,
        ):
            # 发送检索状态
            yield f"data: {json.dumps({'event': 'status', 'data': '检索中...'})}\n\n"

            strategy = get_degradation_strategy(retriever)
            degradation_result = strategy.search_with_degradation(
                query=route_result.rewritten_query,
                top_k=top_k,
                use_rerank=use_reranker,
            )
            docs = [r.text for r in degradation_result.response.results]
            sources = [r.source_file for r in degradation_result.response.results]

            # 发送检索结果
            yield f"data: {json.dumps({'event': 'sources', 'data': sources[:3]})}\n\n"

        # 流式生成
        yield f"data: {json.dumps({'event': 'status', 'data': '生成中...'})}\n\n"

        full_response = ""
        async for event in streaming_gen.stream_generate(
            query=query,
            docs=docs,
            session_history=history,
        ):
            if event.event == "token":
                full_response += event.data
                yield f"data: {json.dumps({'event': 'token', 'data': event.data})}\n\n"
            elif event.event == "done":
                # 保存到会话历史
                session_manager.add_message(
                    session_id,
                    Message(
                        role="user",
                        content=query,
                        intent=route_result.intent_result.intent.value,
                    ),
                )
                session_manager.add_message(
                    session_id,
                    Message(role="assistant", content=full_response, sources=sources),
                )
                yield f"data: {json.dumps({'event': 'done', 'data': '[DONE]'})}\n\n"
            elif event.event == "error":
                yield f"data: {json.dumps({'event': 'error', 'data': event.data})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
