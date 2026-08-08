"""模块13 内容访问控制 — 等级枚举 / 角色映射 / Milvus 过滤表达式

内容级权限隔离（RBAC + RAG 检索过滤）的单一权威模块。
所有检索调用点都从这里取过滤表达式，杜绝各层各写一套导致漏过滤。

权限模型（层级）:
    public(0) < member(1) < vip(2)

可见性规则:
    用户等级(rank) >= 文档等级(rank) 才可见 → Milvus filter: access_level <= {用户rank}

fail-safe 原则:
    任何调用点漏传 access_level，默认取最低权限 public —— 只返回公开内容，永不泄漏。

存储说明:
    Milvus 顶层标量字段 access_level 存 INT8 rank（0/1/2）。
    不能用字符串比较（字典序 "member"<"public"<"vip"，语义错位）。
    可读名（public/member/vip）保留在 chunk_metadata JSON 的 access_level_label 供调试。
"""

from enum import IntEnum

# Milvus 顶层标量字段名（INT8 rank）
MILVUS_ACCESS_FIELD = "access_level"

# chunk_metadata JSON 里的可读名标签（调试/展示用）
ACCESS_LABEL_FIELD = "access_level_label"


class AccessLevel(IntEnum):
    """内容等级 — 数值即 rank，越大越敏感"""

    PUBLIC = 0
    MEMBER = 1
    VIP = 2


# rank → 可读名（反转 AccessLevel 的语义）
_LEVEL_NAMES = {0: "public", 1: "member", 2: "vip"}

# 角色 → 内容等级（admin 与 vip 同级最高；admin 额外用于管理面闸口 require_admin）
ROLE_TO_LEVEL = {
    "normal": AccessLevel.PUBLIC,
    "member": AccessLevel.MEMBER,
    "vip": AccessLevel.VIP,
    "admin": AccessLevel.VIP,
}

_LEVEL_RANK = {v: k for k, v in ROLE_TO_LEVEL.items()}


def parse_access_level(value, default: str = "public") -> int:
    """把任意输入的等级名/rank 规范化为 int rank；非法输入回退 default（fail-safe）。

    Args:
        value: "public"/"member"/"vip" 或 0/1/2 或 AccessLevel 枚举
        default: 非法输入时的回退等级名（默认最低权限 public）

    Returns:
        int rank (0/1/2)
    """
    if isinstance(value, AccessLevel):
        return int(value)
    if isinstance(value, bool):  # bool 是 int 子类，先排除
        return int(ROLE_TO_LEVEL.get(default, AccessLevel.PUBLIC))
    if isinstance(value, int):
        if value in (0, 1, 2):
            return value
        return int(ROLE_TO_LEVEL.get(default, AccessLevel.PUBLIC))
    if isinstance(value, str):
        name = value.strip().lower()
        if name in ("public", "0"):
            return 0
        if name in ("member", "1"):
            return 1
        if name in ("vip", "2"):
            return 2
    return int(ROLE_TO_LEVEL.get(default, AccessLevel.PUBLIC))


def level_name(rank) -> str:
    """rank → 可读名（public/member/vip），非法 rank 返回 'public'"""
    return _LEVEL_NAMES.get(int(parse_access_level(rank)), "public")


def access_rank_for_role(role: str) -> int:
    """角色 → 内容等级 rank（admin 与 vip 同级）"""
    role = (role or "").strip().lower()
    return int(ROLE_TO_LEVEL.get(role, AccessLevel.PUBLIC))


def build_access_filter_expr(access_level) -> str:
    """用户等级 → Milvus filter 片段，如 'access_level <= 1'。

    语义: 用户等级(rank) >= 文档等级(rank) 才可见。
    用整数比较，避免字符串字典序错位（"member"<"public"<"vip"）。
    """
    rank = parse_access_level(access_level)
    return f"{MILVUS_ACCESS_FIELD} <= {rank}"


def is_admin(role: str) -> bool:
    """是否为管理员（管理面闸口：上传/统计/评测）"""
    return (role or "").strip().lower() == "admin"
