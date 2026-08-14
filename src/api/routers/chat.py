"""模块12 对话路由 — POST /api/chat

LangGraph 图编排 + 意图路由 + 多级降级检索 + 幻觉检测自纠正 + 人工介入
+ 多轮对话（会话历史 → 指代消解）+ 情绪识别
"""

import logging

from fastapi import APIRouter, Depends

from src.access import is_admin
from src.api.auth import CurrentUser
from src.api.deps import get_current_user
from src.api.models import ChatRequest, ChatResponse, SearchResultItem
from src.config import settings
from src.conversation import Message, get_session_manager, get_session_memory
from src.engineering.pii_redactor import get_pii_redactor
from src.graph import get_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["对话"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    """智能客服对话 — LangGraph 图编排（需要登录，按用户 access_level 过滤知识范围）

    流程:
      0. PII 脱敏（入口安全: 手机号/身份证/银行卡等自动替换）
      1. 意图分类 (LLM Function Calling)
      2. 人工介入判断（退款/投诉/敏感话题）
      3. 路由决策 (RAG / SQL / 直接回复 / 转人工)
      4. 多级降级检索 (Level 1→2→3→4, 按用户等级过滤)
      5. 幻觉检测 + 自纠正闭环 (最多2轮)
    """
    # ── 模块33: 会话按用户隔离（用户 A 永远只能触达 "{username}:" 前缀的 key）──
    sid = f"{current_user.username}:{req.session_id}"

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

    # 重置 LLM token 累加器，统计本次请求真实用量（而非字符数估算）
    from src.engineering.llm_client import get_llm_client

    get_llm_client().reset_usage()

    # ── 多轮对话: 加载会话历史（指代消解用）──
    session_manager = get_session_manager()
    session = session_manager.get_session(sid)
    if not session:
        session = session_manager.create_session(sid)
    history = [{"role": m.role, "content": m.content} for m in session.messages[-6:]]

    # 三层记忆: 组装"最小有用上下文"（实体ledger/滚动摘要/历史片段）
    memory_context = get_session_memory(sid).build_context(safe_query)

    try:
        result = workflow.run(
            query=safe_query,
            session_id=sid,
            top_k=req.top_k,
            use_reranker=req.use_reranker,
            history=history,
            memory_context=memory_context,
            access_level=current_user.access_level,
            # 修复(审查): 订单查询按用户隔离，防枚举单号越权
            user_id=current_user.seed_user_id,
            is_admin=is_admin(current_user.role),
        )
    except Exception:
        logger.exception("对话工作流执行失败: query=%s", safe_query[:100])
        result = {
            "query": req.query,
            "answer": "系统暂时繁忙，请稍后重试。",
            "error": "workflow_execution_failed",
        }

    # ── 多轮对话: 保存本轮消息到会话历史（用命名空间 sid，按用户隔离）──
    try:
        session_manager.add_message(
            sid,
            Message(
                role="user",
                content=safe_query,
                intent=result.get("intent", ""),
            ),
        )
        session_manager.add_message(
            sid,
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
        logger.warning("保存会话历史失败: %s", sid)

    # 三层记忆: 记录本轮（抽实体 + 更新滚动摘要）
    try:
        get_session_memory(sid).record_turn(safe_query, result.get("answer", ""))
    except Exception:
        logger.warning("记录会话记忆失败: %s", sid)

    # 成本监控: 记录本次查询（token 数按长度粗略估算，成本用官方价格折算）
    try:
        from src.engineering import get_monitor
        from src.engineering.llm_client import get_llm_client
        from src.engineering.monitor import QueryRecord, estimate_cost

        _answer = result.get("answer", "")
        _usage = get_llm_client().total_usage
        _prompt_tokens = _usage.get("prompt_tokens") or max(1, len(safe_query))
        _completion_tokens = _usage.get("completion_tokens") or max(
            1, len(_answer) // 2
        )
        _total_tokens = _usage.get("total_tokens") or (
            _prompt_tokens + _completion_tokens
        )
        get_monitor().record(
            QueryRecord(
                user_query=safe_query,
                intent=result.get("intent", ""),
                retrieval_method=result.get("degradation_method", "hybrid"),
                degradation_level=result.get("degradation_level", 1),
                retrieval_docs_count=len(result.get("retrieved_docs", [])),
                retrieval_time_ms=result.get("search_time_ms", 0),
                hallucination_detected=result.get("was_corrected", False),
                self_correction_rounds=result.get("correction_rounds", 0),
                faithfulness=result.get("faithfulness", 0),
                prompt_tokens=_prompt_tokens,
                completion_tokens=_completion_tokens,
                total_tokens=_total_tokens,
                llm_cost=estimate_cost(
                    settings.default_model, _prompt_tokens, _completion_tokens
                ),
                total_time_ms=result.get("search_time_ms", 0),
                final_answer_length=len(_answer),
                session_id=sid,
                model_used=settings.default_model,
            )
        )
    except Exception as e:
        logger.warning("成本监控记录失败: %s", e)

    # 修复(审查): 评估不通过(忠实度低/检索降级/诚实兜底)应上抛人工核验标志，
    # 否则"无法确认"类低质量答案被静默返回，绕过"高敏承诺需 ≥0.85 否则转人工"的护栏。
    needs_human = result.get("needs_human", False)
    human_reason = result.get("human_reason", "")
    if not needs_human and result.get("evaluation_passed") is False:
        needs_human = True
        human_reason = human_reason or "回答质量评估未通过，建议人工核验"

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
        needs_human=needs_human,
        human_reason=human_reason,
        human_priority=result.get("human_priority", ""),
        emotion=result.get("emotion", "calm"),
        handoff_payload=result.get("handoff_payload", {}),
    )

    return response
