"""模块12 对话路由 — POST /api/chat

LangGraph 图编排 + 意图路由 + 多级降级检索 + 幻觉检测自纠正 + 人工介入
"""

import logging

from fastapi import APIRouter

from src.api.models import ChatRequest, ChatResponse, SearchResultItem
from src.graph import get_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["对话"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """智能客服对话 — LangGraph 图编排

    流程:
      1. 意图分类 (LLM Function Calling)
      2. 人工介入判断（退款/投诉/敏感话题）
      3. 路由决策 (RAG / SQL / 直接回复 / 转人工)
      4. 多级降级检索 (Level 1→2→3→4)
      5. 幻觉检测 + 自纠正闭环 (最多2轮)
    """
    workflow = get_workflow()

    result = workflow.run(
        query=req.query,
        top_k=req.top_k,
        use_reranker=req.use_reranker,
    )

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
    )

    return response
