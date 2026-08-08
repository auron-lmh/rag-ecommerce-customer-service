"""模块33 内容访问控制 — 等级映射 / 过滤表达式 / fail-safe"""

from src.access import (
    ROLE_TO_LEVEL,
    AccessLevel,
    access_rank_for_role,
    build_access_filter_expr,
    is_admin,
    level_name,
    parse_access_level,
)


class TestParseAccessLevel:
    def test_names(self):
        assert parse_access_level("public") == 0
        assert parse_access_level("member") == 1
        assert parse_access_level("vip") == 2

    def test_case_and_whitespace(self):
        assert parse_access_level(" VIP ") == 2
        assert parse_access_level("Member") == 1

    def test_int_and_enum(self):
        assert parse_access_level(0) == 0
        assert parse_access_level(2) == 2
        assert parse_access_level(AccessLevel.MEMBER) == 1

    def test_invalid_falls_back_to_public(self):
        # fail-safe: 非法输入/未知等级 → public(最低权限)，绝不超发
        assert parse_access_level("superadmin") == 0
        assert parse_access_level(99) == 0
        assert parse_access_level(None) == 0
        assert parse_access_level("") == 0

    def test_invalid_with_custom_default(self):
        assert parse_access_level("bogus", default="vip") == 2


class TestRoleToLevel:
    def test_role_mapping(self):
        assert access_rank_for_role("normal") == 0
        assert access_rank_for_role("member") == 1
        assert access_rank_for_role("vip") == 2
        assert access_rank_for_role("admin") == 2  # admin 与 vip 同级最高

    def test_unknown_role_public(self):
        assert access_rank_for_role("root") == 0
        assert access_rank_for_role("") == 0

    def test_rolemap_consistency(self):
        assert ROLE_TO_LEVEL["normal"] == AccessLevel.PUBLIC
        assert ROLE_TO_LEVEL["vip"] == AccessLevel.VIP


class TestLevelName:
    def test_roundtrip(self):
        assert level_name(0) == "public"
        assert level_name(1) == "member"
        assert level_name(2) == "vip"
        assert level_name("vip") == "vip"


class TestBuildAccessFilterExpr:
    def test_member_filter(self):
        # member 用户 → access_level <= 1，覆盖 public(0)+member(1)
        assert build_access_filter_expr("member") == "access_level <= 1"

    def test_vip_filter(self):
        assert build_access_filter_expr("vip") == "access_level <= 2"

    def test_public_filter(self):
        assert build_access_filter_expr("public") == "access_level <= 0"

    def test_invalid_failsafe(self):
        # 非法输入 → public(0)，最严，不泄漏
        assert build_access_filter_expr("superadmin") == "access_level <= 0"


class TestIsAdmin:
    def test_admin_only(self):
        assert is_admin("admin") is True
        assert is_admin("ADMIN") is True
        assert is_admin("vip") is False
        assert is_admin("") is False
