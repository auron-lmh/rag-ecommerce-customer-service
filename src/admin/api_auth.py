"""模块33 管理后台 API 鉴权辅助 — Gradio UI 内部调用 API 时自动登录携带 JWT

背景: 模块33 之后 API 全部需要鉴权，Gradio 三端作为内部调用方，
启动时用配置账号登录一次拿 token，后续请求带 Authorization 头。

账号通过环境变量配置（默认 demo 账号）:
  API_BASE_URL  (默认 http://rag-api:8000)
  API_USERNAME  (客户聊天 UI 默认 normal；管理端 UI 覆盖为 admin)
  API_PASSWORD  (默认 {username}123)
"""

import logging
import os
import threading
import time

import requests

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://rag-api:8000")
API_USERNAME = os.getenv("API_USERNAME", "")
API_PASSWORD = os.getenv("API_PASSWORD", "")

# token 缓存（10 分钟刷新一次，远小于 720min 过期）
_token_cache: dict = {"token": "", "ts": 0.0}
_lock = threading.Lock()
_REFRESH_SECONDS = 600


def _login() -> str:
    """登录获取新 token，失败返回空串（服务端此时会 401，UI 提示登录配置）"""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            json={"username": API_USERNAME, "password": API_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token", "")
    except Exception as e:
        logger.warning("API 登录失败 (username=%s): %s", API_USERNAME, e)
        return ""


def get_token() -> str:
    """获取有效 token（带 10 分钟本地缓存）"""
    with _lock:
        if (
            _token_cache["token"]
            and time.time() - _token_cache["ts"] < _REFRESH_SECONDS
        ):
            return _token_cache["token"]
        token = _login()
        if token:
            _token_cache["token"] = token
            _token_cache["ts"] = time.time()
        return token


def auth_headers() -> dict:
    """返回带 Authorization 的请求头（登录失败则空 dict）"""
    token = get_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def gradio_auth() -> tuple[str, str]:
    """Gradio UI Basic Auth 凭据；未配置则抛错拒绝无鉴权启动（P0 修复）"""
    from src.config import settings

    if not (settings.gradio_username and settings.gradio_password):
        raise RuntimeError(
            "未配置 GRADIO_USERNAME / GRADIO_PASSWORD，拒绝无鉴权启动 UI"
        )
    return (settings.gradio_username, settings.gradio_password)
