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
    history: list  # 会话历史（多轮指代消解用）
    memory_context: str  # 会话记忆（实体ledger/滚动摘要/历史片段）
    access_level: str = "public"  # 模块33 内容权限等级（检索过滤用，fail-safe 最低）

    # 意图分类结果
    intent: str
    confidence: float
    target: str
    rewritten_query: str
    reasoning: str
    entities: dict  # 分类器提取的实体（订单号/商品名/快递单号）

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

    # 情绪识别（新增）
    emotion: str  # calm / dissatisfied / angry / extreme
    emotion_confidence: float

    # 人工介入
    needs_human: bool
    human_reason: str
    human_priority: str
    human_decision: str  # "approve" | "rejected" | "" (由外部注入)
    handoff_payload: dict  # 转人工交接包（摘要/实体/情绪/已尝试动作）

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
        "entities": route_result.intent_result.entities,
    }


def check_human_needed(state: RAGState) -> dict:
    """节点2: 人工介入预判（含情绪识别，改进: 愤怒/极端升级人工）

    行业实践: 情绪极端（辱骂/威胁/法律）直接升级人工；
    愤怒 + 退款/投诉 → 压缩提问轮次、优先转人工，避免机器人激化矛盾。
    """
    logger.info("[节点] check_human_needed")

    from src.conversation import get_emotion_detector

    detector = get_emotion_detector()
    emotion_result = detector.detect(state["query"])
    emotion = emotion_result.level.value

    handler = get_human_handler()
    check = handler.check_needs_human(
        query=state["query"],
        intent=state["intent"],
        confidence=state["confidence"],
        emotion=emotion,
    )

    return {
        "needs_human": check["needs_human"],
        "human_reason": check["reason"],
        "human_priority": check["priority"],
        "emotion": emotion,
        "emotion_confidence": emotion_result.confidence,
    }


