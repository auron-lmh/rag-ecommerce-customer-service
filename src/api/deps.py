"""模块12 依赖注入 — FastAPI Depends 工厂 + 模块13 鉴权依赖"""

from functools import lru_cache

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

from src.access import is_admin
from src.api.auth import CurrentUser, InvalidTokenError, decode_token
from src.embedding.embedder import Embedder, get_embedder
from src.embedding.milvus_store import MilvusStore
from src.embedding.pipeline import IndexingPipeline
from src.embedding.retriever import Retriever

# ── 模块13 鉴权依赖 ──

# auto_error=False: 无凭据时不自动 401，让我们手动控制响应体
_bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials=Depends(_bearer)) -> CurrentUser:
    """解析 Bearer JWT → 当前用户。无凭据/无效/过期 → 401。"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="未提供认证凭据")
    try:
        return decode_token(credentials.credentials)
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"token 无效或已过期: {e}")


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """管理面闸口: 仅 admin 角色可访问 → 否则 403"""
    if not is_admin(user.role):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@lru_cache
def get_store() -> MilvusStore:
    """MilvusStore 单例"""
    return MilvusStore()


@lru_cache
def get_embedder_instance() -> Embedder:
    """Embedder 单例"""
    return get_embedder()


@lru_cache
def get_retriever() -> Retriever:
    """Retriever 单例（Embedder + MilvusStore + Reranker）"""
    return Retriever(
        embedder=get_embedder_instance(),
        store=get_store(),
    )


@lru_cache
def get_pipeline() -> IndexingPipeline:
    """IndexingPipeline 单例（Embedder + MilvusStore）"""
    return IndexingPipeline(
        embedder=get_embedder_instance(),
        store=get_store(),
    )
