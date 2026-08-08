"""模块13 JWT 鉴权 — 登录 / 令牌签发解码 / 管理面闸口 / 无 token 401"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api.app import app as real_app
from src.api.auth import (
    CurrentUser,
    InvalidTokenError,
    authenticate,
    create_access_token,
    decode_token,
)
from src.api.deps import get_current_user, require_admin
from src.config import settings

# ═══════════════════════════════════════
# 最小测试应用（只挂鉴权依赖，不依赖 Milvus/LLM）
# ═══════════════════════════════════════


def _make_auth_app() -> FastAPI:
    app = FastAPI()

    @app.get("/whoami")
    def whoami(user: CurrentUser = Depends(get_current_user)):
        return {
            "username": user.username,
            "role": user.role,
            "access_level": user.access_level,
            "rank": user.access_rank,
        }

    @app.get("/admin")
    def admin(user: CurrentUser = Depends(require_admin)):
        return {"ok": True, "admin": user.username}

    return app


@pytest.fixture
def auth_client():
    return TestClient(_make_auth_app())


def _token(role="member", access_level="member", username="tester"):
    return create_access_token(
        CurrentUser(username=username, role=role, access_level=access_level)
    )


class TestAuthenticate:
    def test_valid_credentials(self):
        user = authenticate("member", "member123")
        assert user is not None
        assert user.role == "member"
        assert user.access_level == "member"

    def test_wrong_password(self):
        assert authenticate("member", "wrong") is None

    def test_unknown_user(self):
        assert authenticate("nobody", "x") is None


class TestTokenRoundtrip:
    def test_roundtrip(self):
        token = _token(role="vip", access_level="vip")
        user = decode_token(token)
        assert user.username == "tester"
        assert user.role == "vip"
        assert user.access_rank == 2

    def test_admin_rank_highest(self):
        user = decode_token(_token(role="admin", access_level="vip"))
        assert user.access_rank == 2

    def test_invalid_token_raises(self):
        with pytest.raises(InvalidTokenError):
            decode_token("not.a.jwt")

    def test_expired_token_raises(self):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "expired",
            "role": "vip",
            "access_level": "vip",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),  # 已过期
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        with pytest.raises(InvalidTokenError):
            decode_token(token)


class TestAuthDependency:
    def test_no_token_401(self, auth_client):
        r = auth_client.get("/whoami")
        assert r.status_code == 401

    def test_valid_token_ok(self, auth_client):
        r = auth_client.get("/whoami", headers={"Authorization": f"Bearer {_token()}"})
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "tester"
        assert body["role"] == "member"
        assert body["rank"] == 1

    def test_invalid_token_401(self, auth_client):
        r = auth_client.get("/whoami", headers={"Authorization": "Bearer garbage"})
        assert r.status_code == 401

    def test_member_blocked_from_admin_403(self, auth_client):
        r = auth_client.get(
            "/admin", headers={"Authorization": f"Bearer {_token('member')}"}
        )
        assert r.status_code == 403

    def test_admin_allowed(self, auth_client):
        r = auth_client.get(
            "/admin", headers={"Authorization": f"Bearer {_token('admin', 'vip')}"}
        )
        assert r.status_code == 200
        assert r.json()["admin"] == "tester"


class TestLoginEndpoint:
    def test_login_success_all_roles(self):
        client = TestClient(real_app)
        for username, role, access_level in [
            ("admin", "admin", "vip"),
            ("vip", "vip", "vip"),
            ("member", "member", "member"),
            ("normal", "normal", "public"),
        ]:
            r = client.post(
                "/api/auth/login",
                json={"username": username, "password": f"{username}123"},
            )
            assert r.status_code == 200, f"{username}: {r.text}"
            body = r.json()
            assert body["token_type"] == "bearer"
            assert body["user"]["role"] == role
            assert body["user"]["access_level"] == access_level
            # 返回的 token 可解码且角色一致
            user = decode_token(body["access_token"])
            assert user.role == role

    def test_login_wrong_password_401(self):
        client = TestClient(real_app)
        r = client.post(
            "/api/auth/login", json={"username": "member", "password": "bad"}
        )
        assert r.status_code == 401

    def test_login_unknown_user_401(self):
        client = TestClient(real_app)
        r = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
        assert r.status_code == 401

    def test_query_without_token_401(self):
        """用户面检索路由未带 token → 401（鉴权先行，不触达 Milvus）"""
        client = TestClient(real_app)
        r = client.post("/api/query", json={"query": "怎么退货"})
        assert r.status_code == 401

    def test_query_with_token_reaches_retriever(self):
        """带有效 token → 通过鉴权（get_retriever 依赖被覆盖，不触达真实 Milvus）"""
        from src.api import deps as api_deps
        from src.embedding.models import SearchResponse

        class _FakeRetriever:
            def search(
                self, query, top_k=5, use_rerank=True, use_hybrid=True, **kwargs
            ):
                return SearchResponse(
                    query=query, results=[], total_found=0, elapsed_ms=1, threshold=0
                )

        real_app.dependency_overrides[api_deps.get_retriever] = lambda: _FakeRetriever()
        try:
            client = TestClient(real_app)
            r = client.post(
                "/api/query",
                json={"query": "怎么退货"},
                headers={"Authorization": f"Bearer {_token('member', 'member')}"},
            )
            assert r.status_code == 200
        finally:
            real_app.dependency_overrides.clear()
