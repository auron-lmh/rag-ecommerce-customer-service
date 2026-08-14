"""模块33 JWT 鉴权 — 令牌签发/解码 + 当前用户模型 + 登录认证

闭环: 登录 → JWT(role) → get_current_user(身份) → 检索按 access_level 过滤知识范围。
身份只信 header(Bearer JWT)，不放 body（可伪造）。

安全说明:
  - demo 密码明文存 .env（hmac.compare_digest 防时序攻击比较）；
    生产必须换 bcrypt/argon2 哈希存储 + 独立用户库。
  - JWT 用 HS256，secret 必须通过 .env 覆盖，严禁使用默认值上线。
"""

import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from src.access import access_rank_for_role, level_name
from src.config import settings


class InvalidTokenError(Exception):
    """token 无效/过期"""


@dataclass
class CurrentUser:
    """已认证的当前用户（由 JWT 解码得到）"""

    username: str
    role: str
    access_level: str  # public/member/vip（内容权限等级名）
    seed_user_id: int | None = (
        None  # copilot 库 orders.user_id（订单归属隔离，admin=None）
    )

    @property
    def access_rank(self) -> int:
        """内容权限 rank（0/1/2），检索过滤用"""
        return access_rank_for_role(self.role)


def create_access_token(user: CurrentUser) -> str:
    """签发 JWT — payload 含 sub/role/access_level/seed_user_id/iat/exp"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.username,
        "role": user.role,
        "access_level": user.access_level,
        "seed_user_id": user.seed_user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> CurrentUser:
    """解码并校验 JWT（含过期），失败抛 InvalidTokenError"""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as e:
        raise InvalidTokenError(f"token 无效: {e}")

    username = payload.get("sub")
    if not username:
        raise InvalidTokenError("token 缺少 sub")
    # 修复(审查): access_level 以 role 权威映射为准（token 里的仅作展示），
    # 防止 .env 配置 role/access_level 不一致导致越权。
    role = str(payload.get("role", "normal"))
    seed_user_id = payload.get("seed_user_id")
    return CurrentUser(
        username=username,
        role=role,
        # access_level 以 role 权威映射（不信 token 里的 access_level，防伪造越权）
        access_level=level_name(access_rank_for_role(role)),
        seed_user_id=(int(seed_user_id) if seed_user_id not in (None, "") else None),
    )


def authenticate(username: str, password: str) -> CurrentUser | None:
    """校验用户名/密码（查 settings.demo_users），成功返回 CurrentUser，失败返回 None"""
    # P0 修复: demo 用户默认关闭，须显式 ENABLE_DEMO_USERS=true 才可用（防弱密码后门）
    if not settings.enable_demo_users:
        return None
    user_cfg = settings.demo_users.get(username)
    if not user_cfg:
        return None
    expected = str(user_cfg.get("password", ""))
    # 防时序攻击: 长度恒定比较
    if not hmac.compare_digest(str(password), expected):
        return None
    sid = user_cfg.get("seed_user_id")
    return CurrentUser(
        username=username,
        role=str(user_cfg.get("role", "normal")),
        access_level=str(user_cfg.get("access_level", "public")),
        seed_user_id=int(sid) if sid is not None else None,
    )
