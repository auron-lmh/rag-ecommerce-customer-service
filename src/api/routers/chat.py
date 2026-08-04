"""模块12 对话路由 — POST /api/chat

LangGraph 图编排 + 意图路由 + 多级降级检索 + 幻觉检测自纠正 + 人工介入
+ 多轮对话（会话历史 → 指代消解）+ 情绪识别
"""

import logging

from fastapi import APIRouter

from src.api.models import ChatRequest, ChatResponse, SearchResultItem
from src.conversation import Message, get_session_manager, get_session_memory
from src.engineering.pii_redactor import get_pii_redactor
from src.graph import get_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["对话"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """智能客服对话 — LangGraph 图编排

    流程:
      0. PII 脱敏（入口安全: 手机号/身份证/银行卡等自动替换）
      1. 意图分类 (LLM Function Calling)
      2. 人工介入判断（退款/投诉/敏感话题）
      3. 路由决策 (RAG / SQL / 直接回复 / 转人工)
      4. 多级降级检索 (Level 1→2→3→4)
      5. 幻觉检测 + 自纠正闭环 (最多2轮)
    """
    # ── 第0步: PII 脱敏 ──
    redactor = get_pii_redactor()
    safe_query, pii_found = redactor.redact(req.query)
    if pii_found:
        logger.warning(
            "PII 脱敏: 输入包含 %d 项敏感信息 (%s)",
            len(pii_found),
            ", ".join(f["type"] for f in pii_found),
        )

    workflow = get_workflow()

    # ── 多轮对话: 加载会话历史（指代消解用）──
    session_manager = get_session_manager()
    session = session_manager.get_session(req.session_id)
    if not session:
        session = session_manager.create_session(req.session_id)
    history = [{"role": m.role, "content": m.content} for m in session.messages[-6:]]

    # 三层记忆: 组装"最小有用上下文"（实体ledger/滚动摘要/历史片段）
    memory_context = get_session_memory(req.session_id).build_context(safe_query)

    try:
        result = workflow.run(
            query=safe_query,
            session_id=req.session_id,
            top_k=req.top_k,
            use_reranker=req.use_reranker,
            history=history,
            memory_context=memory_context,
        )
    except Exception:
        logger.exception("对话工作流执行失败: query=%s", safe_query[:100])
        result = {
            "query": req.query,
            "answer": "系统暂时繁忙，请稍后重试。",
            "error": "workflow_execution_failed",
        }

    # ── 多轮对话: 保存本轮消息到会话历史 ──
    try:
        session_manager.add_message(
            req.session_id,
            Message(
                role="user",
                content=safe_query,
                intent=result.get("intent", ""),
            ),
        )
        session_manager.add_message(
            req.session_id,
            Message(
                role="assistant",
                content=result.get("answer", ""),
                sources=[
                    doc.get("source_file", "")
                    for doc in result.get("retrieved_docs", [])
                ],
            ),
        )
    except Exception:
        logger.warning("保存会话历史失败: %s", req.session_id)

    # 三层记忆: 记录本轮（抽实体 + 更新滚动摘要）
    try:
        get_session_memory(req.session_id).record_turn(
            safe_query, result.get("answer", "")
        )
    except Exception:
        logger.warning("记录会话记忆失败: %s", req.session_id)

    # 构建响应
    response = ChatResponse(
        query=result.get("query", req.query),
        intent=result.get("intent", ""),
        confidence=result.get("confidence", 0.0),
        target=result.get("target", ""),
        rewritten_query=result.get("rewritten_query", req.query),
        reasoning=result.get("reasoning", ""),
        results=[
            SearchResultItem(
                chunk_id=doc.get("chunk_id", ""),
                text=doc.get("text", ""),
                score=doc.get("score", 0.0),
                doc_type=doc.get("doc_type", ""),
                source_file=doc.get("source_file", ""),
            )
            for doc in result.get("retrieved_docs", [])
        ],
        reply=result.get("answer", ""),
        search_time_ms=result.get("search_time_ms", 0),
        degradation_level=result.get("degradation_level", 1),
        degradation_method=result.get("degradation_method", "hybrid"),
        faithfulness=result.get("faithfulness", 0.0),
        correction_rounds=result.get("correction_rounds", 0),
        was_corrected=result.get("was_corrected", False),
        needs_human=result.get("needs_human", False),
        human_reason=result.get("human_reason", ""),
        human_priority=result.get("human_priority", ""),
        emotion=result.get("emotion", "calm"),
        handoff_payload=result.get("handoff_payload", {}),
    )

    return response
