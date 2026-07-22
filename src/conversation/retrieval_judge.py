"""模块6.5 智能重检索判断 — 判断是否需要重新检索

规则:
  - 追问细节（"那XX呢"）→ 不重检索，用已有上下文
  - 切换话题（"那退货怎么退"）→ 重新检索
  - 澄清问题（"不是这个意思，我是说..."）→ 改写 query 重检索
"""

import json
import logging
from typing import Optional

import requests

from src.config import settings

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
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model or settings.default_model
        self._api_key = api_key or settings.deepseek_api_key
        self._base_url = base_url or settings.deepseek_base_url

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
        except Exception as e:
            logger.warning("重检索判断失败，默认需要检索: %s", e)
            return True, "判断失败，默认检索"

    def _call_llm(self, query: str, history: list[dict]) -> tuple[bool, str]:
        """调用 LLM 判断"""
        # 只取最近3轮
        recent = history[-6:]
        history_text = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in recent)

        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": JUDGE_PROMPT.format(
                            history=history_text,
                            query=query,
                        ),
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 200,
            },
            timeout=10,
        )
        resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"].strip()
        # 提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content)
        return bool(data.get("need_retrieval", True)), data.get("reason", "")


# ── 模块级单例 ──

_judge_instance: Optional[RetrievalJudge] = None


def get_retrieval_judge() -> RetrievalJudge:
    global _judge_instance
    if _judge_instance is None:
        _judge_instance = RetrievalJudge()
    return _judge_instance
