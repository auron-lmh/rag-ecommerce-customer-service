"""模块33 会话按用户隔离 — 路由层命名空间 + 会话归属 user_id

隔离机制: 路由层用 "{username}:{session_id}" 命名空间，
用户 A 永远只能触达 "alice:*" 前缀的 key，天然隔离历史/记忆。
"""

import pytest

from src.conversation.models import ConversationSession, Message
from src.conversation.session_manager import SessionManager


@pytest.fixture
def manager(tmp_path):
    return SessionManager(db_path=tmp_path / "test_conversations.db")


class TestSessionUser:
    def test_create_session_binds_user(self, manager):
        s = manager.create_session("alice:chat1", user_id="alice")
        assert s.user_id == "alice"
        assert s.session_id == "alice:chat1"

    def test_namespaced_sessions_do_not_cross(self, manager):
        """同名 session_id，不同用户前缀 → 完全隔离"""
        s_alice = manager.create_session("alice:chat1", user_id="alice")
        s_bob = manager.create_session("bob:chat1", user_id="bob")

        manager.add_message(
            s_alice.session_id, Message(role="user", content="我的私密问题")
        )
        manager.add_message(s_bob.session_id, Message(role="user", content="普通问题"))

        reloaded_alice = manager.get_session("alice:chat1")
        reloaded_bob = manager.get_session("bob:chat1")

        assert len(reloaded_alice.messages) == 1
        assert reloaded_alice.messages[0].content == "我的私密问题"
        assert reloaded_bob.messages[0].content == "普通问题"

    def test_session_roundtrip_persists_user_id(self, manager):
        """SQLite 回读保留 user_id"""
        manager.create_session("alice:chat1", user_id="alice")
        reloaded = manager.get_session("alice:chat1")
        assert reloaded.user_id == "alice"

    def test_create_session_default_empty_user(self, manager):
        s = manager.create_session("legacy:1")
        assert s.user_id == ""


class TestNamespacingHelper:
    def test_namespaced_key_format(self):
        # 与路由层 sid = f"{username}:{session_id}" 一致
        username, session_id = "alice", "chat1"
        assert f"{username}:{session_id}" == "alice:chat1"

    def test_conversation_session_type(self, manager):
        s = manager.create_session("alice:chat1", user_id="alice")
        assert isinstance(s, ConversationSession)
