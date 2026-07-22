"""LangGraph 图编排 — 电商客服 RAG 核心流程

图结构:
  classify_intent → route_decision
    ├── rag_route → retrieve → check_hallucination → (loop/return)
    ├── sql_route → sql_query → return
    ├── human_route → human_handler → return
    └── direct_route → direct_reply → return
"""

import logging
from typing import Annotated, Any, Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.conversation import get_human_handler
from src.embedding.degradation import get_degradation_strategy
from src.generation import get_corrector
from src.routing import RouteTarget, get_router

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════
# 状态定义
# ═══════════════════════════════════════


class RAGState(TypedDict):
    """RAG 工作流状态"""

    # 输入
    query: str
    session_id: str
    top_k: int
    use_reranker: bool

    # 意图分类结果
    intent: str
    confidence: float
    target: str
    rewritten_query: str
    reasoning: str

    # 检索结果
    retrieved_docs: list[dict]
    search_time_ms: float
    degradation_level: int
    degradation_method: str

    # 生成结果
    answer: str
    faithfulness: float
    correction_rounds: int
    was_corrected: bool

    # 人工介入
    needs_human: bool
    human_reason: str
    human_priority: str

    # 错误
    error: str


# ═══════════════════════════════════════
# 节点函数
# ═══════════════════════════════════════


def classify_intent(state: RAGState) -> dict:
    """节点1: 意图分类"""
    logger.info("节点: classify_intent, query=%s", state["query"][:50])

    router = get_router()
    route_result = router.route(state["query"])

    return {
        "intent": route_result.intent_result.intent.value,
        "confidence": route_result.intent_result.confidence,
        "target": route_result.target.value,
        "rewritten_query": route_result.rewritten_query,
        "reasoning": route_result.intent_result.reasoning,
    }


def check_human_needed(state: RAGState) -> dict:
    """节点2: 人工介入判断"""
    logger.info("节点: check_human_needed")

    handler = get_human_handler()
    check = handler.check_needs_human(
        query=state["query"],
        intent=state["intent"],
        confidence=state["confidence"],
    )

    return {
        "needs_human": check["needs_human"],
        "human_reason": check["reason"],
        "human_priority": check["priority"],
    }


def retrieve_docs(state: RAGState) -> dict:
    """节点3: 文档检索"""
    logger.info("节点: retrieve_docs, query=%s", state["rewritten_query"][:50])

    from src.embedding.retriever import get_retriever

    retriever = get_retriever()
    strategy = get_degradation_strategy(retriever)

    result = strategy.search_with_degradation(
        query=state["rewritten_query"],
        top_k=state.get("top_k", 5),
        use_rerank=state.get("use_reranker", True),
    )

    docs = [
        {
            "chunk_id": r.chunk_id,
            "text": r.text,
            "score": r.score,
            "doc_type": r.doc_type,
            "source_file": r.source_file,
        }
        for r in result.response.results
    ]

    return {
        "retrieved_docs": docs,
        "search_time_ms": result.response.elapsed_ms,
        "degradation_level": result.level,
        "degradation_method": result.method,
    }


def generate_answer(state: RAGState) -> dict:
    """节点4: 生成回答（带幻觉检测自纠正）"""
    logger.info("节点: generate_answer")

    from src.embedding.retriever import get_retriever

    retriever = get_retriever()
    corrector = get_corrector(retriever)

    result = corrector.generate_with_correction(
        query=state["rewritten_query"],
        top_k=state.get("top_k", 5),
        use_rerank=state.get("use_reranker", True),
    )

    return {
        "answer": result.answer,
        "faithfulness": result.faithfulness,
        "correction_rounds": result.correction_rounds,
        "was_corrected": result.was_corrected,
    }


def handle_human(state: RAGState) -> dict:
    """节点5: 人工介入处理"""
    logger.info("节点: handle_human, reason=%s", state.get("human_reason", ""))

    handler = get_human_handler()
    scenario = state.get("human_reason", "")

    # 根据场景选择模板
    if "退款" in state["query"]:
        template = handler.get_human_response_template("refund_request")
    elif "投诉" in state["query"]:
        template = handler.get_human_response_template("complaint")
    elif "法律" in state["query"] or "起诉" in state["query"]:
        template = handler.get_human_response_template("sensitive_topic")
    else:
        template = handler.get_human_response_template("low_confidence")

    return {
        "answer": template,
        "needs_human": True,
    }


