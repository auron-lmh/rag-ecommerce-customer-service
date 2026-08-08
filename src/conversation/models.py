"""模块6.5 数据模型 — 对话管理"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """单条对话消息"""

    role: str  # user / assistant / system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    sources: list[str] = field(default_factory=list)  # 引用来源
    faithfulness: float = 0.0  # 忠实度分数
    intent: str = ""  # 意图分类


@dataclass
class ConversationSession:
    """对话会话"""

    session_id: str
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    user_id: str = (
        ""  # 模块33 会话归属用户（路由层用 "{username}:{session_id}" 命名空间隔离）
    )

    @property
    def turn_count(self) -> int:
        """对话轮数（一问一答算一轮）"""
        return len([m for m in self.messages if m.role == "user"])

    def add_message(self, message: Message) -> None:
        """添加消息"""
        self.messages.append(message)
        self.last_active = datetime.now()

    def get_recent_messages(self, n: int = 4) -> list[Message]:
        """获取最近 n 轮对话"""
        return self.messages[-n * 2 :] if self.messages else []

    def get_context_window(
        self, max_tokens: int = 6000, min_recent: int = 4
    ) -> list[Message]:
        """滑动窗口上下文 — 基于 token 估算保留尽可能多的消息

        策略:
          1. 始终保留最近 min_recent 条消息（保证基本上下文）
          2. 从最新消息向前累加，直到接近 max_tokens
          3. 超出部分丢弃（旧消息优先丢弃）

        Args:
            max_tokens: 最大 token 数（默认 6000，约为 8K 模型的 75%）
            min_recent: 最少保留最近消息数（默认 4 条=2 轮对话）

        Returns:
            上下文窗口内的消息列表
        """
        if not self.messages:
            return []

        recent = (
            self.messages[-min_recent:]
            if len(self.messages) >= min_recent
            else list(self.messages)
        )
        older = self.messages[:-min_recent] if len(self.messages) > min_recent else []

        if not older:
            return recent

        # 从最近到最远累加，直到接近 max_tokens
        token_budget = max_tokens - self._estimate_tokens(
            " ".join(m.content for m in recent)
        )
        if token_budget <= 0:
            return recent

        selected_older = []
        used = 0
        for msg in reversed(older):
            cost = self._estimate_tokens(msg.content)
            if used + cost <= token_budget:
                selected_older.append(msg)
                used += cost
            else:
                break

        # 还原时间顺序：older 部分 + recent
        selected_older.reverse()
        return selected_older + recent

    @staticmethod
    def _estimate_tokens(text: str, chars_per_token: float = 1.8) -> int:
        """估算文本的 token 数量

        中文为主时 chars_per_token ≈ 1.5~2.0，取 1.8 偏保守。
        返回 token 数，最小为 1。
        """
        if not text:
            return 0
        return max(1, int(len(text) / chars_per_token))


@dataclass
class StreamEvent:
    """SSE 流式事件"""

    event: str  # token / done / error / sources
    data: str
    id: int = 0
