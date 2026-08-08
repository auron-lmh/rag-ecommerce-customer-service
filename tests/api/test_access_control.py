"""模块13 API 层内容隔离 — 登录 → 查询 → 按用户等级过滤知识范围

用记录型 retriever 覆盖依赖，验证: 用户 access_level 从 JWT 一路透传到检索。
不触达真实 Milvus。
"""

import pytest
from fastapi.testclient import TestClient

from src.api import deps as api_deps
from src.api.app import app as real_app
from src.embedding.models import SearchResponse


class _RecordingRetriever:
    def __init__(self):
        self.last_access_level = None

    def search(self, query, top_k=5, use_rerank=True, use_hybrid=True, **kwargs):
        self.last_access_level = kwargs.get("access_level")
        return SearchResponse(
            query=query,
            results=[],
            total_found=0,
            elapsed_ms=1,
            threshold=0,
        )


@pytest.fixture
def client(monkeypatch):
    rec = _RecordingRetriever()
    real_app.dependency_overrides[api_deps.get_retriever] = lambda: rec
    yield TestClient(real_app), rec
    real_app.dependency_overrides.clear()


def _login(client: TestClient, username: str):
    r = client.post(
        "/api/auth/login",
        json={"username": username, "password": f"{username}123"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


class TestAPIAccessIsolation:
    def test_normal_user_sees_public_only(self, client):
        tc, rec = client
        token = _login(tc, "normal")  # role=normal → access_level=public(0)
        r = tc.post(
            "/api/query",
            json={"query": "怎么退货"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert rec.last_access_level == "public"

    def test_member_user_filters_to_member(self, client):
        tc, rec = client
        token = _login(tc, "member")
        tc.post(
            "/api/query",
            json={"query": "怎么退货"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rec.last_access_level == "member"

    def test_vip_user_sees_full_kb(self, client):
        tc, rec = client
        token = _login(tc, "vip")
        tc.post(
            "/api/query",
            json={"query": "怎么退货"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rec.last_access_level == "vip"

    def test_query_without_login_blocked(self, client):
        tc, _ = client
        r = tc.post("/api/query", json={"query": "怎么退货"})
        assert r.status_code == 401

    def test_member_cannot_upload(self, client):
        """管理面隔离: 普通用户访问 /api/upload → 403"""
        tc, _ = client
        token = _login(tc, "member")
        r = tc.post(
            "/api/upload",
            json={"file_path": "x.md", "access_level": "vip"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403

    def test_admin_can_access_manage(self, client):
        """admin 可访问管理面（/api/cache/stats 纯管理接口，200 证明通过闸口）"""
        tc, _ = client
        token = _login(tc, "admin")
        r = tc.get("/api/cache/stats", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_member_blocked_from_admin_stats(self, client):
        """管理面隔离: member 访问 /api/cache/stats → 403"""
        tc, _ = client
        token = _login(tc, "member")
        r = tc.get("/api/cache/stats", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403
