"""模块6.5: 流式输出 + 多轮对话管理 — SSE / 滑动窗口 / 智能重检索

使用:
    from src.conversation import get_session_manager, get_streaming_generator
    manager = get_session_manager()
    session = manager.create_session()
"""

from .models import ConversationSession, Message, StreamEvent
from .retrieval_judge import RetrievalJudge, get_retrieval_judge
from .session_manager import SessionManager, get_session_manager
from .streaming import StreamingGenerator, get_streaming_generator

__all__ = [
    "ConversationSession",
    "Message",
    "StreamEvent",
    "SessionManager",
    "get_session_manager",
    "StreamingGenerator",
    "get_streaming_generator",
    "RetrievalJudge",
    "get_retrieval_judge",
]
