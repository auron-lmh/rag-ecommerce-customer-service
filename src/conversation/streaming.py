"""模块6.5 流式生成器 — SSE (Server-Sent Events) 流式输出

使用:
    generator = StreamingGenerator()
    async for event in generator.stream_generate(query, docs):
        print(event.data)
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Optional

import requests

from src.config import settings

from .models import StreamEvent

logger = logging.getLogger(__name__)

# 生成 System Prompt
STREAM_PROMPT = """你是一个电商客服助手。请基于以下参考文档回答用户问题。

规则:
1. 只基于提供的文档内容回答，不要编造信息
2. 如果文档中没有相关信息，请明确说"根据已有信息无法确认"
3. 每个回答附引用来源，格式: [1][2]...
4. 回答要简洁、专业、有帮助

参考文档:
{context}

用户问题: {query}"""


class StreamingGenerator:
    """流式生成器 — SSE 输出

    使用方式:
        generator = StreamingGenerator()
        async for event in generator.stream_generate(query, docs):
            if event.event == "token":
                print(event.data, end="")
            elif event.event == "done":
                print("\n完成")
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

    async def stream_generate(
        self,
        query: str,
        docs: list[str],
        session_history: Optional[list[dict]] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """流式生成回答

        Args:
            query: 用户查询
            docs: 参考文档列表
            session_history: 对话历史（可选）

        Yields:
            StreamEvent
        """
        context = "\n\n".join(f"[文档{i+1}] {d[:800]}" for i, d in enumerate(docs[:5]))

        messages = []
        if session_history:
            messages.extend(session_history[-6:])  # 最近3轮
        messages.append(
            {
                "role": "user",
                "content": STREAM_PROMPT.format(context=context, query=query),
            }
        )

        try:
            resp = requests.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 1024,
                    "stream": True,
                },
                stream=True,
                timeout=60,
            )
            resp.raise_for_status()

            event_id = 0
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        yield StreamEvent(event="done", data="[DONE]", id=event_id)
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            event_id += 1
                            yield StreamEvent(event="token", data=content, id=event_id)
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.error("流式生成失败: %s", e)
            yield StreamEvent(event="error", data=str(e))

    def generate(
        self,
        query: str,
        docs: list[str],
        session_history: Optional[list[dict]] = None,
    ) -> str:
        """非流式生成（同步版本）"""
        context = "\n\n".join(f"[文档{i+1}] {d[:800]}" for i, d in enumerate(docs[:5]))

        messages = []
        if session_history:
            messages.extend(session_history[-6:])
        messages.append(
            {
                "role": "user",
                "content": STREAM_PROMPT.format(context=context, query=query),
            }
        )

        try:
            resp = requests.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 1024,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error("生成失败: %s", e)
            return "抱歉，生成回答时出现错误，请稍后重试。"


# ── 模块级单例 ──

_generator_instance: Optional[StreamingGenerator] = None


def get_streaming_generator() -> StreamingGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = StreamingGenerator()
    return _generator_instance
