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

    def get_context_window(self, max_tokens: int = 6000) -> list[Message]:
        """获取上下文窗口（滑动窗口策略）"""
        if not self.messages:
            return []

        # 保留最近4轮原文
        recent = self.messages[-8:]  # 4轮 * 2条/轮

        # 更早的消息需要压缩
        older = self.messages[:-8]
        if not older:
            return recent

        # 返回最近消息（压缩在外部处理）
        return recent


@dataclass
class StreamEvent:
    """SSE 流式事件"""

    event: str  # token / done / error / sources
    data: str
    id: int = 0
