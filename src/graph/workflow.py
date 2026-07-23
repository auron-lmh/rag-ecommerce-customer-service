"""LangGraph 图编排 — 电商客服 RAG 核心流程（Agentic RAG + Human-in-the-Loop）

图结构 (2026-07 升级版):
  classify_intent → check_human → route_decision
    ├── rag_route → retrieve (Hybrid: BM25+Dense)
    │                  ├── [有结果] → generate → evaluate_quality
    │                  │                      ├── [通过] → END
    │                  │                      └── [不通过] → human_approval
    │                  │                                       ├── [批准] → END
    │                  │                                       └── [拒绝] → rewrite → retrieve...
    │                  │
    │                  └── [结果为空/Level≥4] → web_search (智谱/Tavily)
    │                                             └── → generate → evaluate...
    ├── human_route → human_handler → END
    ├── sql_route → sql_query → END
    └── direct_route → direct_reply → END

特性:
  - 级联检索: Hybrid Search → 联网搜索 (两个独立图节点，可视化)
  - Agentic RAG: 生成 → 评估 → 纠正 闭环（最多 3 轮）
  - Human-in-the-Loop: LangGraph interrupt_before 真正中断等待人工
  - 多级降级: 5 级（原始→改写→扩展→联网→兜底）
  - 幻觉检测自纠正: G-Eval LLM 自检
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

# 最大重试轮数（防止无限循环）
MAX_LOOP_COUNT = 3


# ═══════════════════════════════════════
# 状态定义
# ═══════════════════════════════════════


class RAGState(TypedDict):
    """RAG 工作流状态（支持多轮 Agentic 循环）"""

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

    # 质量评估（新增）
    evaluation_score: float
    evaluation_passed: bool

    # 人工介入
    needs_human: bool
    human_reason: str
    human_priority: str
    human_decision: str  # "approve" | "rejected" | "" (由外部注入)

    # Agentic 循环控制
    loop_count: int  # 防止无限循环

    # 错误
    error: str


# ═══════════════════════════════════════
# 节点函数
# ═══════════════════════════════════════


def classify_intent(state: RAGState) -> dict:
    """节点1: 意图分类（LLM Function Calling）"""
    logger.info("[节点] classify_intent, query=%s", state["query"][:50])

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
    """节点2: 人工介入预判"""
    logger.info("[节点] check_human_needed")

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
    """节点3: 多级降级检索"""
    logger.info("[节点] retrieve_docs, query=%s", state["rewritten_query"][:50])

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


def web_search(state: RAGState) -> dict:
    """节点4: 联网搜索（级联检索第二级 — 独立图节点，面试可视化）

    当 Hybrid Search 返回空或降级到 Level≥4 时触发。
    优先使用智谱联网搜索，其次 Tavily Search API。
    """
    logger.info(
        "[节点] web_search: query=%s, level=%d",
        state["rewritten_query"][:50],
        state.get("degradation_level", 1),
    )

    from src.embedding.degradation import DegradationStrategy

    # 直接调用 DegradationStrategy 的联网搜索方法
    from src.embedding.retriever import get_retriever

    retriever = get_retriever()
    strategy = DegradationStrategy(retriever)

    web_results = strategy._web_search(state["rewritten_query"])

    if web_results:
        docs = [
            {
                "chunk_id": f"web_{i}",
                "text": r.get("snippet", r.get("title", "")),
                "score": 0.5,  # 联网结果固定中等分数
                "doc_type": "web",
                "source_file": r.get("url", r.get("title", f"web_result_{i}")),
            }
            for i, r in enumerate(web_results[: state.get("top_k", 5)])
        ]
        logger.info("[节点] 联网搜索命中: %d 条结果", len(docs))
        return {
            "retrieved_docs": docs,
            "degradation_level": 4,
            "degradation_method": "web_search",
        }
    else:
        logger.warning("[节点] 联网搜索无结果，使用兜底")
        return {
            "retrieved_docs": [],
            "degradation_level": 5,
            "degradation_method": "fallback",
        }


def generate_answer(state: RAGState) -> dict:
    """节点5: 生成回答（复用 workflow 检索结果 + 幻觉检测自纠正）"""
    logger.info("[节点] generate_answer, docs=%d", len(state.get("retrieved_docs", [])))

    from src.embedding.retriever import get_retriever

    retriever = get_retriever()
    corrector = get_corrector(retriever)

    retrieved_docs = state.get("retrieved_docs", [])
    docs_texts = [d["text"] for d in retrieved_docs]
    sources = list(
        {d.get("source_file", "") for d in retrieved_docs if d.get("source_file")}
    )

    if not docs_texts:
        # 降级：上游检索为空，走完整检索流程
        result = corrector.generate_with_correction(
            query=state["rewritten_query"],
            top_k=state.get("top_k", 5),
            use_rerank=state.get("use_reranker", True),
        )
    else:
        result = corrector.generate_with_docs(
            query=state["rewritten_query"],
            docs=docs_texts,
            sources=sources,
            top_k=state.get("top_k", 5),
            use_rerank=state.get("use_reranker", True),
        )

    return {
        "answer": result.answer,
        "faithfulness": result.faithfulness,
        "correction_rounds": result.correction_rounds,
        "was_corrected": result.was_corrected,
    }


def evaluate_quality(state: RAGState) -> dict:
    """节点6: 评估生成质量（新增 — Agentic RAG 核心）

    检查:
      1. faithfulness ≥ 0.7 → 通过
      2. 回答包含 "无法确认" / "建议咨询" → 标记为需要人工
      3. 检索质量差（degradation_level ≥ 4）→ 标记为需要人工
    """
    logger.info(
        "[节点] evaluate_quality: faithfulness=%.2f, degradation=%d",
        state.get("faithfulness", 0),
        state.get("degradation_level", 1),
    )

    faithfulness = state.get("faithfulness", 0)
    degradation_level = state.get("degradation_level", 1)
    answer = state.get("answer", "")
    loop_count = state.get("loop_count", 0)

    # 低忠实度关键词
    uncertain_phrases = ["无法确认", "不确定", "没有找到", "建议咨询", "建议您咨询"]

    has_uncertain = any(phrase in answer for phrase in uncertain_phrases)
    quality_poor = faithfulness < 0.7 or degradation_level >= 4

    if loop_count >= MAX_LOOP_COUNT:
        # 已达最大循环次数，强制通过
        logger.warning("已达最大循环次数 %d，强制通过评估", MAX_LOOP_COUNT)
        return {
            "evaluation_score": faithfulness,
            "evaluation_passed": True,
        }

    if quality_poor or has_uncertain:
        reason_parts = []
        if faithfulness < 0.7:
            reason_parts.append(f"忠实度不足({faithfulness:.2f})")
        if degradation_level >= 4:
            reason_parts.append(f"检索降级严重(Level {degradation_level})")
        if has_uncertain:
            reason_parts.append("回答存在不确定性")

        logger.info("[节点] 评估不通过: %s", ", ".join(reason_parts))
        return {
            "evaluation_score": faithfulness,
            "evaluation_passed": False,
        }

    logger.info("[节点] 评估通过: faithfulness=%.2f", faithfulness)
    return {
        "evaluation_score": faithfulness,
        "evaluation_passed": True,
    }


def human_approval(state: RAGState) -> dict:
    """节点7: 人工审批（LangGraph interrupt_before 在此节点前中断）

    执行流程:
      1. 图执行到此处前自动中断（interrupt_before=["human_approval"]）
      2. 外部系统（chat_ui/admin_ui）调用 graph.update_state() 注入 human_decision
      3. 图恢复执行，此节点检查 human_decision 并返回结果
    """
    logger.info(
        "[节点] human_approval: decision=%s, reason=%s",
        state.get("human_decision", ""),
        state.get("human_reason", ""),
    )

    decision = state.get("human_decision", "")

    if decision == "approve":
        return {"human_decision": "approve"}
    elif decision == "rejected":
        return {"human_decision": "rejected"}
    else:
        # 没有外部输入默认拒绝（安全性优先）
        return {"human_decision": "rejected"}


def rewrite_and_retrieve(state: RAGState) -> dict:
    """节点8: 改写查询 + 重新检索（Agentic 回路）

    当人工审批拒绝后:
      1. 分析当前回答的不足
      2. 改写查询（补充缺失信息）
      3. 重新检索
    """
    logger.info(
        "[节点] rewrite_and_retrieve: loop=%d, query=%s",
        state.get("loop_count", 0) + 1,
        state["query"][:50],
    )

    from src.engineering.llm_client import get_llm_client

    client = get_llm_client()

    # 使用 LLM 改写查询
    rewrite_prompt = (
        f"之前的回答没有满足用户需求。请将以下用户问题改写为更精准的检索查询，"
        f"补充可能的隐含信息:\n\n"
        f"原始问题: {state['query']}\n"
        f"之前的回答: {state.get('answer', '')[:200]}\n\n"
        f"改写后查询:"
    )

    rewritten = client.chat_with_fallback(
        messages=[{"role": "user", "content": rewrite_prompt}],
        fallback_value=state["query"],
        temperature=0.3,
        max_tokens=100,
        timeout=10,
    )

    # 限制长度
    if len(rewritten) > 150:
        rewritten = rewritten[:150]

    loop_count = state.get("loop_count", 0) + 1
    logger.info(
        "[节点] 改写查询 (loop %d): %s → %s",
        loop_count,
        state["query"][:50],
        rewritten[:50],
    )

    return {
        "rewritten_query": rewritten,
        "loop_count": loop_count,
    }


def handle_human(state: RAGState) -> dict:
    """节点8: 人工介入处理（高风险场景直接转人工）"""
    logger.info("[节点] handle_human, reason=%s", state.get("human_reason", ""))

    handler = get_human_handler()
    query = state["query"]

    if "退款" in query:
        scenario = "refund_request"
    elif "投诉" in query:
        scenario = "complaint"
    elif "法律" in query or "起诉" in query:
        scenario = "sensitive_topic"
    else:
        scenario = "low_confidence"

    template = handler.get_human_response_template(scenario)

    return {
        "answer": template,
        "needs_human": True,
    }


def handle_sql(state: RAGState) -> dict:
    """节点9: SQL 查询（预留扩展）"""
    logger.info("[节点] handle_sql (预留)")

    return {
        "answer": "订单/物流查询功能开发中，请提供订单号以便人工查询。",
    }


def handle_direct(state: RAGState) -> dict:
    """节点10: 直接回复（闲聊场景）"""
    logger.info("[节点] handle_direct")

    return {
        "answer": "您好！我是电商智能客服，请问有什么可以帮您？",
    }


def handle_error(state: RAGState) -> dict:
    """节点11: 错误处理"""
    logger.error("[节点] handle_error, error=%s", state.get("error", ""))

    return {
        "answer": "系统暂时繁忙，请稍后重试。",
    }


# ═══════════════════════════════════════
# 条件边函数
# ═══════════════════════════════════════


def route_decision(state: RAGState) -> str:
    """条件边: 根据意图路由"""
    target = state.get("target", "rag")

    if state.get("needs_human", False):
        return "human"

    if target in ("rag", "hybrid"):
        return "rag"
    elif target == "sql":
        return "sql"
    elif target == "human":
        return "human"
    else:
        return "direct"


def evaluate_decision(state: RAGState) -> str:
    """条件边: 评估后路由（新增）

    - 评估通过 → END
    - 评估不通过 + loop_count < MAX → human_approval（人工介入）
    - 评估不通过 + loop_count >= MAX → END（强制结束）
    """
    if state.get("evaluation_passed", True):
        return "end"

    loop_count = state.get("loop_count", 0)
    if loop_count >= MAX_LOOP_COUNT:
        logger.warning("评估不通过但已达最大循环，强制结束")
        return "end"

    return "human"


def human_decision_edge(state: RAGState) -> str:
    """条件边: 人工审批后路由（新增）

    - approved → END
    - rejected → rewrite（重新改写+检索+生成）
    """
    decision = state.get("human_decision", "")
    if decision == "approve":
        return "end"
    return "rewrite"


def check_retrieval(state: RAGState) -> str:
    """条件边: 检索结果检查（新增 — 级联检索可视化）

    - 有结果 + 质量好 → generate（正常流程）
    - 结果为空或降级到 Level≥4 → web_search（联网搜索兜底）
    """
    docs = state.get("retrieved_docs", [])
    degradation_level = state.get("degradation_level", 1)

    if not docs or degradation_level >= 4:
        logger.info("[条件边] 检索为空或降级严重 → 联网搜索")
        return "web"
    return "generate"


def retry_after_rewrite(state: RAGState) -> str:
    """条件边: 改写后是否重试检索"""
    loop_count = state.get("loop_count", 0)
    if loop_count >= MAX_LOOP_COUNT:
        return "error"
    return "retrieve"


# ═══════════════════════════════════════
# 工作流构建
# ═══════════════════════════════════════


def build_rag_workflow() -> StateGraph:
    """构建 Agentic RAG 工作流图（含评估+人工介入+回路）"""

    workflow = StateGraph(RAGState)

    # ── 添加节点 ──
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("check_human", check_human_needed)
    workflow.add_node("retrieve", retrieve_docs)
    workflow.add_node("web_search", web_search)  # 新增: 联网搜索兜底
    workflow.add_node("generate", generate_answer)
    workflow.add_node("evaluate_quality", evaluate_quality)  # 新增
    workflow.add_node("human_approval", human_approval)  # 新增: 真正的 HITL
    workflow.add_node("rewrite_and_retrieve", rewrite_and_retrieve)  # 新增: 改写回路
    workflow.add_node("human", handle_human)
    workflow.add_node("sql", handle_sql)
    workflow.add_node("direct", handle_direct)
    workflow.add_node("error", handle_error)

    # ── 设置入口 ──
    workflow.set_entry_point("classify_intent")

    # ── 边 ──
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

    # ── Agentic RAG 主路径（含级联检索 + 回路） ──
    # 新增: retrieve → [有结果→generate] / [无结果→web_search]
    workflow.add_conditional_edges(
        "retrieve",
        check_retrieval,
        {
            "generate": "generate",
            "web": "web_search",
        },
    )
    workflow.add_edge("web_search", "generate")  # 联网搜索后走生成
    workflow.add_edge("generate", "evaluate_quality")

    # 新增: 评估 → END / human_approval
    workflow.add_conditional_edges(
        "evaluate_quality",
        evaluate_decision,
        {
            "end": END,
            "human": "human_approval",
        },
    )

    # 新增: 人工审批 → END / rewrite
    workflow.add_conditional_edges(
        "human_approval",
        human_decision_edge,
        {
            "end": END,
            "rewrite": "rewrite_and_retrieve",
        },
    )

    # 新增: 改写后 → retrieve / error
    workflow.add_conditional_edges(
        "rewrite_and_retrieve",
        retry_after_rewrite,
        {
            "retrieve": "retrieve",
            "error": "error",
        },
    )

    # ── 终止节点 ──
    workflow.add_edge("human", END)
    workflow.add_edge("sql", END)
    workflow.add_edge("direct", END)
    workflow.add_edge("error", END)

    return workflow


# ═══════════════════════════════════════
# 工作流封装
# ═══════════════════════════════════════


class RAGWorkflow:
    """Agentic RAG 工作流封装（支持 Human-in-the-Loop）

    使用方式:
        # 普通模式
        workflow = RAGWorkflow()
        result = workflow.run(query="怎么退货？")
        print(result["answer"])

        # Human-in-the-Loop 模式
        workflow = RAGWorkflow()
        config = {"configurable": {"thread_id": "session-123"}}

        # 启动执行（会在 human_approval 前中断）
        result = workflow.run(query="我要退款", config=config)

        if result.get("__interrupt__"):
            # 图中断，等待人工决策
            workflow.app.update_state(
                config,
                {"human_decision": "approve"}  # 或 "rejected"
            )
            result = workflow.resume(config)
    """

    def __init__(self):
        self._graph = build_rag_workflow()
        # 在 human_approval 节点前中断，等待外部注入 human_decision
        self._app = self._graph.compile(interrupt_before=["human_approval"])

    @property
    def app(self):
        """获取编译后的 LangGraph app（用于外部 update_state）"""
        return self._app

    def run(
        self,
        query: str,
        session_id: str = "default",
        top_k: int = 5,
        use_reranker: bool = True,
        config: dict | None = None,
    ) -> dict:
        """运行工作流（支持 Human-in-the-Loop 中断）

        Args:
            query: 用户查询
            session_id: 会话ID
            top_k: 检索结果数
            use_reranker: 是否启用 Reranker
            config: LangGraph config（含 thread_id 用于 HITL）

        Returns:
            状态字典。如果图中断，会包含 "__interrupt__" 标记
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
            "evaluation_score": 0.0,
            "evaluation_passed": True,
            "needs_human": False,
            "human_reason": "",
            "human_priority": "",
            "human_decision": "",
            "loop_count": 0,
            "error": "",
        }

        if config is None:
            config = {"configurable": {"thread_id": session_id}}

        try:
            result = self._app.invoke(initial_state, config)

            # 关键修复: 检查是否中断（HITL 场景）
            # LangGraph 中断时返回的对象可能包含 __interrupt__ 属性
            if hasattr(result, "__interrupt__"):
                return {
                    **initial_state,
                    "__interrupt__": result.__interrupt__,
                    "answer": "等待人工审批中...",
                }

            # 检查是否是 None（某些 LangGraph 版本中断时返回 None）
            if result is None:
                return {
                    **initial_state,
                    "__interrupt__": True,
                    "answer": "等待人工审批中...",
                }

            return result
        except Exception as e:
            logger.error("工作流执行失败: %s", e)
            return {
                **initial_state,
                "answer": "系统暂时繁忙，请稍后重试。",
                "error": str(e),
            }

    def resume(self, config: dict) -> dict:
        """恢复中断的工作流（HITL approve/rejected 后继续执行）

        Args:
            config: 与 run() 相同的 config

        Returns:
            继续执行后的状态字典
        """
        try:
            # 传入 None 表示使用 update_state 注入的值继续执行
            return self._app.invoke(None, config)
        except Exception as e:
            logger.error("工作流恢复失败: %s", e)
            return {"error": str(e)}

    def get_graph(self):
        """获取编译后的图对象（用于可视化）"""
        return self._app


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_workflow() -> RAGWorkflow:
    """获取 RAGWorkflow 单例"""
    return RAGWorkflow()
