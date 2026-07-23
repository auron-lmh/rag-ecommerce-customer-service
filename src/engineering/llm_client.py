"""统一 LLM API 客户端 — 消除代码中 18 处重复的 requests.post 调用

所有模块通过此客户端调用 LLM，统一处理:
  - 认证 header 构建
  - 超时 + 重试
  - 错误处理 + 降级
  - 同步/异步双模式
  - JSON 响应解析

使用:
    from src.engineering.llm_client import get_llm_client

    client = get_llm_client()

    # 同步调用
    answer = client.chat([{"role": "user", "content": "你好"}])
    data = client.chat_json([{"role": "user", "content": "输出JSON: ..."}])

    # 异步调用
    answer = await client.achat([{"role": "user", "content": "你好"}])
    async for token in client.achat_stream([{"role": "user", "content": "..."}]):
        print(token)
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

# 默认重试配置
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_DELAY = 1.0  # 秒


class LLMClient:
    """统一的 LLM API 客户端

    自动从 settings 读取配置，也可通过构造函数覆盖。

    特性:
      - 同步 chat() / chat_json()
      - 异步 achat() / achat_stream()
      - 自动重试（429 限流 + 5xx 服务端错误）
      - 超时控制
      - JSON 自动提取（处理 markdown 包裹）
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.model = model or settings.default_model
        self._api_key = api_key or settings.deepseek_api_key
        self._base_url = base_url or settings.deepseek_base_url
        self._max_retries = max_retries
        self._sync_client: Optional[httpx.Client] = None  # 同步客户端
        self._async_client: Optional[httpx.AsyncClient] = None  # 异步客户端

    # ── 公共 API ──

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: int = 30,
        tools: Optional[list] = None,
        tool_choice: Optional[dict] = None,
    ) -> str:
        """同步调用 LLM，返回文本回答

        当传入 tools 参数时，启用 function calling 模式，
        返回 tool_calls 中第一个 function 的 arguments JSON 字符串。

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度 (0~2)
            max_tokens: 最大输出 token 数
            timeout: 请求超时 (秒)
            tools: Function Calling 工具定义列表
            tool_choice: 工具选择策略

        Returns:
            LLM 生成的文本（或 function calling 的 arguments）

        Raises:
            LLMClientError: 所有重试失败后抛出
        """
        return self._call_with_retry(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            tools=tools,
            tool_choice=tool_choice,
        )

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        timeout: int = 30,
    ) -> dict:
        """同步调用 LLM，返回解析后的 JSON 对象

        自动处理 markdown 代码块包裹（```json ... ```）。

        Args:
            messages: 消息列表
            temperature: 温度
            max_tokens: 最大输出 token 数
            timeout: 请求超时 (秒)

        Returns:
            解析后的 JSON dict

        Raises:
            LLMClientError: 调用失败或 JSON 解析失败
        """
        raw = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return self._extract_json(raw)

    def chat_with_fallback(
        self,
        messages: list[dict],
        fallback_value: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: int = 30,
    ) -> str:
        """同步调用 LLM，失败时返回 fallback_value（不抛异常）"""
        try:
            return self.chat(messages, temperature, max_tokens, timeout)
        except LLMClientError as e:
            logger.warning("LLM 调用失败，使用降级值: %s", e)
            return fallback_value

    def chat_json_with_fallback(
        self,
        messages: list[dict],
        fallback_value: Optional[dict] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        timeout: int = 30,
    ) -> Optional[dict]:
        """同步调用 LLM JSON，失败时返回 fallback_value"""
        try:
            return self.chat_json(messages, temperature, max_tokens, timeout)
        except LLMClientError as e:
            logger.warning("LLM JSON 调用失败，使用降级值: %s", e)
            return fallback_value

    # ── 异步 API ──

    async def achat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: int = 60,
    ) -> str:
        """异步调用 LLM，返回文本回答"""
        client = await self._get_async_client()

        try:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=httpx.Timeout(timeout),
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()

        except httpx.TimeoutException:
            raise LLMClientError(f"异步调用超时 ({timeout}s)")
        except httpx.HTTPStatusError as e:
            raise LLMClientError(f"HTTP {e.response.status_code}")
        except Exception as e:
            raise LLMClientError(str(e))

    async def achat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: int = 60,
    ) -> AsyncGenerator[str, None]:
        """异步流式调用 LLM，逐 token yield"""
        client = await self._get_async_client()

        try:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
                timeout=httpx.Timeout(timeout),
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

        except httpx.TimeoutException:
            raise LLMClientError(f"流式调用超时 ({timeout}s)")
        except httpx.HTTPStatusError as e:
            raise LLMClientError(f"流式 HTTP {e.response.status_code}")
        except Exception as e:
            raise LLMClientError(str(e))

    async def achat_with_fallback(
        self,
        messages: list[dict],
        fallback_value: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        timeout: int = 60,
    ) -> str:
        """异步调用 LLM，失败时返回 fallback_value"""
        try:
            return await self.achat(messages, temperature, max_tokens, timeout)
        except LLMClientError as e:
            logger.warning("异步 LLM 调用失败，使用降级值: %s", e)
            return fallback_value

    # ── 内部实现 ──

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _call_with_retry(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        timeout: int,
        tools: Optional[list] = None,
        tool_choice: Optional[dict] = None,
    ) -> str:
        """带重试的同步调用"""
        last_error = None

        for attempt in range(self._max_retries + 1):
            try:
                return self._do_call(
                    messages, temperature, max_tokens, timeout, tools, tool_choice
                )
            except LLMClientError as e:
                last_error = e
                is_retryable = self._is_retryable(e)

                if attempt < self._max_retries and is_retryable:
                    delay = DEFAULT_RETRY_DELAY * (2**attempt)
                    logger.warning(
                        "LLM 调用重试 %d/%d (%.1fs 后): %s",
                        attempt + 1,
                        self._max_retries,
                        delay,
                        e,
                    )
                    time.sleep(delay)
                elif attempt < self._max_retries:
                    # 不可重试的错误，不等待
                    logger.warning(
                        "LLM 调用失败 (不可重试) %d/%d: %s",
                        attempt + 1,
                        self._max_retries,
                        e,
                    )
                else:
                    logger.error("LLM 调用 %d 次后仍失败: %s", self._max_retries + 1, e)

        raise last_error or LLMClientError("未知错误")

    def _do_call(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        timeout: int,
        tools: Optional[list] = None,
        tool_choice: Optional[dict] = None,
    ) -> str:
        """执行单次同步调用（统一使用 httpx.Client）"""
        try:
            body: dict = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools is not None:
                body["tools"] = tools
            if tool_choice is not None:
                body["tool_choice"] = tool_choice

            client = self._get_sync_client()
            resp = client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=body,
                timeout=httpx.Timeout(timeout),
            )

            if resp.status_code == 429:
                raise LLMClientError("429 Too Many Requests", status_code=429)
            if resp.status_code >= 500:
                raise LLMClientError(
                    f"Server error {resp.status_code}", status_code=resp.status_code
                )

            resp.raise_for_status()
            message = resp.json()["choices"][0]["message"]

            # Function Calling 模式：返回 tool_calls 的 arguments
            if "tool_calls" in message and message["tool_calls"]:
                return message["tool_calls"][0]["function"]["arguments"]

            return (message.get("content") or "").strip()

        except httpx.TimeoutException:
            raise LLMClientError(f"请求超时 ({timeout}s)")
        except httpx.ConnectError as e:
            raise LLMClientError(f"连接失败: {e}")
        except LLMClientError:
            raise
        except Exception as e:
            raise LLMClientError(str(e))

    @staticmethod
    def _is_retryable(error: "LLMClientError") -> bool:
        """判断错误是否可重试"""
        code = error.status_code
        if code == 429:
            return True  # 限流
        if code and code >= 500:
            return True  # 服务端错误
        if "timeout" in str(error).lower() or "超时" in str(error):
            return True
        if "connection" in str(error).lower() or "连接" in str(error):
            return True
        return False

    @staticmethod
    def _extract_json(raw: str) -> dict:
        """从 LLM 返回的文本中提取 JSON"""
        content = raw.strip()
        # 处理 markdown 代码块
        if "```json" in content:
            content = content.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMClientError(f"JSON 解析失败: {e}\n原文: {raw[:200]}")

    # ── httpx Client 管理 ──

    def _get_sync_client(self) -> httpx.Client:
        """获取或创建复用的 httpx Client（同步）"""
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client()
        return self._sync_client

    async def _get_async_client(self) -> httpx.AsyncClient:
        """获取或创建复用的 httpx AsyncClient（异步）"""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient()
        return self._async_client

    def close_sync(self) -> None:
        """关闭同步客户端"""
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()
            self._sync_client = None

    async def close(self) -> None:
        """关闭异步客户端"""
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()
            self._async_client = None


class LLMClientError(Exception):
    """LLM 客户端异常"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


# ── 模块级单例 ──

import threading

_client_instance: Optional[LLMClient] = None
_lock = threading.Lock()


def get_llm_client(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMClient:
    """获取 LLMClient 单例

    首次调用使用默认配置，后续调用返回同一个实例。
    如需自定义配置，在首次调用时传入参数。
    """
    global _client_instance
    if _client_instance is None:
        with _lock:
            if _client_instance is None:
                _client_instance = LLMClient(
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                )
    return _client_instance


def reset_llm_client() -> None:
    """重置 LLMClient 单例（测试用）"""
    global _client_instance
    _client_instance = None