def handle_sql(state: RAGState) -> dict:
    """节点6: SQL 查询（预留）"""
    logger.info("节点: handle_sql (预留)")

    return {
        "answer": "订单/物流查询功能开发中，请提供订单号以便人工查询。",
    }


def handle_direct(state: RAGState) -> dict:
    """节点7: 直接回复（闲聊）"""
    logger.info("节点: handle_direct")

    return {
        "answer": "您好！我是电商智能客服，请问有什么可以帮您？",
    }


def handle_error(state: RAGState) -> dict:
    """节点8: 错误处理"""
    logger.error("节点: handle_error, error=%s", state.get("error", ""))

    return {
        "answer": "系统暂时繁忙，请稍后重试。",
    }


# ═══════════════════════════════════════
# 条件边函数
# ═══════════════════════════════════════


def route_decision(state: RAGState) -> str:
    """条件边: 根据意图路由到不同处理节点"""
    target = state.get("target", "rag")

    # 优先检查人工介入
    if state.get("needs_human", False):
        return "human"

    if target == "rag" or target == "hybrid":
        return "rag"
    elif target == "sql":
        return "sql"
    elif target == "human":
        return "human"
    else:
        return "direct"


def should_retry(state: RAGState) -> str:
    """条件边: 检查是否需要重试"""
    if state.get("error"):
        return "error"
    return "end"


# ═══════════════════════════════════════
# 工作流构建
# ═══════════════════════════════════════


def build_rag_workflow() -> StateGraph:
    """构建 RAG 工作流图"""

    workflow = StateGraph(RAGState)

    # 添加节点
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("check_human", check_human_needed)
    workflow.add_node("retrieve", retrieve_docs)
    workflow.add_node("generate", generate_answer)
    workflow.add_node("human", handle_human)
    workflow.add_node("sql", handle_sql)
    workflow.add_node("direct", handle_direct)
    workflow.add_node("error", handle_error)

    # 设置入口
    workflow.set_entry_point("classify_intent")

    # 添加边
    workflow.add_edge("classify_intent", "check_human")

    # 条件边: 路由决策
    workflow.add_conditional_edges(
        "check_human",
        route_decision,
        {
            "rag": "retrieve",
            "sql": "sql",
            "human": "human",
            "direct": "direct",
        },
    )

    # RAG 流程
    workflow.add_edge("retrieve", "generate")
    workflow.add_conditional_edges(
        "generate",
        should_retry,
        {
            "error": "error",
            "end": END,
        },
    )

    # 终止节点
    workflow.add_edge("human", END)
    workflow.add_edge("sql", END)
    workflow.add_edge("direct", END)
    workflow.add_edge("error", END)

    return workflow


# ═══════════════════════════════════════
# 工作流封装
# ═══════════════════════════════════════


class RAGWorkflow:
    """RAG 工作流封装

    使用方式:
        workflow = RAGWorkflow()
        result = workflow.run(query="怎么退货？")
        print(result["answer"])
    """

    def __init__(self):
        self._graph = build_rag_workflow()
        self._app = self._graph.compile()

    def run(
        self,
        query: str,
        session_id: str = "default",
        top_k: int = 5,
        use_reranker: bool = True,
    ) -> dict:
        """运行工作流

        Args:
            query: 用户查询
            session_id: 会话ID
            top_k: 检索结果数
            use_reranker: 是否启用 Reranker

        Returns:
            状态字典
        """
        initial_state = {
            "query": query,
            "session_id": session_id,
            "top_k": top_k,
            "use_reranker": use_reranker,
            "intent": "",
            "confidence": 0.0,
            "target": "",
            "rewritten_query": query,
            "reasoning": "",
            "retrieved_docs": [],
            "search_time_ms": 0,
            "degradation_level": 1,
            "degradation_method": "hybrid",
            "answer": "",
            "faithfulness": 0.0,
            "correction_rounds": 0,
            "was_corrected": False,
            "needs_human": False,
            "human_reason": "",
            "human_priority": "",
            "error": "",
        }

        try:
            result = self._app.invoke(initial_state)
            return result
        except Exception as e:
            logger.error("工作流执行失败: %s", e)
            return {
                **initial_state,
                "answer": "系统暂时繁忙，请稍后重试。",
                "error": str(e),
            }

    def get_graph(self):
        """获取图对象（用于可视化）"""
        return self._app


# ── 模块级单例 ──

_workflow_instance: RAGWorkflow | None = None


def get_workflow() -> RAGWorkflow:
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = RAGWorkflow()
    return _workflow_instance
