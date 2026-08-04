"""模块6.5: 流式输出 + 多轮对话管理 — SSE / 滑动窗口 / 智能重检索 / 人工介入

使用:
    from src.conversation import get_session_manager, get_streaming_generator, get_human_handler
    manager = get_session_manager()
    session = manager.create_session()
"""

from .coreference import CoreferenceResolver, get_coreference_resolver
from .emotion import (
    EmotionDetector,
    EmotionLevel,
    EmotionResult,
    get_emotion_detector,
)
from .human_in_loop import HumanInLoopHandler, get_human_handler
from .memory import SessionMemory, get_session_memory, reset_memory
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
    "HumanInLoopHandler",
    "get_human_handler",
    "EmotionDetector",
    "EmotionLevel",
    "EmotionResult",
    "get_emotion_detector",
    "CoreferenceResolver",
    "get_coreference_resolver",
    "SessionMemory",
    "get_session_memory",
    "reset_memory",
]
