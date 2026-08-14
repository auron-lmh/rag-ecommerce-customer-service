"""模块6.5 智能重检索判断 — 判断是否需要重新检索

规则:
  - 追问细节（"那XX呢"）→ 不重检索，用已有上下文
  - 切换话题（"那退货怎么退"）→ 重新检索
  - 澄清问题（"不是这个意思，我是说..."）→ 改写 query 重检索
"""

import json
import logging
from typing import Optional

from src.engineering.llm_client import LLMClient, LLMClientError, get_llm_client

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """判断用户的新问题是否需要重新检索知识库。

对话历史:
{history}

用户新问题: {query}

判断规则:
1. 如果是追问细节（如"那XX呢"、"具体怎么操作"），返回 false（用已有上下文）
2. 如果是切换话题（如"那退货怎么退"、"XX商品怎么样"），返回 true（需要重新检索）
3. 如果是澄清问题（如"不是这个意思"、"我是说..."），返回 true（需要重新检索）

输出JSON格式:
{{"need_retrieval": true, "reason": "切换到新话题"}}
"""


class RetrievalJudge:
    """智能重检索判断器

    使用方式:
        judge = RetrievalJudge()
        need = judge.should_retrieve("那具体怎么操作", history)
    """

    def __init__(
        self,
        client: Optional[LLMClient] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        if client is not None:
            self._client = client
        elif model or api_key or base_url:
            self._client = LLMClient(model=model, api_key=api_key, base_url=base_url)
        else:
            self._client = get_llm_client()

    def should_retrieve(self, query: str, history: list[dict]) -> tuple[bool, str]:
        """判断是否需要重新检索

        Args:
            query: 用户新问题
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]

        Returns:
            (need_retrieval, reason)
        """
        if not history:
            return True, "无对话历史，需要检索"

        try:
            return self._call_llm(query, history)
        except (LLMClientError, json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("重检索判断失败，默认需要检索: %s", e)
            return True, "判断失败，默认检索"

    def _call_llm(self, query: str, history: list[dict]) -> tuple[bool, str]:
        """调用 LLM 判断"""
        # 只取最近3轮
        recent = history[-6:]
        history_text = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in recent)

        content = self._client.chat(
            messages=[
                {
                    "role": "user",
                    "content": JUDGE_PROMPT.format(
                        history=history_text,
                        query=query,
                    ),
                }
            ],
            temperature=0.1,
            max_tokens=200,
            timeout=10,
        )

        # 提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())
        return bool(data.get("need_retrieval", True)), data.get("reason", "")


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_retrieval_judge() -> RetrievalJudge:
    return RetrievalJudge()
