"""模块6.5 流式生成器 — SSE (Server-Sent Events) 流式输出

基于统一 LLMClient 实现流式生成，自动支持异步/同步双模式。

使用:
    generator = StreamingGenerator()
    async for event in generator.stream_generate(query, docs):
        print(event.data)
"""

import logging
from collections.abc import AsyncGenerator
from typing import Optional

from src.engineering.llm_client import LLMClientError, get_llm_client

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
    """流式生成器 — 基于 LLMClient 的 RAG 专用流式封装

    使用方式:
        generator = StreamingGenerator()
        async for event in generator.stream_generate(query, docs):
            if event.event == "token":
                print(event.data, end="")
    """

    def __init__(self):
        self._client = get_llm_client()

    def _build_messages(
        self,
        query: str,
        docs: list[str],
        session_history: Optional[list[dict]] = None,
    ) -> list[dict]:
        """构建 RAG prompt 消息"""
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
        return messages

    async def stream_generate(
        self,
        query: str,
        docs: list[str],
        session_history: Optional[list[dict]] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """流式生成回答（真正的异步 SSE，委托给 LLMClient）"""
        messages = self._build_messages(query, docs, session_history)

        try:
            event_id = 0
            async for token in self._client.achat_stream(
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
                timeout=60,
            ):
                event_id += 1
                yield StreamEvent(event="token", data=token, id=event_id)

            yield StreamEvent(event="done", data="[DONE]", id=event_id)

        except LLMClientError as e:
            logger.error("流式生成失败: %s", e)
            yield StreamEvent(event="error", data=str(e))

    async def generate_async(
        self,
        query: str,
        docs: list[str],
        session_history: Optional[list[dict]] = None,
    ) -> str:
        """非流式生成（异步版本 — 委托给 LLMClient）"""
        messages = self._build_messages(query, docs, session_history)
        return await self._client.achat_with_fallback(
            messages=messages,
            fallback_value="抱歉，生成回答时出现错误，请稍后重试。",
            temperature=0.3,
            max_tokens=1024,
            timeout=60,
        )

    def generate(
        self,
        query: str,
        docs: list[str],
        session_history: Optional[list[dict]] = None,
    ) -> str:
        """非流式生成（同步版本 — 委托给 LLMClient）"""
        messages = self._build_messages(query, docs, session_history)
        return self._client.chat_with_fallback(
            messages=messages,
            fallback_value="抱歉，生成回答时出现错误，请稍后重试。",
            temperature=0.3,
            max_tokens=1024,
            timeout=30,
        )

    async def close(self) -> None:
        """关闭底层 LLMClient 的异步连接"""
        await self._client.close()


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_streaming_generator() -> StreamingGenerator:
    """获取 StreamingGenerator 单例"""
    return StreamingGenerator()
