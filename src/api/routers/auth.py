"""模块33 登录路由 — POST /api/auth/login

用户面/管理面统一登录入口，签发 JWT。后续请求带 Authorization: Bearer <token>。
"""

import logging

from fastapi import APIRouter, HTTPException

from src.api.auth import authenticate, create_access_token
from src.api.models import LoginRequest
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["鉴权"])


@router.post("/login")
def login(req: LoginRequest) -> dict:
    """用户名密码登录 → 返回 JWT 令牌 + 用户信息"""
    user = authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.token_expire_minutes * 60,
        "user": {
            "username": user.username,
            "role": user.role,
            "access_level": user.access_level,
        },
    }
