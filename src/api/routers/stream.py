"""模块12 流式对话路由 — POST /api/chat/stream (SSE)

流式输出 + 多轮对话管理
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from src.api.auth import CurrentUser
from src.api.deps import get_current_user, get_retriever
from src.conversation import (
    Message,
    get_retrieval_judge,
    get_session_manager,
    get_streaming_generator,
)
from src.embedding.degradation import get_degradation_strategy
from src.embedding.retriever import Retriever
from src.engineering.pii_redactor import get_pii_redactor
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
    current_user: CurrentUser = Depends(get_current_user),
):
    """流式客服对话 — SSE 输出（需要登录，按用户 access_level 过滤知识范围）

    流程:
      1. 意图分类
      2. 智能重检索判断（多轮对话时）
      3. 多级降级检索（按用户等级过滤）
      4. 流式生成回答
    """
    # 模块33: 会话按用户隔离
    sid = f"{current_user.username}:{session_id}"

    session_manager = get_session_manager()
    streaming_gen = get_streaming_generator()
    retrieval_judge = get_retrieval_judge()

    # 获取会话历史
    session = session_manager.get_session(sid)
    if not session:
        session = session_manager.create_session(sid)

    history = [{"role": m.role, "content": m.content} for m in session.messages[-6:]]

    # ── 第0步: PII 脱敏 ──
    redactor = get_pii_redactor()
    safe_query, pii_found = redactor.redact(query)
    if pii_found:
        logger.warning(
            "PII 脱敏 (stream): 输入包含 %d 项敏感信息 (%s)",
            len(pii_found),
            ", ".join(f["type"] for f in pii_found),
        )

    # 意图分类
    router_instance = get_router()
    route_result = router_instance.route(safe_query)

    # 情绪识别（改进: 愤怒/极端 → 安抚 + 优先转人工，不让机器人激化矛盾）
    from src.conversation import (
        get_coreference_resolver,
        get_emotion_detector,
        get_session_memory,
    )

    emotion_result = get_emotion_detector().detect(safe_query)
    emotion = emotion_result.level.value
    emotion_escalate = emotion in ("angry", "extreme")

    # 多轮指代消解（改进: 结合历史 + 三层记忆补全追问，
    # 如"那需要运费吗"→"退货需要运费吗"、"上次那个券"→"满300减50券"）
    retrieval_query = route_result.rewritten_query
    if not emotion_escalate:
        memory_context = get_session_memory(sid).build_context(safe_query)
        if history or memory_context:
            retrieval_query = get_coreference_resolver().resolve(
                route_result.rewritten_query, history, memory_context
            )

    # 智能重检索判断
    need_retrieval = True
    if history:
        need_retrieval, reason = retrieval_judge.should_retrieve(query, history)
        logger.info("重检索判断: %s, reason: %s", need_retrieval, reason)

    async def event_generator() -> AsyncGenerator[str, None]:
        docs = []
        sources = []

        # 情绪极端/愤怒 → 直接安抚 + 转人工，跳过检索与生成
        if emotion_escalate:
            yield f"data: {json.dumps({'event': 'status', 'data': '正在为您转接人工客服...'})}\n\n"
            from src.conversation import get_human_handler

            template = get_human_handler().get_human_response_template("high_emotion")
            for token in template:
                yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"
            yield f"data: {json.dumps({'event': 'emotion', 'data': emotion})}\n\n"
            yield f"data: {json.dumps({'event': 'done', 'data': '[DONE]'})}\n\n"
            return

        # 检索阶段（用 asyncio.to_thread 包装同步阻塞调用，避免阻塞事件循环）
        if need_retrieval and route_result.target in (
            RouteTarget.RAG,
            RouteTarget.HYBRID,
        ):
            # 发送检索状态
            yield f"data: {json.dumps({'event': 'status', 'data': '检索中...'})}\n\n"

            strategy = get_degradation_strategy(retriever)

            # 关键修复: 用 asyncio.to_thread 包装同步阻塞的检索调用
            # 双路召回: 原始问题（保真度） + 改写/指代消解后问题（专业术语）并行合并
            degradation_result = await asyncio.to_thread(
                strategy.search_with_degradation,
                query=route_result.query,
                secondary_query=retrieval_query,
                top_k=top_k,
                use_rerank=use_reranker,
                access_level=current_user.access_level,
            )
            docs = [r.text for r in degradation_result.response.results]
            sources = [r.source_file for r in degradation_result.response.results]

            # 发送检索结果
            yield f"data: {json.dumps({'event': 'sources', 'data': sources[:3]})}\n\n"

        # 流式生成
        yield f"data: {json.dumps({'event': 'status', 'data': '生成中...'})}\n\n"

        full_response = ""
        try:
            # 修复(审查): LLM 输入与会话存储统一用脱敏后的 safe_query，
            # 与 chat.py 一致，避免原始含手机号/身份证的 query 明文入库并直送 LLM。
            async for event in streaming_gen.stream_generate(
                query=safe_query,
                docs=docs,
                session_history=history,
            ):
                if event.event == "token":
                    full_response += event.data
                    yield f"data: {json.dumps({'event': 'token', 'data': event.data})}\n\n"
                elif event.event == "done":
                    # 保存到会话历史（命名空间 sid，按用户隔离）
                    session_manager.add_message(
                        sid,
                        Message(
                            role="user",
                            content=safe_query,
                            intent=route_result.intent_result.intent.value,
                        ),
                    )
                    session_manager.add_message(
                        sid,
                        Message(
                            role="assistant", content=full_response, sources=sources
                        ),
                    )
                    # 三层记忆: 记录本轮（抽实体 + 更新滚动摘要）
                    try:
                        get_session_memory(sid).record_turn(safe_query, full_response)
                    except Exception:
                        logger.warning("记录会话记忆失败: %s", sid)
                    yield f"data: {json.dumps({'event': 'done', 'data': '[DONE]'})}\n\n"
                elif event.event == "error":
                    yield f"data: {json.dumps({'event': 'error', 'data': event.data})}\n\n"
        except Exception as e:
            # 关键修复: 异常时发送 error 事件，避免客户端一直等待
            logger.error("流式生成异常: %s", e)
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