def retrieve_docs(state: RAGState) -> dict:
    """节点3: 双路召回 + 多级降级检索

    双路召回（行业实践两步检索，召回率+30%）:
      原始问题（保真度兜底） + 改写后问题（专业术语/指代消解）并行召回 → 合并去重。
      改写偏离时原始问题仍能命中，避免"改写错就全错"。

    辅助增强:
      - 指代消解: 结合会话历史补全追问（"那需要运费吗"→"退货需要运费吗"）
      - 商品实体: 双路都拼上商品名（解决"商品定位难"）
    """
    original_query = state["query"]
    rewritten = state["rewritten_query"]

    # 指代消解: 补全改写后的追问（含三层记忆，解析"上次那个券"类跨轮指代）
    history = state.get("history") or []
    memory_context = state.get("memory_context") or ""
    if history or memory_context:
        from src.conversation import get_coreference_resolver

        rewritten = get_coreference_resolver().resolve(
            rewritten, history, memory_context
        )

    # 商品实体: 双路都拼上商品名（定位具体商品）
    product_name = (state.get("entities", {}) or {}).get("product_name") or ""
    if product_name:
        if product_name not in original_query:
            original_query = f"{product_name} {original_query}"
        if product_name not in rewritten:
            rewritten = f"{product_name} {rewritten}"
    logger.info(
        "[节点] retrieve_docs, 双路召回: [原始]%s || [改写]%s",
        original_query[:40],
        rewritten[:40],
    )

    from src.embedding.retriever import get_retriever

    retriever = get_retriever()
    strategy = get_degradation_strategy(retriever)

    result = strategy.search_with_degradation(
        query=original_query,
        secondary_query=rewritten,
        top_k=state.get("top_k", 5),
        use_rerank=state.get("use_reranker", True),
        access_level=state.get("access_level", "public"),
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

    # 模块33: 空 docs 兜底会触发 generate_with_correction 内部再检索，
    # 必须透传 access_level —— 否则受限用户在"检索空→自行重搜"时无过滤漏检索（头号隐性泄漏）
    access_level = state.get("access_level", "public")

    if not docs_texts:
        # 降级：上游检索为空，走完整检索流程
        result = corrector.generate_with_correction(
            query=state["rewritten_query"],
            top_k=state.get("top_k", 5),
            use_rerank=state.get("use_reranker", True),
            access_level=access_level,
        )
    else:
        result = corrector.generate_with_docs(
            query=state["rewritten_query"],
            docs=docs_texts,
            sources=sources,
            top_k=state.get("top_k", 5),
            use_rerank=state.get("use_reranker", True),
            access_level=access_level,
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
      1. faithfulness ≥ 0.7 → 通过；含高敏承诺（价格/退款/政策）→ 需 ≥0.85
      2. 回答包含 "无法确认" / "建议咨询" → 标记为需要人工
      3. 检索质量差（degradation_level ≥ 4）→ 标记为需要人工

    高敏承诺护栏（改进）: 行业最大事故源是"AI 瞎承诺政策/价格/退款"
    （跨境卖家案例: AI 承诺7天无理由实际15天，亏损十几万）。
    回答含价格/退款/政策承诺时提高忠实度门槛，不达标强制转人工。
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

    # 高敏承诺检测: 含价格/退款/政策承诺 → 要求更高忠实度（0.85）
    from src.engineering.promise_guard import (
        HIGH_STAKE_FAITHFULNESS,
        detect_high_stakes,
    )

    high_stake_cats = detect_high_stakes(answer)
    min_faithfulness = HIGH_STAKE_FAITHFULNESS if high_stake_cats else 0.7

    # 低忠实度关键词
    uncertain_phrases = ["无法确认", "不确定", "没有找到", "建议咨询", "建议您咨询"]

    has_uncertain = any(phrase in answer for phrase in uncertain_phrases)
    quality_poor = faithfulness < min_faithfulness or degradation_level >= 4

    if loop_count >= MAX_LOOP_COUNT:
        # 已达最大循环次数，强制通过
        # 修复: 含高敏承诺(价格/退款/政策)且忠实度不足时，不能无条件放行——转人工核验
        if high_stake_cats and faithfulness < min_faithfulness:
            logger.warning(
                "已达循环上限但含高敏承诺(%s)且忠实度不足(%.2f)，转人工核验",
                ",".join(high_stake_cats),
                faithfulness,
            )
            return {"evaluation_score": faithfulness, "evaluation_passed": False}
        logger.warning("已达最大循环次数 %d，强制通过评估", MAX_LOOP_COUNT)
        return {
            "evaluation_score": faithfulness,
            "evaluation_passed": True,
        }

    if quality_poor or has_uncertain:
        reason_parts = []
        if high_stake_cats:
            reason_parts.append(f"高敏承诺需核验({','.join(high_stake_cats)})")
        if faithfulness < min_faithfulness:
            reason_parts.append(f"忠实度不足({faithfulness:.2f}<{min_faithfulness})")
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


def _build_handoff_payload(state: RAGState) -> dict:
    """转人工交接包（行业实践: 升级后不得要求用户重复描述）

    包含: 对话摘要/记忆 + 已确认实体 + 情绪等级 + 系统已尝试动作 + 未解决原因。
    人工坐席拿包直接接手，无需用户重讲诉求。
    """
    entities = state.get("entities", {}) or {}
    return {
        "user_query": state.get("query", ""),
        "intent": state.get("intent", ""),
        "emotion": state.get("emotion", "calm"),
        "entities": {k: v for k, v in entities.items() if v},
        "memory_summary": (state.get("memory_context") or "")[:500],
        "attempted_actions": (
            f"degradation_level={state.get('degradation_level', 1)}, "
            f"correction_rounds={state.get('correction_rounds', 0)}"
        ),
        "unresolved_reason": state.get("human_reason", ""),
    }


def handle_human(state: RAGState) -> dict:
    """节点8: 人工介入处理（高风险场景 + 情绪安抚分支）

    情绪 angry/extreme → 用"安抚 + 优先转人工"话术（行业实践: 愤怒用户
    缺的不是表演式共情，而是别再让他重复操作、尽快升级到真人）。
    附带转人工交接包（对话摘要/实体/情绪/已尝试动作）。
    """
    logger.info("[节点] handle_human, reason=%s", state.get("human_reason", ""))

    handler = get_human_handler()
    query = state["query"]
    emotion = state.get("emotion", "calm")

    # 情绪分支：愤怒/极端 → 安抚 + 优先升级
    if emotion in ("angry", "extreme"):
        template = handler.get_human_response_template("high_emotion")
    else:
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
        "handoff_payload": _build_handoff_payload(state),
    }


def handle_sql(state: RAGState) -> dict:
    """节点9: 订单/物流查询（工具调用）——RAG + 工具 + 转人工 混合架构

    改进1: 从预留 stub 升级为真实工具查询:
      1. 从分类实体取订单号/快递单号
      2. 调用订单服务（mock 数据库）查询真实状态 → 返回格式化回答
      3. 未命中/无单号 → 提示 + 转人工
    生产环境: 将 OrderService 替换为真实订单库 / 快递鸟/菜鸟物流 API。
    """
    logger.info("[节点] handle_sql, entities=%s", state.get("entities", {}))

    from src.orders.order_service import get_order_service

    entities = state.get("entities", {}) or {}
    order_id = entities.get("order_id") or ""
    tracking_number = entities.get("tracking_number") or ""

    service = get_order_service()
    reply, found = service.reply_for(order_id, tracking_number)

    if found:
        return {"answer": reply, "needs_human": False}

    # 未命中工具 → 提示 + 转人工（附交接包）
    return {
        "answer": (
            reply
            or "您的订单/物流查询需要订单号或快递单号，请提供后我们为您查询最新状态。"
        ),
        "needs_human": True,
        "human_reason": "订单/物流实时查询未命中工具结果，需人工跟进",
        "human_priority": "medium",
        "handoff_payload": _build_handoff_payload(state),
    }


def handle_policy(state: RAGState) -> dict:
    """节点10: 退货/换货结构化政策（RAG + 工具 混合架构的"政策工具"）

    退货窗口/运费规则/退款时效/质量争议等定义清晰的政策问题，
    从结构化政策数据直接答——准确、不产生幻觉（退货是 AI 客服持续薄弱点，
    通用 FAQ 答不准；政策变更只改数据）。
    """
    logger.info("[节点] handle_policy, query=%s", state.get("query", "")[:40])

    from src.business.return_policy import get_return_policy

    service = get_return_policy()
    reply, found = service.answer(state.get("query", ""))

    if found:
        return {"answer": reply, "needs_human": False}

    # 未命中（应不会走到，防御）→ 走 RAG 兜底
    return {"answer": "", "needs_human": False}


def handle_direct(state: RAGState) -> dict:
    """节点11: 直接回复（闲聊场景）"""
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
    """条件边: 根据意图路由

    退货/换货意图 + 命中结构化政策子场景（窗口/运费/时效/质量）→ "policy" 节点，
    从结构化政策直接答（准确、零幻觉）；未命中则走 RAG 知识库。
    """
    target = state.get("target", "rag")

    if state.get("needs_human", False):
        return "human"

    if target in ("rag", "hybrid"):
        # 退货结构化政策优先（定义清晰的政策问题不用 RAG 猜）
        if state.get("intent") == "return_refund":
            from src.business.return_policy import get_return_policy

            if get_return_policy().detect_sub_scenario(state.get("query", "")):
                return "policy"
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
    workflow.add_node("policy", handle_policy)  # 新增: 退货结构化政策工具
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
            "policy": "policy",
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
    workflow.add_edge("policy", END)
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
        history: list | None = None,
        memory_context: str = "",
        access_level: str = "public",
    ) -> dict:
        """运行工作流（支持 Human-in-the-Loop 中断）

        Args:
            query: 用户查询
            session_id: 会话ID
            top_k: 检索结果数
            use_reranker: 是否启用 Reranker
            config: LangGraph config（含 thread_id 用于 HITL）
            history: 会话历史 [{"role": "user"/"assistant", "content": "..."}]
                    用于多轮指代消解（可为空）
            memory_context: 会话记忆上下文（实体ledger/滚动摘要/历史片段），
                    解析"上次那个券"类跨轮指代
            access_level: 模块33 内容权限等级（检索过滤用，fail-safe 最低）

        Returns:
            状态字典。如果图中断，会包含 "__interrupt__" 标记
        """
        initial_state = {
            "query": query,
            "session_id": session_id,
            "top_k": top_k,
            "use_reranker": use_reranker,
            "history": history or [],
            "memory_context": memory_context or "",
            "access_level": access_level,
            "intent": "",
            "confidence": 0.0,
            "target": "",
            "rewritten_query": query,
            "reasoning": "",
            "entities": {},
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
            "emotion": "calm",
            "emotion_confidence": 0.0,
            "needs_human": False,
            "human_reason": "",
            "human_priority": "",
            "human_decision": "",
            "handoff_payload": {},
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
