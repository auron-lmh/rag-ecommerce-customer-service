"""多轮指代消解 + 省略补全 — 结合会话历史把追问改写为完整独立查询

行业痛点（百度千帆/腾讯云实测）:
  - 用户: "退货流程是什么？" → 追问: "那需要运费吗？"（省略主语"退货"）
  - 用户: "这款手机续航怎么样？" → 追问: "它支持快充吗？"（"它"指代不明）
  直接拿最后一句话检索召回率仅 ~62%，结合历史改写后可提升到 ~89%。

实现: LLM 结合最近几轮对话历史，将追问改写为完整独立 query。
  - 新话题 → 原样返回，不强行改写
  - 改写失败 → 降级用原 query（retrieval_judge 同款降级策略）
"""

import logging
from typing import Optional

from src.engineering.llm_client import get_llm_client

logger = logging.getLogger(__name__)

# 参与改写的历史轮数（滑动窗口，覆盖大部分指代/省略场景即可）
MAX_HISTORY_TURNS = 3

CORE_REFERENCE_PROMPT = """你是电商客服查询改写器，负责多轮对话的指代消解与省略补全。

对话历史:
{history}

会话记忆（实体/摘要/历史片段）:
{memory_context}

用户最新问题: {query}

改写规则:
1. 结合对话历史和会话记忆，把用户问题补全为"完整、独立、语义明确"的检索查询
2. 处理指代（它/这个/那个/这）和省略（如 "那需要运费吗" → "退货需要运费吗"）
3. **跨轮指代**: 若用户说"上次那个券/那个订单"等，从会话记忆中定位具体实体
   （如"上次那个券" → "满300减50券"）
4. 若用户开启了新话题（与历史无关），直接原样输出用户问题，不要强行改写
5. 只输出改写后的一句话，不要解释、不要加引号、不要 Markdown 标记

改写结果:"""


class CoreferenceResolver:
    """指代消解器

    使用方式:
        resolver = CoreferenceResolver()
        completed = resolver.resolve("那需要运费吗？", history)
        completed = resolver.resolve("上次那个券", history, memory_context)
    """

    def resolve(
        self,
        query: str,
        history: list[dict],
        memory_context: str = "",
    ) -> str:
        """结合会话历史 + 三层记忆补全查询

        Args:
            query: 用户最新问题
            history: 对话历史 [{"role": "user"/"assistant", "content": "..."}]
            memory_context: 会话记忆上下文（实体ledger/滚动摘要/历史片段），
                            用于解析"上次那个券"这类跨轮指代

        Returns:
            补全后的独立查询；改写失败/无历史时返回原 query
        """
        if not query:
            return query

        # 只取最近几轮，控制 token
        history_text = ""
        if history:
            recent = history[-MAX_HISTORY_TURNS * 2 :]
            history_text = "\n".join(
                f"{m.get('role', 'user')}: {str(m.get('content', ''))[:200]}"
                for m in recent
            )

        if not history_text and not memory_context:
            return query

        try:
            client = get_llm_client()
            completed = client.chat_with_fallback(
                messages=[
                    {
                        "role": "user",
                        "content": CORE_REFERENCE_PROMPT.format(
                            history=history_text or "（无）",
                            memory_context=memory_context or "（无）",
                            query=query,
                        ),
                    }
                ],
                fallback_value=query,
                temperature=0.1,
                max_tokens=150,
                timeout=10,
            )
            completed = completed.strip().strip('"').strip("'")
            # 防止改写为空或异常长
            if not completed or len(completed) > 200:
                return query
            from src.engineering.pii_redactor import redact_text

            safe_query, _ = redact_text(query)
            logger.info("指代消解: %s → %s", safe_query[:40], completed[:60])
            return completed
        except Exception as e:
            logger.warning("指代消解失败，使用原 query: %s", e)
            return query


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_coreference_resolver() -> CoreferenceResolver:
    """获取指代消解器单例"""
    return CoreferenceResolver()
