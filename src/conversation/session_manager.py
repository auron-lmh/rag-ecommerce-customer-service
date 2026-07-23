"""模块6.5 会话管理器 — 对话历史存储 + 上下文窗口管理

存储策略:
  - 热点: 内存 dict（当前活跃会话）
  - 持久化: SQLite（全量归档）
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import settings

from .models import ConversationSession, Message

logger = logging.getLogger(__name__)

# SQLite 数据库路径
DB_PATH = settings.data_dir / "conversations.db"


class SessionManager:
    """会话管理器

    使用方式:
        manager = SessionManager()
        session = manager.create_session()
        manager.add_message(session.session_id, Message(role="user", content="怎么退货？"))
        history = manager.get_history(session.session_id)
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or DB_PATH
        self._sessions: dict[str, ConversationSession] = {}
        self._init_db()

    def _init_db(self) -> None:
        """初始化 SQLite 数据库"""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    sources TEXT DEFAULT '[]',
                    faithfulness REAL DEFAULT 0.0,
                    intent TEXT DEFAULT '',
                    FOREIGN KEY (session_id) REFERENCES conversations(session_id)
                )
            """)
            conn.commit()

    def create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        """创建新会话"""
        sid = session_id or str(uuid.uuid4())[:8]
        session = ConversationSession(session_id=sid)
        self._sessions[sid] = session

        # 持久化到 SQLite
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO conversations (session_id, created_at, last_active) VALUES (?, ?, ?)",
                (sid, session.created_at.isoformat(), session.last_active.isoformat()),
            )
            conn.commit()

        logger.info("创建会话: %s", sid)
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """获取会话（优先内存，其次 SQLite）"""
        if session_id in self._sessions:
            return self._sessions[session_id]

        # 从 SQLite 加载
        return self._load_session(session_id)

    def _load_session(self, session_id: str) -> Optional[ConversationSession]:
        """从 SQLite 加载会话"""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM conversations WHERE session_id = ?", (session_id,)
            ).fetchone()

            if not row:
                return None

            session = ConversationSession(
                session_id=session_id,
                created_at=datetime.fromisoformat(row["created_at"]),
                last_active=datetime.fromisoformat(row["last_active"]),
            )

            # 加载消息
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()

            for r in rows:
                session.messages.append(
                    Message(
                        role=r["role"],
                        content=r["content"],
                        timestamp=datetime.fromisoformat(r["timestamp"]),
                        sources=json.loads(r["sources"]),
                        faithfulness=r["faithfulness"],
                        intent=r["intent"],
                    )
                )

            self._sessions[session_id] = session
            return session

    def add_message(self, session_id: str, message: Message) -> None:
        """添加消息到会话"""
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)

        session.add_message(message)

        # 持久化到 SQLite
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO messages (session_id, role, content, timestamp, sources, faithfulness, intent)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    message.role,
                    message.content,
                    message.timestamp.isoformat(),
                    json.dumps(message.sources),
                    message.faithfulness,
                    message.intent,
                ),
            )
            conn.execute(
                "UPDATE conversations SET last_active = ? WHERE session_id = ?",
                (datetime.now().isoformat(), session_id),
            )
            conn.commit()

    def get_history(self, session_id: str, max_turns: int = 10) -> list[Message]:
        """获取对话历史"""
        session = self.get_session(session_id)
        if not session:
            return []
        return session.get_recent_messages(max_turns)

    def get_context_messages(
        self, session_id: str, max_tokens: int = 6000
    ) -> list[Message]:
        """获取上下文窗口消息（滑动窗口策略）"""
        session = self.get_session(session_id)
        if not session:
            return []
        return session.get_context_window(max_tokens)

    def list_sessions(self, limit: int = 20) -> list[dict]:
        """列出最近的会话"""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY last_active DESC LIMIT ?",
                (limit,),
            ).fetchall()

            return [
                {
                    "session_id": r["session_id"],
                    "created_at": r["created_at"],
                    "last_active": r["last_active"],
                }
                for r in rows
            ]

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute(
                "DELETE FROM conversations WHERE session_id = ?", (session_id,)
            )
            conn.commit()

        self._sessions.pop(session_id, None)
        return True


# ── 模块级单例 ──

from src.engineering.singleton import singleton_factory


@singleton_factory
def get_session_manager() -> SessionManager:
    return SessionManager()
